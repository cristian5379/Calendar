# events/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from .forms import RegistrationForm
from django.urls import reverse
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Event, Country, Community
from .forms import EventForm, ProfileForm
from django.utils import timezone
from django.db.models import Q
from django.urls import reverse
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth import login as auth_login
from .forms import NameLoginForm
from .forms import EventImageForm
from .models import EventImage
from django.views.decorators.http import require_POST
from django.shortcuts import resolve_url

# Bucharest sectors used in several places (calendar filters, events filtering, and forms)
BUCHAREST_SECTORS = ['Sector 1', 'Sector 2', 'Sector 3', 'Sector 4', 'Sector 5', 'Sector 6']


def home_view(request):
    """Home page that allows inline login when anonymous.

    POST: attempts to authenticate using AuthenticationForm. On success, logs the user in and redirects to `next` or calendar.
    GET: displays the page with an empty AuthenticationForm.
    """
    next_url = request.POST.get('next') or request.GET.get('next') or reverse('calendar')

    if request.method == 'POST' and not request.user.is_authenticated:
        form = NameLoginForm(request.POST)
        # ensure fields have bootstrap classes
        if form.is_valid():
            email = form.cleaned_data['email'].strip()
            password = form.cleaned_data['password']
            User = get_user_model()
            matches = User.objects.filter(email__iexact=email)
            if matches.count() == 1:
                user_obj = matches.first()
                user = authenticate(request, username=user_obj.username, password=password)
                if user is not None:
                    auth_login(request, user)
                    return redirect(next_url)
                else:
                    form.add_error(None, 'Invalid password.')
            elif matches.count() == 0:
                form.add_error(None, 'No account found with that email. Please check the email or register.')
            else:
                form.add_error(None, 'Multiple accounts found with that email. Please contact admin.')
    else:
        form = NameLoginForm()

    return render(request, "events/home.html", {"form": form})


def register_view(request):
    """Simple registration view that only requires username and password.

    Uses Django's UserCreationForm (which asks for username, password1, password2).
    On success the new user is logged in and redirected to the calendar.
    """
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(reverse('calendar'))
    else:
        form = RegistrationForm()

    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    """Custom login view that accepts first_name + last_name + password and maps them to a username."""
    next_url = request.POST.get('next') or request.GET.get('next') or reverse('calendar')

    if request.method == 'POST':
        form = NameLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip()
            password = form.cleaned_data['password']

            # find matching users (case-insensitive)
            User = get_user_model()
            matches = User.objects.filter(email__iexact=email)

            if matches.count() == 0:
                form.add_error(None, 'No account found with that email. Please check the email or register.')
            elif matches.count() > 1:
                form.add_error(None, 'Multiple accounts found with that email. Please sign in with your username or contact admin.')
            else:
                user = matches.first()
                user = authenticate(request, username=user.username, password=password)
                if user is None:
                    form.add_error(None, 'Invalid password.')
                else:
                    auth_login(request, user)
                    return redirect(next_url)
    else:
        form = NameLoginForm()

    return render(request, 'registration/login.html', {'form': form, 'next': request.GET.get('next', '')})


def calendar_view(request):
    # pass available countries and communities for the calendar filters
    countries = Country.objects.all().order_by('name')
    communities = Community.objects.all().order_by('name')
    # pass along any current selections so template can pre-select them
    selected_country = request.GET.get('country', '')
    selected_community = request.GET.get('community', '')
    # define Bucharest sectors for the template to render the optgroup
    sectors_list = BUCHAREST_SECTORS

    return render(request, "events/calendar.html", {
        "countries": countries,
        "communities": communities,
        "selected_country": selected_country,
        "selected_community": selected_community,
        "sectors_list": sectors_list,
    })


