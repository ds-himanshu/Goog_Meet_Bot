import os
import json
from playwright.sync_api import sync_playwright
from django.conf import settings
import logging

# Setup logger
logger = logging.getLogger(__name__)

class GoogleMeetAutomation:
    """Class to automate joining a Google Meet and starting recording."""


    MEETING_LINK = "https://meet.google.com/uod-gvhc-wtk?authuser=0"
    SESSION_FILE = os.path.join(settings.BASE_DIR, 'google_session.json')  # Path to store session file

    def __init__(self):
        """Initialize the automation class."""
        self.browser = None
        self.context = None

    def join_google_meet(self):
        """Automates the process of joining a Google Meet and starting a recording."""
        try:
            with sync_playwright() as p:
                # Launch the browser and grant permissions
                self.browser = p.chromium.launch(headless=False)
                permissions = ["microphone", "camera"]

                # Check and load session if exists
                if os.path.exists(self.SESSION_FILE):
                    try:
                        self.context = self.browser.new_context(storage_state=self.SESSION_FILE)
                        logger.info("Loaded session from file.")
                    except Exception as e:
                        logger.error(f"Failed to load session: {e}. Creating a new context.")
                        self.context = self.browser.new_context()
                    self.context.grant_permissions(permissions, origin="https://meet.google.com")
                else:
                    logger.info("Session file not found. Creating a new context.")
                    self.context = self.browser.new_context()

                # Open the page and join the meeting
                page = self.context.new_page()
                page.goto(self.MEETING_LINK)

                # Automate the joining process
                page.wait_for_selector("//span[contains(text(),'Join now')]/..", timeout=10000)
                page.click("//span[contains(text(),'Join now')]/..")
                logger.info("Successfully joined the meeting!")

                # Record the meeting if possible
                page.wait_for_selector("(//button[@aria-label='More options'])[2]", timeout=10000)
                page.click("(//button[@aria-label='More options'])[2]")
                page.wait_for_selector("//*[text()='radio_button_checked']/ancestor::li", timeout=10000)
                page.click("//*[text()='radio_button_checked']/ancestor::li")
                page.click("//input[@type='checkbox']")

                try:
                    page.click("//*[text()='Start recording']")
                    page.click("//*[text()='Start']")
                except Exception:
                    page.click("//*[text()='Start']")

                logger.info("Meeting joined and recording started.")

                # Wait for all pages to close before exiting
                while len(self.context.pages) > 0:
                    pass

                logger.info("Meeting closed.")

                # Save the session state
                self.context.storage_state(path=self.SESSION_FILE)
                logger.info(f"Session saved to {self.SESSION_FILE}.")

                # Optionally log session data for debugging
                with open(self.SESSION_FILE, 'r') as file:
                    session_data = json.load(file)
                    logger.info("Session content: %s", json.dumps(session_data, indent=4))

                return {"status": "success", "message": "Meeting joined and recording started."}

        except Exception as e:
            logger.error(f"Error while joining the meeting: {e}")
            return {"status": "error", "message": str(e)}

    def close_browser(self):
        """Close the browser instance."""
        if self.browser:
            self.browser.close()
