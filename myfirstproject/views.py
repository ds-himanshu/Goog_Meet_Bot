# import os
# from django.shortcuts import redirect
# from google_auth_oauthlib.flow import Flow
# from django.conf import settings
# from django.views.decorators.csrf import csrf_exempt
# from .playwright_google_meet import GoogleMeetAutomation
# from google_auth.models import OAuthToken
#
# flow = Flow.from_client_secrets_file(
#     settings.GOOGLE_CLIENT_SECRET_FILE,
#     scopes=settings.GOOGLE_SCOPES,
#     redirect_uri=settings.GOOGLE_REDIRECT_URI
# )
#
#
# def google_login(request):
#     auth_url, _ = flow.authorization_url(prompt='consent')
#     return redirect(auth_url)
#
#
# def google_callback(request):
#     # Optional: Clear previous tokens if you want only one active token
#     OAuthToken.objects.all().delete()
#
#     flow.fetch_token(authorization_response=request.build_absolute_uri())
#     credentials = flow.credentials
#
#     # Create and save the token to the database
#     token_entry = OAuthToken.objects.create(
#         token=credentials.token,
#         refresh_token=credentials.refresh_token,
#         token_uri=credentials.token_uri,
#         client_id=credentials.client_id,
#         client_secret=credentials.client_secret,
#         scopes=credentials.scopes,
#         universe_domain=credentials.universe_domain,
#         account=getattr(credentials, 'account', ''),
#         expiry=credentials.expiry
#     )
#
#     return JsonResponse({"message": "Google Authentication Successful"})
#
#
# # def get_calendar_events(request):
# #     creds_data = request.session.get('credentials')
# #
# #     if not creds_data:
# #         return JsonResponse({"error": "User not authenticated"}, status=401)
# #
# #     creds = Credentials(**creds_data)
# #     service = build("calendar", "v3", credentials=creds)
# #
# #     events_result = service.events().list(calendarId='primary', maxResults=10).execute()
# #     events = events_result.get("items", [])
# #
# #     return JsonResponse({"events": events})
#
# import os
# import csv
# from django.conf import settings
# from django.http import HttpResponse, JsonResponse
# from google_auth_oauthlib.flow import Flow
# from google.oauth2.credentials import Credentials
# from googleapiclient.discovery import build
# from google.auth.exceptions import RefreshError
# from google.auth.transport.requests import Request
#
#
# def extract_meeting_details(request):
#     creds_data = request.session.get('credentials')
#
#     if not creds_data:
#         return JsonResponse({"error": "User not authenticated"}, status=401)
#
#     creds = Credentials(**creds_data)
#     service = build("calendar", "v3", credentials=creds)
#
#     events_result = service.events().list(calendarId='primary', maxResults=10).execute()
#     events = events_result.get("items", [])
#
#     meeting_details = []
#     for event in events:
#         meeting_info = {
#             'summary': event.get('summary', 'No Title'),
#             'start_time': event.get('start', {}).get('dateTime'),
#             'end_time': event.get('end', {}).get('dateTime'),
#             'meet_link': event.get('hangoutLink'),
#             'conference_uri': event.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri')
#         }
#         meeting_details.append(meeting_info)
#
#     # CSV Export
#     csv_filename = os.path.join(settings.BASE_DIR, 'meeting_invites.csv')
#     with open(csv_filename, 'w', newline='') as csvfile:
#         fieldnames = ['summary', 'start_time', 'end_time', 'meet_link', 'conference_uri']
#         writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
#
#         writer.writeheader()
#         for meeting in meeting_details:
#             writer.writerow(meeting)
#
#     return JsonResponse({
#         "meetings": meeting_details,
#         "csv_path": csv_filename
#     })
#
#
# @csrf_exempt
# def join_meeting_view(request):
#     """Django view to trigger Google Meet automation."""
#     if request.method == 'GET':
#         google_meet = GoogleMeetAutomation()
#         response = google_meet.join_google_meet()
#
#         # Close the browser once the meeting process is done
#         google_meet.close_browser()
#
#         # Return the response from Google Meet automation
#         if response["status"] == "success":
#             return JsonResponse({
#                 "status": "success",
#                 "message": response["message"]
#             })
#         else:
#             return JsonResponse({
#                 "status": "error",
#                 "message": response["message"]
#             }, status=500)
#
#     return JsonResponse({"error": "GET method required"}, status=405)
#
#
# def get_stored_credentials():
#     try:
#         latest_token = OAuthToken.objects.latest('id')
#         credentials = Credentials(
#             token=latest_token.token,
#             refresh_token=latest_token.refresh_token,
#             token_uri=latest_token.token_uri,
#             client_id=latest_token.client_id,
#             client_secret=latest_token.client_secret,
#             scopes=latest_token.scopes,
#             expiry=latest_token.expiry
#         )
#
#         # Check if token needs refresh
#         if credentials.expired:
#             try:
#                 credentials.refresh(Request())
#                 # Update stored token
#                 latest_token.token = credentials.token
#                 latest_token.expiry = credentials.expiry
#                 latest_token.save()
#             except RefreshError:
#                 return None
#
#         return credentials
#     except OAuthToken.DoesNotExist:
#         return None
