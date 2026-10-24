"""Idempotent seed data for the clinic admin and roster."""

import os

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

from base.backend.services import DoctorService, PatientService
from base.models import Doctor, Patient

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ['ADMIN_PASSWORD']
DOCTOR_PASSWORD = os.environ['DOCTOR_PASSWORD']
PATIENT_PASSWORD = os.environ['PATIENT_PASSWORD']

DOCTOR_NAMES = ('Ada', 'Ben', 'Cara', 'Dan', 'Eve')
PATIENTS = (
    ('Grace', '0700000001'),
    ('Ken', '0700000002'),
    ('Lucy', '0700000003'),
    ('Mo', '0700000004'),
)


def seed_admin():
    """Creates the super admin and their API token.
		@return: The admin user and token.
		@rtype: tuple"""
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=ADMIN_USERNAME,
        defaults={
            'is_staff': True,
            'is_superuser': True,
            'is_active': True,
        },
    )
    if created:
        user.set_password(ADMIN_PASSWORD)
        user.save()
    else:
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(ADMIN_PASSWORD)
        user.save()
    token, _ = Token.objects.get_or_create(user=user)
    return user, token


def seed_doctors():
    """Creates the five clinic doctors and their slot grids.
		@return: The doctors in name order.
		@rtype: list"""
    doctors = []
    for name in DOCTOR_NAMES:
        doctor = Doctor.objects.filter(name=name).first()
        if doctor is None:
            doctor = DoctorService().create(name=name, password=DOCTOR_PASSWORD)
        doctors.append(doctor)
    return doctors


def seed_patients():
    """Creates the four clinic patients.
		@return: The patients in name order.
		@rtype: list"""
    patients = []
    for name, phone in PATIENTS:
        patient = Patient.objects.filter(name=name).first()
        if patient is None:
            patient = PatientService().create(
                name=name, phone_number=phone, password=PATIENT_PASSWORD,
            )
        patients.append(patient)
    return patients


def seed_all():
    """Seeds the admin, doctors, and patients.
		@return: None
		@rtype: None"""
    seed_admin()
    seed_doctors()
    seed_patients()
