import logging

from django.urls import path
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView

from api.errors import error_response, service_error
from api.utility.common import parse_date
from base.backend.services import AppointmentService, DoctorService, slot_end

lgr = logging.getLogger(__name__)


class ListDoctors(APIView):
    """GET /doctors"""

    def get(self, request):
        """Lists every doctor for the authenticated admin.
		@param request: The HTTP request.
		@type request: Request
		@return: The doctors without passwords.
		@rtype: Response"""
        try:
            doctors = DoctorService().filter()
            doctors = [] if doctors is None else doctors.order_by('name')
            return Response({
                'doctors': [
                    {
                        'id': str(doctor.id),
                        'name': doctor.name,
                        'date_created': doctor.date_created.isoformat(),
                    }
                    for doctor in doctors
                ],
            })
        except Exception as ex:
            lgr.exception('Error listing doctors: %s', ex)
            return Response({'detail': 'General failure.'}, status=500)


class DoctorAvailability(APIView):
    """GET /doctors/{id}/availability?date="""

    def get(self, request, doctor_id):
        """Returns the free 30-minute slots for a doctor on a date.
		@param request: The HTTP request. Query field is date, as YYYY-MM-DD.
		@type request: Request
		@param doctor_id: The doctor whose availability is requested.
		@type doctor_id: uuid.UUID
		@return: The free slots, or an error response.
		@rtype: Response"""
        try:
            visit_date = parse_date(request.query_params.get('date'))
            if not request.query_params.get('date'):
                return error_response(400, 'date is required.')
            if visit_date is None:
                return error_response(400, 'date must be YYYY-MM-DD.')
            slots, error = AppointmentService().availability(doctor_id, visit_date)
            if error:
                return service_error(error)
            return Response({
                'doctor_id': str(doctor_id),
                'date': visit_date.isoformat(),
                'slots': [
                    {
                        'start_time': slot.start_time.strftime('%H:%M'),
                        'end_time': slot_end(slot.start_time).strftime('%H:%M'),
                    }
                    for slot in slots
                ],
            })
        except APIException:
            raise
        except Exception as ex:
            lgr.exception('Error reading availability: %s', ex)
            return Response({'detail': 'General failure.'}, status=500)


urlpatterns = [
    path('doctors', ListDoctors.as_view()),
    path('doctors/<uuid:doctor_id>/availability', DoctorAvailability.as_view()),
]