@login_required
def myevents_view(request):
    """List and create/delete events for the logged-in user."""
    user = request.user

    # handle create
    if request.method == 'POST' and request.POST.get('action') == 'create':
        # allow the special 'bucharest' aggregate value from the UI; expand it to the
        # actual sector community ids so the ModelMultipleChoiceField accepts them.
        posted = request.POST.copy()
        if 'targeted_communities' in posted:
            vals = posted.getlist('targeted_communities')
            if 'bucharest' in vals:
                sector_ids = list(Community.objects.filter(name__in=BUCHAREST_SECTORS).values_list('id', flat=True))
                # remove the 'bucharest' token and append the numeric ids
                new_vals = [v for v in vals if v != 'bucharest'] + [str(i) for i in sector_ids]
                posted.setlist('targeted_communities', new_vals)

        form = EventForm(posted)
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
        ev = get_object_or_404(Event, id=ev_id, owner=user, is_deleted=False)
        # soft-delete: mark the event as deleted so it no longer appears for anyone
        ev.is_deleted = True
        ev.deleted_at = timezone.now()
        ev.deleted_by = user
        ev.save()
        messages.success(request, 'Event deleted (hidden).')
        return redirect('myevents')
    elif request.method == 'POST' and request.POST.get('action') == 'join':
        ev_id = request.POST.get('event_id')
        ev = get_object_or_404(Event, id=ev_id, is_deleted=False)
        ev.participants.add(user)
        # Do not show a flash message when joining from the My Events page
        return redirect('myevents')
    elif request.method == 'POST' and request.POST.get('action') == 'leave':
        ev_id = request.POST.get('event_id')
        ev = get_object_or_404(Event, id=ev_id, is_deleted=False)
        ev.participants.remove(user)
        # Do not show a flash message when leaving from the My Events page
        return redirect('myevents')
    else:
        form = EventForm()

    # Owned events
    # Only show upcoming events that the user is hosting (end_time >= now)
    now = timezone.now()
    events = Event.objects.filter(owner=user, end_time__gte=now, is_deleted=False).order_by('start_time')

    # Events where the user is a participant
    now = timezone.now()
    participating_upcoming = Event.objects.filter(participants=user, end_time__gte=now, is_deleted=False).order_by('start_time')
    # participated (past) events are now shown on a separate page
    participated_past = Event.objects.none()

    # pass communities and sectors list so the template can render the custom multi-select
    communities = Community.objects.all().order_by('name')
    # determine selected targeted communities to pre-select options in the template
    if request.method == 'POST' and request.POST.get('action') == 'create':
        # use the posted copy we prepared earlier if present
        selected_targeted = posted.getlist('targeted_communities') if 'posted' in locals() else request.POST.getlist('targeted_communities')
    else:
        selected_targeted = []

    return render(request, "events/myevents.html", {
        "events": events,
        "participating": participating_upcoming,
        "form": form,
        "communities": communities,
        "sectors_list": BUCHAREST_SECTORS,
        "selected_targeted": selected_targeted,
    })


def events_json(request):
    data = []
    qs = Event.objects.filter(is_deleted=False)
    # apply optional filters from querystring
    country = request.GET.get('country')
    community = request.GET.get('community')
    if country:
        try:
            cid = int(country)
            qs = qs.filter(country_id=cid)
        except ValueError:
            pass
    if community:
        # special aggregate for Bucharest which includes six sectors
        if community == 'bucharest':
            qs = qs.filter(targeted_communities__name__in=BUCHAREST_SECTORS)
        else:
            try:
                comid = int(community)
                qs = qs.filter(targeted_communities__id=comid)
            except ValueError:
                pass

    # avoid duplicates when filtering across M2M
    qs = qs.distinct()

    for e in qs.order_by('start_time'):
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
                "type": e.event_type.name if e.event_type else None,
                "participants": e.participants.count(),
                "joined": request.user.is_authenticated and e.participants.filter(id=request.user.id).exists(),
                "location": e.location,
            })
            current = current + timedelta(days=1)
    return JsonResponse(data, safe=False)


def participate_event(request, event_id):
    """AJAX endpoint to join/leave an event. Returns JSON with joined state and participants count."""
    ev = get_object_or_404(Event, id=event_id, is_deleted=False)
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
    ev = get_object_or_404(Event, id=event_id, is_deleted=False)

    # images and upload form
    images = ev.images.all()
    upload_form = EventImageForm()

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

    return render(request, 'events/event_detail.html', {'event': ev, 'now': timezone.now(), 'images': images, 'upload_form': upload_form})


@login_required
@require_POST
def upload_event_image(request, event_id):
    """Handle image uploads for a specific event. Only authenticated users may upload."""
    ev = get_object_or_404(Event, id=event_id, is_deleted=False)
    form = EventImageForm(request.POST, request.FILES)
    if form.is_valid():
        img = form.save(commit=False)
        img.event = ev
        img.uploaded_by = request.user
        img.save()
        messages.success(request, 'Photo uploaded.')
    else:
        messages.error(request, 'Failed to upload photo. Please ensure the file is a valid image.')
    return redirect(resolve_url('event_detail', event_id=event_id))


