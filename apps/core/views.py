from django.shortcuts import render

from apps.awards.models import Award


def home(request):
    return render(request, "core/home.html", {"events": Award.objects.filter(is_open=True)})
