# events/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from .models import Event
from .forms import EventForm


def home_view(request):
    """Home page that allows inline login when anonymous.

    POST: attempts to authenticate using AuthenticationForm. On success, logs the user in and redirects to `next` or calendar.
    GET: displays the page with an empty AuthenticationForm.
    """
    next_url = request.POST.get('next') or request.GET.get('next') or reverse('calendar')

    if request.method == 'POST' and not request.user.is_authenticated:
        form = AuthenticationForm(request, data=request.POST)
        # ensure the fields have bootstrap classes even after validation failure
        form.fields['username'].widget.attrs.update({"class": "form-control", "autofocus": "autofocus"})
        form.fields['password'].widget.attrs.update({"class": "form-control"})
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect(next_url)
    else:
        form = AuthenticationForm(request)
        # set widget attrs for GET form
        form.fields['username'].widget.attrs.update({"class": "form-control", "autofocus": "autofocus"})
        form.fields['password'].widget.attrs.update({"class": "form-control"})

    return render(request, "events/home.html", {"form": form})


def calendar_view(request):
    events = Event.objects.all().order_by("start_time")
    return render(request, "events/calendar.html", {"events": events})


@login_required
def myevents_view(request):
    """List and create/delete events for the logged-in user."""
    user = request.user

    # handle create
    if request.method == 'POST' and request.POST.get('action') == 'create':
        form = EventForm(request.POST)
        if form.is_valid():
            ev = form.save(commit=False)
            ev.owner = user
            ev.save()
            return redirect('myevents')
    elif request.method == 'POST' and request.POST.get('action') == 'delete':
        ev_id = request.POST.get('event_id')
        ev = get_object_or_404(Event, id=ev_id, owner=user)
        ev.delete()
        return redirect('myevents')
    else:
        form = EventForm()

    events = Event.objects.filter(owner=user).order_by('start_time')
    return render(request, "events/myevents.html", {"events": events, "form": form})


def events_json(request):
    data = [{
        "id": e.id,
        "title": e.title,
        "start": e.start_time.isoformat(),
        "end": e.end_time.isoformat(),
    } for e in Event.objects.all()]
    return JsonResponse(data, safe=False)
