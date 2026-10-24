import uuid

from django.db import models


class BaseModel(models.Model):
    """Shared primary key and timestamps for every table."""

    id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, primary_key=True)
    date_modified = models.DateTimeField(auto_now=True)
    date_created = models.DateTimeField(auto_now_add=True)
    synced = models.BooleanField(default=False)

    class Meta(object):
        abstract = True


class GenericBaseModel(BaseModel):
    """Named lookup rows such as states."""

    name = models.CharField(max_length=200)
    description = models.TextField(max_length=255, blank=True, null=True)

    class Meta(object):
        abstract = True


class State(GenericBaseModel):
    """Workflow states such as Booked and Cancelled."""

    def __str__(self):
        return '%s' % self.name

    class Meta(object):
        ordering = ('name',)

    @classmethod
    def default_state(cls):
        """Returns the Active state.
		@return: The Active state, or None when it does not exist.
		@rtype: State | None"""
        try:
            return cls.objects.get(name='Active')
        except Exception:
            return None

    @classmethod
    def disabled_state(cls):
        """Returns the Disabled state.
		@return: The Disabled state, or None when it does not exist.
		@rtype: State | None"""
        try:
            return cls.objects.get(name='Disabled')
        except Exception:
            return None


class Doctor(BaseModel):
    """A clinician who owns a day of bookable slots."""

    name = models.CharField(max_length=50)
    password = models.CharField(max_length=128)

    def __str__(self):
        return '%s' % self.name

    class Meta(object):
        ordering = ('name',)


class Patient(BaseModel):
    """A person who books an appointment."""

    name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    password = models.CharField(max_length=128, blank=True, null=True)

    def __str__(self):
        return '%s' % self.name

    class Meta(object):
        ordering = ('name',)


class Slot(BaseModel):
    """One 30-minute opening on a doctor's day."""

    class Status(models.TextChoices):
        ACTIVE = 'active', 'active'
        AVAILABLE = 'available', 'available'
        BOOKED = 'booked', 'booked'

    doctor = models.ForeignKey(Doctor, related_name='slots', on_delete=models.CASCADE)
    start_time = models.TimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)

    def __str__(self):
        return '%s %s' % (self.doctor, self.start_time.strftime('%H:%M'))

    class Meta(object):
        ordering = ('start_time',)
        constraints = [
            models.UniqueConstraint(fields=['doctor', 'start_time'], name='unique_doctor_slot_time'),
        ]


class Appointment(BaseModel):
    """A patient booked into a slot on a given date."""

    patient = models.ForeignKey(Patient, related_name='appointments', on_delete=models.CASCADE)
    slot = models.ForeignKey(Slot, related_name='appointments', on_delete=models.CASCADE)
    date = models.DateField()
    state = models.ForeignKey(State, related_name='appointments', on_delete=models.CASCADE)
    cancellation_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return '%s %s' % (self.patient, self.date)

    class Meta(object):
        ordering = ('date', 'slot__start_time')
        constraints = [
            models.UniqueConstraint(
                fields=['slot', 'date'],
                condition=models.Q(cancellation_reason__isnull=True),
                name='one_active_booking_per_slot_date',
            ),
        ]
