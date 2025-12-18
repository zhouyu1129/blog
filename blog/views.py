from django.views.decorators.http import require_http_methods
from django.shortcuts import render


@require_http_methods(["GET"])
def index(request):
    return render(request, 'index.html')


@require_http_methods(["GET"])
def about(request):
    return render(request, 'about.html')


def custom_404(request, exception):
    return render(request, '404.html', status=404)
