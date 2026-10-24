"""Model services. Views talk to these instead of the ORM."""

import logging
from datetime import datetime, timedelta

from django.contrib.auth.hashers import make_password
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from base.backend.servicebase import ServiceBase
from base.models import Appointment, Doctor, Patient, Slot, State

lgr = logging.getLogger(__name__)

DAY_START_HOUR = 8
DAY_HOURS = 7
SLOT_MINUTES = 30


class StateService(ServiceBase):
    """Service class for State."""

    manager = State.objects


class DoctorService(ServiceBase):
    """Service class for Doctor. Creating a doctor also builds that day's slots."""

    manager = Doctor.objects

    def create(self, **kwargs):
        """Creates a doctor and the 30-minute slots for that doctor's day.
		@param kwargs: Field values for the doctor. A password is stored hashed.
		@type kwargs: dict
		@return: The created doctor, or None on error.
		@rtype: Doctor | None"""
        password = kwargs.get('password')
        if password:
            kwargs['password'] = make_password(password)
        try:
            with transaction.atomic():
                doctor = self.manager.create(**kwargs)
                SlotService().generate_day(doctor)
                return doctor
        except Exception as e:
            lgr.exception('Doctor Service create exception: %s', e)
        return None


class PatientService(ServiceBase):
    """Service class for Patient."""

    manager = Patient.objects

    def create(self, **kwargs):
        """Creates a patient.
		@param kwargs: Field values for the patient. A password is stored hashed.
		@type kwargs: dict
		@return: The created patient, or None on error.
		@rtype: Patient | None"""
        password = kwargs.get('password')
        if password:
            kwargs['password'] = make_password(password)
        return super().create(**kwargs)


class SlotService(ServiceBase):
    """Service class for Slot."""

    manager = Slot.objects

    def generate_day(self, doctor):
        """Creates 30-minute slots covering a 7-hour day, starting at 08:00.
		@param doctor: The doctor who owns the new slots.
		@type doctor: Doctor
		@return: The created slots.
		@rtype: list"""
        start = datetime.now().replace(
            hour=DAY_START_HOUR, minute=0, second=0, microsecond=0,
        )
        count = (DAY_HOURS * 60) // SLOT_MINUTES
        slots = [
            Slot(
                doctor=doctor,
                start_time=(start + timedelta(minutes=SLOT_MINUTES * index)).time(),
                status=Slot.Status.AVAILABLE,
            )
            for index in range(count)
        ]
        return Slot.objects.bulk_create(slots)


def slot_end(start_time):
    """Returns the end of a 30-minute slot.
		@param start_time: The slot start.
		@type start_time: datetime.time
		@return: The slot end, 30 minutes after the start.
		@rtype: datetime.time"""
    return (datetime.combine(datetime.min, start_time) + timedelta(minutes=SLOT_MINUTES)).time()


def starts_at(visit_date, start_time):
    """Builds the timezone-aware start of a slot on a clinic day.
		@param visit_date: The clinic day.
		@type visit_date: datetime.date
		@param start_time: The slot start.
		@type start_time: datetime.time
		@return: The aware datetime for that slot.
		@rtype: datetime.datetime"""
    combined = datetime.combine(visit_date, start_time)
    return timezone.make_aware(combined, timezone.get_current_timezone())


