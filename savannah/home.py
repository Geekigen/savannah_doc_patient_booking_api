from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def home(request):
    """Renders a short HTML note that this project is a REST API.
		@param request: The HTTP request.
		@type request: HttpRequest
		@return: The landing page.
		@rtype: HttpResponse"""
    return render(request, 'home.html')


@require_GET
def postman_collection(request):
    """Serves the Postman collection file for download.
		@param request: The HTTP request.
		@type request: HttpRequest
		@return: The collection JSON as a download.
		@rtype: FileResponse"""
    path = Path(settings.BASE_DIR) / 'docs' / 'savannah.postman_collection.json'
    if not path.is_file():
        raise Http404('Postman collection was not found.')
    return FileResponse(
        path.open('rb'),
        as_attachment=True,
        filename='savannah.postman_collection.json',
        content_type='application/json',
    )
