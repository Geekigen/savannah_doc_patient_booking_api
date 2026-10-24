import logging

from django.urls import path
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView

from api.errors import error_response, service_error
from api.utility.common import appointment_payload, parse_date, parse_time, parse_uuid
from base.backend.services import AppointmentService

lgr = logging.getLogger(__name__)


class BookAppointment(APIView):
    """POST /appointments"""

    def post(self, request):
        """Books a slot for a patient.
		@param request: The HTTP request. Body fields are patient_id, doctor_id, date, and start_time.
		@type request: Request
		@return: The booked appointment, or an error response.
		@rtype: Response"""
        try:
            data = request.data
            patient_id = parse_uuid(data.get('patient_id'))
            doctor_id = parse_uuid(data.get('doctor_id'))
            visit_date = parse_date(data.get('date'))
            start_time = parse_time(data.get('start_time'))
            if not data.get('patient_id') or not data.get('doctor_id') or not data.get('date') or not data.get('start_time'):
                return error_response(400, 'patient_id, doctor_id, date, and start_time are required.')
            if patient_id is None or doctor_id is None or visit_date is None or start_time is None:
                return error_response(
                    400,
                    'patient_id and doctor_id must be ids, date must be YYYY-MM-DD, and start_time must be HH:MM.',
                )
            appointment, error = AppointmentService().book(patient_id, doctor_id, visit_date, start_time)
            if error:
                return service_error(error)
            return Response(appointment_payload(appointment), status=200)
        except APIException:
            raise
        except Exception as ex:
            lgr.exception('Error booking appointment: %s', ex)
            return Response({'detail': 'General failure.'}, status=500)


class CancelAppointment(APIView):
    """PATCH /appointments/{id}/cancel"""

    def patch(self, request, appointment_id):
        """Cancels an appointment and frees its slot.
		@param request: The HTTP request. Body field is reason.
		@type request: Request
		@param appointment_id: The appointment to cancel.
		@type appointment_id: uuid.UUID
		@return: The cancelled appointment, or an error response.
		@rtype: Response"""
        try:
            reason = request.data.get('reason')
            if not isinstance(reason, str) or not reason.strip():
                return error_response(400, 'reason is required.')
            appointment, error = AppointmentService().cancel(appointment_id, reason.strip())
            if error:
                return service_error(error)
            return Response(appointment_payload(appointment))
        except APIException:
            raise
        except Exception as ex:
            lgr.exception('Error cancelling appointment: %s', ex)
            return Response({'detail': 'General failure.'}, status=500)


class RescheduleAppointment(APIView):
    """PATCH /appointments/{id}/reschedule"""

    def patch(self, request, appointment_id):
        """Moves an appointment to a new slot.
		@param request: The HTTP request. Body fields are date and start_time.
		@type request: Request
		@param appointment_id: The appointment to move.
		@type appointment_id: uuid.UUID
		@return: The updated appointment, or an error response.
		@rtype: Response"""
        try:
            data = request.data
            visit_date = parse_date(data.get('date'))
            start_time = parse_time(data.get('start_time'))
            if not data.get('date') or not data.get('start_time'):
                return error_response(400, 'date and start_time are required.')
            if visit_date is None or start_time is None:
                return error_response(400, 'date must be YYYY-MM-DD and start_time must be HH:MM.')
            appointment, error = AppointmentService().reschedule(appointment_id, visit_date, start_time)
            if error:
                return service_error(error)
            return Response(appointment_payload(appointment))
        except APIException:
            raise
        except Exception as ex:
            lgr.exception('Error rescheduling appointment: %s', ex)
            return Response({'detail': 'General failure.'}, status=500)


urlpatterns = [
    path('appointments', BookAppointment.as_view()),
    path('appointments/<uuid:appointment_id>/cancel', CancelAppointment.as_view()),
    path('appointments/<uuid:appointment_id>/reschedule', RescheduleAppointment.as_view()),
]
