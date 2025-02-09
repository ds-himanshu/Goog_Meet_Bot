import os
import json
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright
from django.conf import settings
from urllib.parse import urlparse
from pathlib import Path

# Setup logger
logger = logging.getLogger(__name__)


class GoogleMeetAutomation:
    """Class to automate joining a Google Meet and starting recording."""

    # SESSION_FILE = os.path.join(settings.BASE_DIR, 'google_session.json')
    SESSION_FILE = Path(__file__).resolve().parent.parent / 'google_session.json'

    def __init__(self, meeting_link=None):
        """
        Initialize the automation class with a meeting link.

        Args:
            meeting_link (str): The Google Meet URL to join
        """
        self.browser = None
        self.context = None

        if not meeting_link:
            raise ValueError("Meeting link is required")

        # Validate meeting link
        if not self._is_valid_meet_link(meeting_link):
            raise ValueError(f"Invalid Google Meet link: {meeting_link}")

        self.meeting_link = meeting_link
        logger.info(f"Initializing automation for meeting: {self.meeting_link}")

    def _is_valid_meet_link(self, url):
        """Validate if the URL is a valid Google Meet link."""
        try:
            parsed = urlparse(url)
            return parsed.scheme in ('http', 'https') and 'meet.google.com' in parsed.netloc
        except Exception as e:
            logger.error(f"Error validating meet link: {e}")
            return False

    def _setup_browser_context(self, playwright):
        """Set up browser context with necessary permissions."""
        try:
            # Launch browser with video/audio permissions
            self.browser = playwright.chromium.launch(
                headless=False,
                args=['--use-fake-ui-for-media-stream']  # Auto-allow camera/mic permissions
            )
            permissions = ["microphone", "camera"]

            # Load existing session if available
            if os.path.exists(self.SESSION_FILE):
                try:
                    self.context = self.browser.new_context(storage_state=self.SESSION_FILE)
                    logger.info("Loaded existing session from file.")
                except Exception as e:
                    logger.error(f"Failed to load session: {e}. Creating new context.")
                    self.context = self.browser.new_context()
            else:
                logger.info("No session file found. Creating new context.")
                self.context = self.browser.new_context()

            # Grant permissions
            self.context.grant_permissions(permissions, origin="https://meet.google.com")
            return True

        except Exception as e:
            logger.error(f"Error setting up browser context: {e}")
            return False

    def join_google_meet(self):
        """
        Automates the process of joining a Google Meet session and leaving when the meeting ends.
        """
        try:
            logger.info(f"Attempting to join meeting at: {self.meeting_link}")

            with sync_playwright() as p:
                if not self._setup_browser_context(p):
                    return {"status": "error", "message": "Failed to setup browser"}

                page = self.context.new_page()
                page.on("console", lambda msg: logger.info(f"Browser Console: {msg.text}"))
                page.on("pageerror", lambda err: logger.error(f"Page Error: {err}"))

                logger.info(f"Navigating to meeting URL: {self.meeting_link}")
                page.goto(self.meeting_link, timeout=30000, wait_until='networkidle')

                logger.info(f"Page title: {page.title()}")
                page.screenshot(path='meet_page.png')

                # Selectors
                join_now_selector = "//span[text()='Join now']/.."
                ask_to_join_selectors = [
                    "//span[contains(text(),'Ask to join')]/..",
                    "button:has-text('Ask to join')",
                    "button[aria-label='Ask to join']"
                ]

                # Click "Join now" if available, else click "Ask to join"
                join_now_button = None
                try:
                    join_now_button = page.wait_for_selector(join_now_selector, timeout=5000)
                except:
                    pass

                if join_now_button:
                    logger.info("Clicking 'Join now' button")
                    join_now_button.click()
                else:
                    join_button = None
                    for selector in ask_to_join_selectors:
                        try:
                            join_button = page.wait_for_selector(selector, timeout=5000)
                            if join_button:
                                break
                        except Exception as select_err:
                            logger.info(f"Selector {selector} not found: {select_err}")

                    if not join_button:
                        logger.info("No 'Ask to join' or 'Join now' button found. Exiting.")
                        return {"status": "error", "message": "No join button found"}

                    logger.info("Clicking 'Ask to join' button")
                    join_button.click()

                    # Wait to be admitted into the meeting
                    try:
                        page.wait_for_selector("//div[contains(text(),'You’re in the meeting')]", timeout=60000)
                        logger.info("Successfully joined the meeting!")
                    except Exception as join_err:
                        logger.error(f"Error waiting for join confirmation: {join_err}")
                        return {"status": "error", "message": "Failed to confirm join request"}

                # **Wait until meeting ends (when //div[text()='1'] is visible)**
                try:
                    logger.info("Monitoring meeting status...")

                    while True:
                        if page.locator("//div[text()='1']").is_visible():
                            logger.info("Meeting has ended (only 1 participant left). Leaving now.")
                            break  # Exit the loop

                        page.wait_for_timeout(5000)  # Check every 5 seconds

                    logger.info("Closing browser as meeting has ended.")
                    page.close()

                except Exception as end_meeting_err:
                    logger.error(f"Error checking meeting status: {end_meeting_err}")

        except Exception as e:
            logger.error(f"Comprehensive join error: {e}")
            return {"status": "error", "message": str(e)}

    def close_browser(self):
        """Close the browser instance."""
        try:
            if self.browser:
                self.browser.close()
                logger.info("Browser closed successfully")
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")

    def __del__(self):
        """Destructor to ensure browser cleanup."""
        self.close_browser()