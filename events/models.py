from django.db import models
from django.conf import settings

class Event(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='events'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)  # set once when created
    updated_at = models.DateTimeField(auto_now=True)      # updates on every save

    # soft-delete fields: mark an event as deleted without removing it from the DB
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='deleted_events'
    )

    # users who are participating in this event ( RSVPs / attendees )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='participating_events'
    )

    # additional organizers (the owner is the primary organizer)
    organizers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='organized_events'
    )

    # users who were marked as present by the organizer after the event finished
    attendees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='attended_events'
    )

    # event location scope: country and targeted communities
    country = models.ForeignKey(
        'Country',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='events'
    )

    targeted_communities = models.ManyToManyField(
        'Community',
        blank=True,
        related_name='targeted_events'
    )

    # optional event type (managed by admins)
    event_type = models.ForeignKey(
        'EventType',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='events'
    )

    def __str__(self):
        return f"{self.title} ({self.start_time:%Y-%m-%d %H:%M})"


class EventType(models.Model):
    """Admin-manageable preset types for events (e.g., Workshop, Meetup, Webinar)."""
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Event type'
        verbose_name_plural = 'Event types'

    def __str__(self):
        return self.name


class EventImage(models.Model):
    """Image uploaded by users for a specific event."""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='event_images/%Y/%m/%d')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='uploaded_images'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Image for {self.event.title} by {self.uploaded_by or 'anonymous'}"


class Country(models.Model):
    """A country that users can select for their profile. Managed by admin."""
    name = models.CharField(max_length=200, unique=True)

    class Meta:
        verbose_name_plural = "countries"

    def __str__(self):
        return self.name


class Community(models.Model):
    """A community/region/organization users belong to. Managed by admin."""
    name = models.CharField(max_length=200, unique=True)

    class Meta:
        verbose_name_plural = "communities"

    def __str__(self):
        return self.name


class Profile(models.Model):
    """Profile extension for User to store country and community choices."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    # allow null so existing users can be left unset and updated by admin later
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    community = models.ForeignKey(Community, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Profile for {self.user.username}"
