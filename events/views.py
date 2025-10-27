# events/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Event
from .forms import EventForm
from django.utils import timezone
from django.urls import reverse


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


def register_view(request):
    """Simple registration view that only requires username and password.

    Uses Django's UserCreationForm (which asks for username, password1, password2).
    On success the new user is logged in and redirected to the calendar.
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        # add bootstrap classes to widgets so form renders consistently
        for fld in form.fields.values():
            fld.widget.attrs.update({"class": "form-control"})
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(reverse('calendar'))
    else:
        form = UserCreationForm()
        for fld in form.fields.values():
            fld.widget.attrs.update({"class": "form-control"})

    return render(request, 'registration/register.html', {'form': form})


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
            messages.success(request, 'Event created.')
            return redirect('myevents')
        else:
            messages.error(request, 'There were errors creating the event. Please check the form below.')
    elif request.method == 'POST' and request.POST.get('action') == 'delete':
        ev_id = request.POST.get('event_id')
        ev = get_object_or_404(Event, id=ev_id, owner=user)
        ev.delete()
        messages.success(request, 'Event deleted.')
        return redirect('myevents')
    elif request.method == 'POST' and request.POST.get('action') == 'join':
        ev_id = request.POST.get('event_id')
        ev = get_object_or_404(Event, id=ev_id)
        ev.participants.add(user)
        # Do not show a flash message when joining from the My Events page
        return redirect('myevents')
    elif request.method == 'POST' and request.POST.get('action') == 'leave':
        ev_id = request.POST.get('event_id')
        ev = get_object_or_404(Event, id=ev_id)
        ev.participants.remove(user)
        # Do not show a flash message when leaving from the My Events page
        return redirect('myevents')
    else:
        form = EventForm()

    # Owned events
    # Only show upcoming events that the user is hosting (end_time >= now)
    now = timezone.now()
    events = Event.objects.filter(owner=user, end_time__gte=now).order_by('start_time')

    # Events where the user is a participant
    now = timezone.now()
    participating_upcoming = Event.objects.filter(participants=user, end_time__gte=now).order_by('start_time')
    participated_past = Event.objects.filter(participants=user, end_time__lt=now).order_by('-start_time')

    return render(request, "events/myevents.html", {
        "events": events,
        "participating": participating_upcoming,
        "participated": participated_past,
        "form": form
    })


def events_json(request):
    data = []
    for e in Event.objects.all():
        # expand multi-day events into per-day entries so they appear on each day in the calendar
        start_date = e.start_time.date()
        end_date = e.end_time.date()
        current = start_date
        while current <= end_date:
            # combine the original times with the current date
            start_dt = datetime.combine(current, e.start_time.time())
            end_dt = datetime.combine(current, e.end_time.time())
            data.append({
                "id": f"{e.id}-{current.isoformat()}",
                "orig_id": e.id,
                "title": e.title,
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "description": e.description,
                "participants": e.participants.count(),
                "joined": request.user.is_authenticated and e.participants.filter(id=request.user.id).exists(),
                "location": e.location,
            })
            current = current + timedelta(days=1)
    return JsonResponse(data, safe=False)


def participate_event(request, event_id):
    """AJAX endpoint to join/leave an event. Returns JSON with joined state and participants count."""
    ev = get_object_or_404(Event, id=event_id)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "login_required"}, status=401)

    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=405)

    action = request.POST.get('action')
    if action == 'join':
        ev.participants.add(request.user)
    elif action == 'leave':
        ev.participants.remove(request.user)
    else:
        return JsonResponse({"error": "invalid_action"}, status=400)

    return JsonResponse({
        "joined": ev.participants.filter(id=request.user.id).exists(),
        "participants": ev.participants.count()
    })


def event_detail(request, event_id):
    ev = get_object_or_404(Event, id=event_id)

    # handle join/leave from the detail page
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in to join or leave events.')
            return redirect('login')

        action = request.POST.get('action')
        if action == 'join':
            ev.participants.add(request.user)
            messages.success(request, 'You are now participating in this event.')
            return redirect(reverse('event_detail', args=[ev.id]))
        elif action == 'leave':
            ev.participants.remove(request.user)
            messages.success(request, 'You have left this event.')
            return redirect(reverse('event_detail', args=[ev.id]))

    return render(request, 'events/event_detail.html', {'event': ev})
