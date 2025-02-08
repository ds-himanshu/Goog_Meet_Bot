import os
import logging
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from playwright.sync_api import sync_playwright

# Set up logging
logger = logging.getLogger(__name__)

class PlaywrightSessionManager:
    """Class to manage Google login session with Playwright"""

    SESSION_FILE = os.path.join(settings.BASE_DIR, "google_session.json")

    @classmethod
    def save_google_session(cls):
        """Launch Playwright browser, allow manual login, and save session"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)  # Open browser
                context = browser.new_context()
                page = context.new_page()

                # Navigate to Google login
                page.goto("https://meet.google.com/uao-bfxf-ewp")

                # Pause to allow manual login
                print("Please log in manually and then close the browser.")
                page.pause()

                # Save session state
                context.storage_state(path=cls.SESSION_FILE)
                logger.info(f"Session saved at {cls.SESSION_FILE}")

                # Close browser
                browser.close()

            return cls.SESSION_FILE  # Return session path

        except Exception as e:
            logger.error(f"Error in Playwright login: {str(e)}")
            raise Exception("Failed to save session. Check logs for details.")

def save_google_session_view(request):
    """Django view to trigger Playwright session-saving on GET request"""
    if request.method != "GET":
        return JsonResponse({"error": "GET method required"}, status=405)

    try:
        session_file = PlaywrightSessionManager.save_google_session()
        return JsonResponse({"message": "Session saved successfully", "session_path": session_file})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


