from django.urls import path
from django.http import HttpResponse
from google_auth.views import (
    google_login,
    google_callback,
    extract_meeting_details,
    join_meeting_view
)

urlpatterns = [
    path('auth/google/login/', google_login, name='google_login'),
    path('auth/google/callback/', google_callback, name='google_callback'),
    path('auth/google/calendar/', extract_meeting_details, name='google_calendar'),
    path('auth/playwright/join-meeting/', join_meeting_view, name='join_google_meet'),
]