def event_gallery(request, event_id):
    ev = get_object_or_404(Event, id=event_id, is_deleted=False)
    images = ev.images.all()
    return render(request, 'events/event_gallery.html', {'event': ev, 'images': images})


@login_required
def event_edit(request, event_id):
    """Allow the owner/organizer to edit an event."""
    ev = get_object_or_404(Event, id=event_id, is_deleted=False)

    # allow the owner or any existing organizer to edit the event
    is_owner = (ev.owner and ev.owner.id == request.user.id)
    is_organizer = ev.organizers.filter(id=request.user.id).exists()
    if not (is_owner or is_organizer):
        messages.error(request, 'You do not have permission to edit this event.')
        return redirect('calendar')

    if request.method == 'POST':
        # expand 'bucharest' aggregate into the actual sector ids before binding the form
        posted = request.POST.copy()
        if 'targeted_communities' in posted:
            vals = posted.getlist('targeted_communities')
            if 'bucharest' in vals:
                sector_ids = list(Community.objects.filter(name__in=BUCHAREST_SECTORS).values_list('id', flat=True))
                new_vals = [v for v in vals if v != 'bucharest'] + [str(i) for i in sector_ids]
                posted.setlist('targeted_communities', new_vals)

        form = EventForm(posted, instance=ev)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event updated.')
            return redirect('myevents')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = EventForm(instance=ev)

    # supply communities and sectors_list for the custom multi-select rendering and
    # compute selected_targeted to pre-select options (from POST when bound, else from instance)
    communities = Community.objects.all().order_by('name')
    if request.method == 'POST':
        selected_targeted = posted.getlist('targeted_communities') if 'posted' in locals() else request.POST.getlist('targeted_communities')
    else:
        selected_targeted = [str(c.id) for c in ev.targeted_communities.all()]

    return render(request, 'events/event_edit.html', {'form': form, 'event': ev, 'communities': communities, 'sectors_list': BUCHAREST_SECTORS, 'selected_targeted': selected_targeted})



@login_required
def edit_profile(request):
    """Allow the logged-in user to edit their profile (country/community)."""
    # ensure a Profile exists for the user (create if missing)
    profile, created = None, False
    try:
        profile = request.user.profile
    except Exception:
        # lazy-create an empty profile; country/community are nullable
        from .models import Profile
        profile = Profile.objects.create(user=request.user)
        created = True

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('myevents')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'events/profile_edit.html', {'form': form})


@login_required
def participated_view(request):
    """Show events the user has participated in (past events)."""
    user = request.user
    now = timezone.now()
    participated = Event.objects.filter(participants=user, end_time__lt=now, is_deleted=False).order_by('-start_time')
    return render(request, 'events/participated.html', {'participated': participated})


@login_required
def organized_view(request):
    """Show past events where the user was the owner or an organizer."""
    user = request.user
    now = timezone.now()
    # include events where the user is the owner or listed in the organizers M2M
    organized = Event.objects.filter(
        Q(owner=user) | Q(organizers=user),
        end_time__lt=now,
        is_deleted=False
    ).distinct().order_by('-start_time')

    return render(request, 'events/organized.html', {'organized': organized})


@login_required
def mark_attendance(request, event_id):
    """Allow the event owner to mark which participants actually attended (Attendace).

    Only available after the event end_time. Saves selected users to Event.attendees.
    """
    ev = get_object_or_404(Event, id=event_id, owner=request.user, is_deleted=False)
    now = timezone.now()
    if ev.end_time > now:
        messages.error(request, 'Attendace can only be managed after the event has finished.')
        return redirect('event_detail', event_id=ev.id)

    participants = ev.participants.all()

    if request.method == 'POST':
        # expected data: checkbox inputs named 'user_<id>' with value 'on' when checked
        selected_ids = [int(k.split('_', 1)[1]) for k, v in request.POST.items() if k.startswith('user_')]
        # ensure only participants can be marked
        valid_ids = [u.id for u in participants if u.id in selected_ids]
        ev.attendees.set(valid_ids)
        messages.success(request, 'Attendace updated.')
        return redirect('event_detail', event_id=ev.id)

    return render(request, 'events/attendace.html', {'event': ev, 'participants': participants})
