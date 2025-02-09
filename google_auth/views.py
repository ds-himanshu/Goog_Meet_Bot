import csv
import os
import secrets

import pytz
from django.shortcuts import redirect
from django.http import JsonResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from .models import OAuthToken
from .playwright_google_meet import GoogleMeetAutomation


def get_flow():
    """Initialize and return Google OAuth flow"""
    return Flow.from_client_secrets_file(
        settings.GOOGLE_CLIENT_SECRET_FILE,
        scopes=settings.GOOGLE_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI
    )


def google_login(request):
    """Initiate the OAuth2 authorization flow"""
    flow = get_flow()
    # Generate a random state parameter
    state = secrets.token_urlsafe(32)

    auth_url, _ = flow.authorization_url(
        access_type='offline',
        state=state,
        prompt='consent'
    )

    return redirect(auth_url)


def google_callback(request):
    try:
        flow = get_flow()
        flow.fetch_token(authorization_response=request.build_absolute_uri())
        credentials = flow.credentials

        # Ensure expiry is timezone-aware before saving
        expiry = credentials.expiry
        if expiry.tzinfo is None:
            expiry = timezone.make_aware(expiry)

        # Clear existing tokens and save new one
        OAuthToken.objects.all().delete()
        token_entry = OAuthToken.objects.create(
            token=credentials.token,
            refresh_token=credentials.refresh_token or '',
            token_uri=credentials.token_uri,
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            scopes=','.join(credentials.scopes) if isinstance(credentials.scopes, list) else credentials.scopes,
            universe_domain=getattr(credentials, 'universe_domain', ''),
            account=getattr(credentials, 'account', ''),
            expiry=expiry
        )

        print(f"New token saved. Expiry: {expiry}")
        return JsonResponse({"message": "Authentication successful", "token_id": token_entry.id})

    except Exception as e:
        print(f"Error in callback: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


from django.utils import timezone
from datetime import datetime, timezone as dt_timezone

from google.auth import _helpers


def get_stored_credentials():
    try:
        latest_token = OAuthToken.objects.latest('id')

        # Ensure expiry is timezone-aware
        expiry = latest_token.get_expiry()  # Use the model method
        expiry = expiry.replace(tzinfo=None)
        credentials = Credentials(
            token=latest_token.token,
            refresh_token=latest_token.refresh_token,
            token_uri=latest_token.token_uri,
            client_id=latest_token.client_id,
            client_secret=latest_token.client_secret,
            scopes=latest_token.scopes.split(',') if isinstance(latest_token.scopes, str) else latest_token.scopes,
            expiry=expiry
        )
        return credentials
    except OAuthToken.DoesNotExist:
        return None


def extract_meeting_details(request):
    credentials = get_stored_credentials()

    if not credentials:
        return JsonResponse({"error": "User not authenticated"}, status=401)

    try:
        service = build("calendar", "v3", credentials=credentials)
        now = datetime.now(pytz.UTC)

        events_result = service.events().list(
            calendarId='primary',
            timeMin=now.isoformat(),
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        meeting_details = []

        # Use existing CSV file
        csv_filepath = 'meeting_invites.csv'

        # Define CSV headers
        csv_headers = ['Summary', 'Start Time', 'End Time', 'Meet Link', 'Conference URI']

        # Append to existing CSV file
        with open(csv_filepath, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=csv_headers)

            # If file is empty, write headers
            if os.path.getsize(csv_filepath) == 0:
                writer.writeheader()

            for event in events:
                meeting_info = {
                    'Summary': event.get('summary', 'No Title'),
                    'Start Time': event.get('start', {}).get('dateTime'),
                    'End Time': event.get('end', {}).get('dateTime'),
                    'Meet Link': event.get('hangoutLink', ''),
                    'Conference URI': event.get('conferenceData', {})
                    .get('entryPoints', [{}])[0].get('uri', '')
                }
                meeting_details.append(meeting_info)
                writer.writerow(meeting_info)

        return JsonResponse({
            "meetings": meeting_details,
            "count": len(meeting_details),
            "message": "Meeting details appended to meeting_invites.csv"
        })

    except Exception as e:
        print(f"Calendar API error: {str(e)}")
        return JsonResponse({
            "error": str(e),
            "error_type": type(e).__name__
        }, status=500)


@csrf_exempt
def join_meeting_view(request):
    """Django view to trigger Google Meet automation"""
    if request.method != 'GET':
        return JsonResponse({"error": "GET method required"}, status=405)

    try:
        google_meet = GoogleMeetAutomation()
        response = google_meet.join_google_meet()
        google_meet.close_browser()

        if response["status"] == "success":
            return JsonResponse({
                "status": "success",
                "message": response["message"]
            })
        else:
            return JsonResponse({
                "status": "error",
                "message": response["message"]
            }, status=500)
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)


def cleanup_old_files(directory, max_files=10):
    files = os.listdir(directory)
    if len(files) > max_files:
        files.sort(key=lambda x: os.path.getctime(os.path.join(directory, x)))
        for file in files[:-max_files]:
            os.remove(os.path.join(directory, file))
