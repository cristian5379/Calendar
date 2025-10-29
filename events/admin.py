from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Event, Country, Community, Profile, EventType, EventImage


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "start_time", "end_time", "location", "country", "event_type", "is_deleted")
    list_filter = ("start_time", "location", "country", "event_type", "is_deleted")
    search_fields = ("title", "description")


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "country", "community")
    search_fields = ("user__username",)


# Add Profile inline to the User admin so superusers can edit country/community on the user page
User = get_user_model()


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'profile'
    fk_name = 'user'


class CustomUserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)


try:
    admin.site.unregister(User)
except Exception:
    # If the user model wasn't registered, ignore — we'll register below
    pass

try:
    admin.site.register(User, CustomUserAdmin)
except Exception:
    # Avoid failing imports when using a custom user admin elsewhere
    # Admin registration is best-effort; if it fails, the Profile model is still editable via its own admin.
    pass


@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(EventImage)
class EventImageAdmin(admin.ModelAdmin):
    list_display = ("event", "filename", "uploaded_by", "created_at")
    list_filter = ("created_at",)
    # allow admins to search by the event title, uploader username and the
    # stored file path / filename (image field stores the path as a string)
    search_fields = ("event__title", "uploaded_by__username", "image")

    def filename(self, obj):
        """Return only the image filename (not full upload path)."""
        try:
            return obj.image.name.rsplit('/', 1)[-1]
        except Exception:
            return ''
    filename.short_description = 'Filename'
