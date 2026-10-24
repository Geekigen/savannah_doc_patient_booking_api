import json
import logging
import uuid
from datetime import datetime

from django.http import QueryDict
from rest_framework.response import Response

from base.backend.services import slot_end

lgr = logging.getLogger(__name__)


def parse_uuid(value):
    """Parses a value into a UUID.
		@param value: The raw id from the request.
		@type value: object
		@return: The UUID, or None when the value is not a UUID.
		@rtype: uuid.UUID | None"""
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def parse_date(value):
    """Parses a YYYY-MM-DD string into a date.
		@param value: The raw date from the request.
		@type value: object
		@return: The date, or None when the value is not YYYY-MM-DD.
		@rtype: datetime.date | None"""
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def parse_time(value):
    """Parses an HH:MM or HH:MM:SS string into a time.
		@param value: The raw time from the request.
		@type value: object
		@return: The time, or None when the value is not a time string.
		@rtype: datetime.time | None"""
    if not isinstance(value, str):
        return None
    for fmt in ('%H:%M', '%H:%M:%S'):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def appointment_payload(appointment):
    """Builds the JSON body for one appointment.
		@param appointment: The appointment to describe.
		@type appointment: Appointment
		@return: The appointment fields returned to the client.
		@rtype: dict"""
    start = appointment.slot.start_time
    return {
        'id': str(appointment.id),
        'patient_id': str(appointment.patient_id),
        'doctor_id': str(appointment.slot.doctor_id),
        'date': appointment.date.isoformat(),
        'start_time': start.strftime('%H:%M'),
        'end_time': slot_end(start).strftime('%H:%M'),
        'state': appointment.state.name,
        'cancellation_reason': appointment.cancellation_reason,
    }


def get_request_data(request):
    """Retrieves request data irrespective of the method and content type.
		@param request: The Django or DRF request.
		@type request: Request
		@return: The request payload as a dict.
		@rtype: dict"""
    try:
        if request is None:
            return {}
        if hasattr(request, 'data'):
            data = request.data
            if isinstance(data, QueryDict):
                return data.dict()
            if isinstance(data, dict):
                return dict(data)
        request_meta = getattr(request, 'META', {})
        request_method = getattr(request, 'method', None)
        if request_meta.get('CONTENT_TYPE', '') == 'application/json':
            return json.loads(request.body)
        if str(request_meta.get('CONTENT_TYPE', '')).startswith('multipart/form-data;'):
            return request.POST.copy().dict()
        if request_method == 'GET':
            return request.GET.copy().dict()
        if request_method == 'POST':
            posted = request.POST.copy().dict()
            if posted:
                return posted
        body = getattr(request, 'body', None)
        if body:
            return json.loads(body)
    except Exception as e:
        lgr.exception('get_request_data Exception: %s', e)
    return {}


def api_response(code, message, status=200, **extra):
    """Builds a JSON body with a code, a message, and any extra fields.
		@param code: The application response code.
		@type code: str
		@param message: The human-readable message.
		@type message: str
		@param status: The HTTP status code.
		@type status: int
		@param extra: Additional fields merged into the body.
		@type extra: dict
		@return: The JSON response.
		@rtype: Response"""
    body = {'code': code, 'message': message}
    body.update(extra)
    return Response(body, status=status)
