import logging

from django.urls import path
from rest_framework.response import Response
from rest_framework.views import APIView

from api.errors import service_error
from api.utility.common import appointment_payload
from base.backend.services import AppointmentService, PatientService

lgr = logging.getLogger(__name__)


class ListPatients(APIView):
    """GET /patients"""

    def get(self, request):
        """Lists every patient for the authenticated admin.
		@param request: The HTTP request.
		@type request: Request
		@return: The patients without passwords.
		@rtype: Response"""
        try:
            patients = PatientService().filter()
            patients = [] if patients is None else patients.order_by('name')
            return Response({
                'patients': [
                    {
                        'id': str(patient.id),
                        'name': patient.name,
                        'phone_number': patient.phone_number,
                        'date_created': patient.date_created.isoformat(),
                    }
                    for patient in patients
                ],
            })
        except Exception as ex:
            lgr.exception('Error listing patients: %s', ex)
            return Response({'detail': 'General failure.'}, status=500)


class PatientAppointments(APIView):
    """GET /patients/{id}/appointments"""

    def get(self, request, patient_id):
        """Returns a patient's upcoming appointments, earliest first.
		@param request: The HTTP request.
		@type request: Request
		@param patient_id: The patient whose visits are listed.
		@type patient_id: uuid.UUID
		@return: The upcoming appointments, or an error response.
		@rtype: Response"""
        try:
            appointments, error = AppointmentService().upcoming_for_patient(patient_id)
            if error:
                return service_error(error)
            return Response({
                'patient_id': str(patient_id),
                'appointments': [appointment_payload(appointment) for appointment in appointments],
            })
        except Exception as ex:
            lgr.exception('Error listing appointments: %s', ex)
            return Response({'detail': 'General failure.'}, status=500)


urlpatterns = [
    path('patients', ListPatients.as_view()),
    path('patients/<uuid:patient_id>/appointments', PatientAppointments.as_view()),
]