class AppointmentService(ServiceBase):
    """Service class for Appointment."""

    manager = Appointment.objects

    def book(self, patient_id, doctor_id, visit_date, start_time):
        """Books a doctor's slot on a date.
		@param patient_id: The patient who is booking.
		@type patient_id: uuid.UUID
		@param doctor_id: The doctor whose slot is being booked.
		@type doctor_id: uuid.UUID
		@param visit_date: The clinic day of the visit.
		@type visit_date: datetime.date
		@param start_time: The slot start. It must fall on the doctor's grid.
		@type start_time: datetime.time
		@return: The appointment and an error code. The error is None on success.
		@rtype: tuple"""
        try:
            with transaction.atomic():
                try:
                    doctor = Doctor.objects.get(id=doctor_id)
                except Doctor.DoesNotExist:
                    return None, 'doctor_not_found'
                try:
                    patient = Patient.objects.get(id=patient_id)
                except Patient.DoesNotExist:
                    return None, 'patient_not_found'
                slot = (
                    Slot.objects.select_for_update()
                    .filter(doctor=doctor, start_time=start_time)
                    .first()
                )
                if slot is None:
                    return None, 'outside_hours'
                error = self._validate_start(visit_date, start_time)
                if error:
                    return None, error
                if self._is_taken(slot, visit_date):
                    return None, 'taken'
                state = State.objects.get(name='Booked')
                appointment = self.manager.create(
                    patient=patient, slot=slot, date=visit_date, state=state,
                )
                return appointment, None
        except IntegrityError:
            return None, 'taken'
        except Exception as e:
            lgr.exception('Appointment Service book exception: %s', e)
        return None, 'failed'

    def cancel(self, appointment_id, reason):
        """Cancels a booking, records the reason, and frees that date and time.
		@param appointment_id: The appointment to cancel.
		@type appointment_id: uuid.UUID
		@param reason: Why the appointment is being cancelled.
		@type reason: str
		@return: The appointment and an error code. The error is None on success.
		@rtype: tuple"""
        try:
            with transaction.atomic():
                appointment = (
                    Appointment.objects.select_for_update()
                    .select_related('slot', 'state')
                    .get(id=appointment_id)
                )
                if self._is_cancelled(appointment):
                    return appointment, 'already_cancelled'
                cancelled = State.objects.get(name='Cancelled')
                appointment.state = cancelled
                appointment.cancellation_reason = reason
                appointment.save(update_fields=['state', 'cancellation_reason', 'date_modified'])
                return appointment, None
        except Appointment.DoesNotExist:
            return None, 'not_found'
        except Exception as e:
            lgr.exception('Appointment Service cancel exception: %s', e)
        return None, 'failed'

    def reschedule(self, appointment_id, visit_date, start_time):
        """Moves a booking onto a new slot. The previous slot becomes free.
		@param appointment_id: The appointment to move.
		@type appointment_id: uuid.UUID
		@param visit_date: The new clinic day.
		@type visit_date: datetime.date
		@param start_time: The new slot start.
		@type start_time: datetime.time
		@return: The appointment and an error code. The error is None on success.
		@rtype: tuple"""
        try:
            with transaction.atomic():
                appointment = (
                    Appointment.objects.select_for_update()
                    .select_related('slot', 'state')
                    .get(id=appointment_id)
                )
                if self._is_cancelled(appointment):
                    return appointment, 'already_cancelled'
                slot = (
                    Slot.objects.select_for_update()
                    .filter(doctor_id=appointment.slot.doctor_id, start_time=start_time)
                    .first()
                )
                if slot is None:
                    return None, 'outside_hours'
                error = self._validate_start(visit_date, start_time)
                if error:
                    return None, error
                if self._is_taken(slot, visit_date, exclude_id=appointment.id):
                    return None, 'taken'
                appointment.slot = slot
                appointment.date = visit_date
                appointment.save(update_fields=['slot', 'date', 'date_modified'])
                return appointment, None
        except Appointment.DoesNotExist:
            return None, 'not_found'
        except IntegrityError:
            return None, 'taken'
        except Exception as e:
            lgr.exception('Appointment Service reschedule exception: %s', e)
        return None, 'failed'

    def availability(self, doctor_id, visit_date):
        """Returns free 30-minute slots for a doctor on a date.
		@param doctor_id: The doctor whose grid is being read.
		@type doctor_id: uuid.UUID
		@param visit_date: The clinic day.
		@type visit_date: datetime.date
		@return: The free slots and an error code. The error is None on success.
		@rtype: tuple"""
        try:
            doctor = Doctor.objects.get(id=doctor_id)
        except Doctor.DoesNotExist:
            return None, 'doctor_not_found'
        taken_ids = set(
            Appointment.objects.filter(
                slot__doctor=doctor,
                date=visit_date,
                cancellation_reason__isnull=True,
            ).values_list('slot_id', flat=True)
        )
        free = []
        for slot in Slot.objects.filter(doctor=doctor).order_by('start_time'):
            if slot.id in taken_ids:
                continue
            if self._validate_start(visit_date, slot.start_time):
                continue
            free.append(slot)
        return free, None

    def upcoming_for_patient(self, patient_id):
        """Returns active appointments that have not started, ordered by date then start time.
		@param patient_id: The patient whose visits are listed.
		@type patient_id: uuid.UUID
		@return: The appointments and an error code. The error is None on success.
		@rtype: tuple"""
        if not Patient.objects.filter(id=patient_id).exists():
            return None, 'patient_not_found'
        now = timezone.localtime()
        appointments = (
            self.manager.filter(patient_id=patient_id, cancellation_reason__isnull=True)
            .filter(Q(date__gt=now.date()) | Q(date=now.date(), slot__start_time__gte=now.time()))
            .select_related('slot', 'slot__doctor', 'state')
            .order_by('date', 'slot__start_time')
        )
        return list(appointments), None

    def _validate_start(self, visit_date, start_time):
        """Checks that a slot start is still in the future and at least one hour away.
		@param visit_date: The clinic day.
		@type visit_date: datetime.date
		@param start_time: The slot start.
		@type start_time: datetime.time
		@return: An error code, or None when the start is bookable.
		@rtype: str | None"""
        when = starts_at(visit_date, start_time)
        now = timezone.now()
        if when <= now:
            return 'in_the_past'
        if when < now + timedelta(hours=1):
            return 'within_hour'
        return None

    def _is_taken(self, slot, visit_date, exclude_id=None):
        """Checks whether another active appointment already holds this slot on this date.
		@param slot: The slot to check.
		@type slot: Slot
		@param visit_date: The clinic day.
		@type visit_date: datetime.date
		@param exclude_id: An appointment id to ignore, used when rescheduling.
		@type exclude_id: uuid.UUID | None
		@return: True when the slot is already held.
		@rtype: bool"""
        taken = Appointment.objects.filter(
            slot=slot, date=visit_date, cancellation_reason__isnull=True,
        )
        if exclude_id is not None:
            taken = taken.exclude(id=exclude_id)
        return taken.exists()

    def _is_cancelled(self, appointment):
        """Checks whether the appointment has already been cancelled.
		@param appointment: The appointment to check.
		@type appointment: Appointment
		@return: True when the appointment is cancelled.
		@rtype: bool"""
        return appointment.cancellation_reason is not None or appointment.state.name == 'Cancelled'
