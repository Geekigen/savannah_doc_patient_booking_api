import uuid
from datetime import datetime, time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from base.models import Appointment, Doctor, Patient, Slot, State
from base.seed import ADMIN_PASSWORD, ADMIN_USERNAME, seed_all


class BookingAPITests(APITestCase):
    def setUp(self):
        seed_all()
        self.user = get_user_model().objects.get(username=ADMIN_USERNAME)
        self.token = Token.objects.get(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token %s' % self.token.key)
        self.doctor = Doctor.objects.get(name='Ada')
        self.patient = Patient.objects.get(name='Grace')
        self.other = Patient.objects.get(name='Ken')
        self.day = timezone.localdate() + timedelta(days=2)

    def book(self, start='08:00', day=None, patient=None, doctor=None):
        return self.client.post('/appointments', {
            'patient_id': str((patient or self.patient).id),
            'doctor_id': str((doctor or self.doctor).id),
            'date': (day or self.day).isoformat(),
            'start_time': start,
        }, format='json')

    def test_login_and_lists_require_auth(self):
        self.client.credentials()
        denied = self.client.get('/doctors')
        self.assertEqual(denied.status_code, 401, denied.data)
        self.assertEqual(denied.data['error'], 'Unauthorized')

        bad = self.client.post('/login', {'username': ADMIN_USERNAME, 'password': 'wrong'}, format='json')
        self.assertEqual(bad.status_code, 401, bad.data)

        login = self.client.post(
            '/login',
            {'username': ADMIN_USERNAME, 'password': ADMIN_PASSWORD},
            format='json',
        )
        self.assertEqual(login.status_code, 200, login.data)
        self.assertEqual(login.data['username'], ADMIN_USERNAME)
        self.assertTrue(login.data['token'])

        self.client.credentials(HTTP_AUTHORIZATION='Token %s' % login.data['token'])
        doctors = self.client.get('/doctors')
        self.assertEqual(doctors.status_code, 200, doctors.data)
        self.assertEqual(len(doctors.data['doctors']), 5)
        self.assertEqual(
            [doctor['name'] for doctor in doctors.data['doctors']],
            ['Ada', 'Ben', 'Cara', 'Dan', 'Eve'],
        )
        self.assertNotIn('password', doctors.data['doctors'][0])

        patients = self.client.get('/patients')
        self.assertEqual(patients.status_code, 200, patients.data)
        self.assertEqual(len(patients.data['patients']), 4)
        self.assertEqual(
            [patient['name'] for patient in patients.data['patients']],
            ['Grace', 'Ken', 'Lucy', 'Mo'],
        )
        self.assertNotIn('password', patients.data['patients'][0])

        unauthenticated_book = self.client
        unauthenticated_book.credentials()
        blocked = unauthenticated_book.post('/appointments', {
            'patient_id': str(self.patient.id),
            'doctor_id': str(self.doctor.id),
            'date': self.day.isoformat(),
            'start_time': '08:00',
        }, format='json')
        self.assertEqual(blocked.status_code, 401, blocked.data)

    def test_book_cancel_reschedule_and_lists(self):
        booked = self.book()
        self.assertEqual(booked.status_code, 200, booked.data)
        self.assertEqual(booked.data['start_time'], '08:00')
        self.assertEqual(booked.data['end_time'], '08:30')
        self.assertEqual(booked.data['state'], 'Booked')
        self.assertEqual(
            Slot.objects.get(doctor=self.doctor, start_time=time(8, 0)).status,
            Slot.Status.AVAILABLE,
        )

        taken = self.book(patient=self.other)
        self.assertEqual(taken.status_code, 409, taken.data)

        outside = self.book(start='07:00')
        self.assertEqual(outside.status_code, 409, outside.data)
        self.assertEqual(outside.data['error'], 'Conflict')
        self.assertIn('working hours', outside.data['message'])

        availability = self.client.get(
            '/doctors/%s/availability' % self.doctor.id,
            {'date': self.day.isoformat()},
        )
        self.assertEqual(availability.status_code, 200, availability.data)
        start_times = [slot['start_time'] for slot in availability.data['slots']]
        self.assertNotIn('08:00', start_times)
        self.assertIn('08:30', start_times)
        self.assertEqual(len(start_times), 13)

        missing = self.client.get('/doctors/%s/availability' % uuid.uuid4(), {'date': self.day.isoformat()})
        self.assertEqual(missing.status_code, 404)

        later = self.book(start='11:00', day=self.day + timedelta(days=1))
        self.assertEqual(later.status_code, 200, later.data)
        listed = self.client.get('/patients/%s/appointments' % self.patient.id)
        self.assertEqual(listed.status_code, 200, listed.data)
        self.assertEqual(
            [item['date'] for item in listed.data['appointments']],
            [self.day.isoformat(), (self.day + timedelta(days=1)).isoformat()],
        )

        moved = self.client.patch(
            '/appointments/%s/reschedule' % booked.data['id'],
            {'date': self.day.isoformat(), 'start_time': '09:00'},
            format='json',
        )
        self.assertEqual(moved.status_code, 200, moved.data)
        self.assertEqual(moved.data['start_time'], '09:00')
        after_move = self.client.get(
            '/doctors/%s/availability' % self.doctor.id,
            {'date': self.day.isoformat()},
        )
        moved_times = [slot['start_time'] for slot in after_move.data['slots']]
        self.assertIn('08:00', moved_times)
        self.assertNotIn('09:00', moved_times)

        cancelled = self.client.patch(
            '/appointments/%s/cancel' % booked.data['id'],
            {'reason': 'Feeling better'},
            format='json',
        )
        self.assertEqual(cancelled.status_code, 200, cancelled.data)
        self.assertEqual(cancelled.data['state'], 'Cancelled')
        self.assertEqual(cancelled.data['cancellation_reason'], 'Feeling better')
        freed = self.client.get(
            '/doctors/%s/availability' % self.doctor.id,
            {'date': self.day.isoformat()},
        )
        self.assertIn('09:00', [slot['start_time'] for slot in freed.data['slots']])

        again = self.client.patch(
            '/appointments/%s/cancel' % booked.data['id'],
            {'reason': 'Again'},
            format='json',
        )
        self.assertEqual(again.status_code, 409, again.data)

        rescheduled = self.client.patch(
            '/appointments/%s/reschedule' % booked.data['id'],
            {'date': self.day.isoformat(), 'start_time': '10:00'},
            format='json',
        )
        self.assertEqual(rescheduled.status_code, 409, rescheduled.data)

        without_reason = self.client.patch(
            '/appointments/%s/cancel' % later.data['id'],
            {},
            format='json',
        )
        self.assertEqual(without_reason.status_code, 400)
        self.assertEqual(without_reason.data['error'], 'Bad Request')
        self.assertIn('reason', without_reason.data['message'])

        wrong_method = self.client.get('/appointments')
        self.assertEqual(wrong_method.status_code, 405)
        self.assertEqual(wrong_method.data['error'], 'Method Not Allowed')
        self.assertIn('POST', wrong_method.headers['Allow'])

        remaining = self.client.get('/patients/%s/appointments' % self.patient.id)
        self.assertEqual([item['id'] for item in remaining.data['appointments']], [later.data['id']])

        unknown = self.client.get('/patients/%s/appointments' % uuid.uuid4())
        self.assertEqual(unknown.status_code, 404)

    def test_past_and_within_the_hour_are_rejected(self):
        zone = timezone.get_current_timezone()
        morning = timezone.make_aware(datetime(2026, 10, 26, 9, 0), zone)
        with patch('base.backend.services.timezone.now', return_value=morning):
            past = self.book(start='08:00', day=morning.date())
        self.assertEqual(past.status_code, 409, past.data)
        self.assertIn('past', past.data['message'])

        just_before = timezone.make_aware(datetime(2026, 10, 26, 7, 30), zone)
        with patch('base.backend.services.timezone.now', return_value=just_before):
            too_soon = self.book(start='08:00', day=just_before.date())
        self.assertEqual(too_soon.status_code, 409, too_soon.data)
        self.assertIn('one hour', too_soon.data['message'])

        on_the_hour = timezone.make_aware(datetime(2026, 10, 26, 7, 0), zone)
        with patch('base.backend.services.timezone.now', return_value=on_the_hour):
            allowed = self.book(start='08:00', day=on_the_hour.date())
        self.assertEqual(allowed.status_code, 200, allowed.data)

    def test_upcoming_list_skips_a_past_visit(self):
        past_slot = Slot.objects.get(doctor=self.doctor, start_time=time(10, 0))
        Appointment.objects.create(
            patient=self.patient,
            slot=past_slot,
            date=timezone.localdate() - timedelta(days=1),
            state=State.objects.get(name='Booked'),
        )
        listed = self.client.get('/patients/%s/appointments' % self.patient.id)
        self.assertEqual(listed.status_code, 200, listed.data)
        self.assertEqual(listed.data['appointments'], [])
