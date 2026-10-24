from rest_framework.response import Response
from rest_framework.views import exception_handler

CLIENT_ERRORS = {
    400: 'Bad Request',
    401: 'Unauthorized',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    409: 'Conflict',
}

SERVICE_ERRORS = {
    'outside_hours': (409, "That time is outside the doctor's working hours."),
    'in_the_past': (409, 'That time is in the past.'),
    'within_hour': (409, 'Bookings must start at least one hour from now.'),
    'taken': (409, 'That slot is already taken.'),
    'already_cancelled': (409, 'Appointment is already cancelled.'),
    'doctor_not_found': (404, 'Doctor was not found.'),
    'patient_not_found': (404, 'Patient was not found.'),
    'not_found': (404, 'Appointment was not found.'),
}


def error_response(status, message, headers=None):
    """Builds an error body with status, error name, and message.
		@param status: The HTTP status code.
		@type status: int
		@param message: The specific reason this request failed.
		@type message: str
		@param headers: Extra response headers, such as Allow.
		@type headers: dict | None
		@return: The error response.
		@rtype: Response"""
    return Response(
        {
            'status': status,
            'error': CLIENT_ERRORS[status],
            'message': message,
        },
        status=status,
        headers=headers,
    )


def service_error(code):
    """Turns a service error code into the matching HTTP error response.
		@param code: The error code returned by a service.
		@type code: str
		@return: The error response.
		@rtype: Response"""
    status, message = SERVICE_ERRORS[code]
    return error_response(status, message)


def standard_exception_handler(exc, context):
    """Shapes framework errors with status, error, and message.
		@param exc: The exception raised while handling the request.
		@type exc: Exception
		@param context: The request context from Django REST framework.
		@type context: dict
		@return: The formatted error response, or None when the framework does not handle it.
		@rtype: Response | None"""
    response = exception_handler(exc, context)
    if response is None or response.status_code not in CLIENT_ERRORS:
        return response
    message = response.data.get('detail', response.data) if isinstance(response.data, dict) else response.data
    if not isinstance(message, str):
        message = str(message)
    headers = {}
    allow = response.headers.get('Allow')
    if allow:
        headers['Allow'] = allow
    return error_response(response.status_code, message, headers=headers)
