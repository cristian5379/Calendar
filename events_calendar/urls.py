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
from events.views import home_view, calendar_view, events_json, myevents_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', home_view, name='home'),
    path('myevents/', myevents_view, name='myevents'),
    # provide a logout view that redirects back to the calendar after logging out
    path('accounts/logout/', LogoutView.as_view(next_page='/calendar/'), name='logout'),
    # include auth views (login etc.) at /accounts/
    path('accounts/', include('django.contrib.auth.urls')),
    path("calendar/", calendar_view, name="calendar"),
    path("events-json/", events_json, name="events_json"),
]
