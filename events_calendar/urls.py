"""
URL configuration for events_calendar project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.contrib.auth.views import LogoutView
from django.views.generic.base import RedirectView
from events.views import home_view, calendar_view, events_json, myevents_view, register_view, event_detail, participate_event, event_edit, edit_profile
from events.views import participated_view, mark_attendance, organized_view, upload_event_image, event_gallery
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', home_view, name='home'),
    path('myevents/', myevents_view, name='myevents'),
    path('myevents/participated/', participated_view, name='participated_events'),
    path('myevents/organized/', organized_view, name='organized_events'),
    path('events/<int:event_id>/attendace/', mark_attendance, name='mark_attendance'),
    # provide a logout view that redirects back to the calendar after logging out
    path('accounts/logout/', LogoutView.as_view(next_page='/calendar/'), name='logout'),
    path('accounts/register/', register_view, name='register'),
    # redirect any direct /accounts/login/ access back to the home page
    path('accounts/login/', RedirectView.as_view(pattern_name='home', permanent=False), name='login'),
    # include remaining auth views (password reset etc.)
    path('accounts/', include('django.contrib.auth.urls')),
    path("calendar/", calendar_view, name="calendar"),
    path("events-json/", events_json, name="events_json"),
    path("events/<int:event_id>/", event_detail, name="event_detail"),
        path("events/<int:event_id>/edit/", event_edit, name="event_edit"),
    path("events/<int:event_id>/gallery/", event_gallery, name="event_gallery"),
    path("events/<int:event_id>/upload-image/", upload_event_image, name="upload_event_image"),
    path("events/<int:event_id>/participate/", participate_event, name="event_participate"),
    path('accounts/profile/edit/', edit_profile, name='edit_profile'),
]

# serve user-uploaded media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
