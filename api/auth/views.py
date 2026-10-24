import logging

from django.contrib.auth import authenticate
from django.urls import path
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.errors import error_response

lgr = logging.getLogger(__name__)


class Login(APIView):
    """POST /login"""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        """Logs in the super admin and returns an API token.
		@param request: The HTTP request. Body fields are username and password.
		@type request: Request
		@return: The token and username, or an error response.
		@rtype: Response"""
        try:
            username = request.data.get('username')
            password = request.data.get('password')
            if not isinstance(username, str) or not username.strip() or not isinstance(password, str):
                return error_response(400, 'username and password are required.')
            user = authenticate(username=username.strip(), password=password)
            if user is None or not user.is_active:
                return error_response(401, 'Invalid username or password.')
            token, _ = Token.objects.get_or_create(user=user)
            return Response({'token': token.key, 'username': user.username}, status=200)
        except APIException:
            raise
        except Exception as ex:
            lgr.exception('Error logging in: %s', ex)
            return Response({'detail': 'General failure.'}, status=500)


urlpatterns = [
    path('login', Login.as_view()),
]
