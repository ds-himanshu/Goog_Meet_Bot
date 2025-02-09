from django.core.management.base import BaseCommand
from datetime import datetime
import os
import json
import logging
from django.conf import settings
from google_auth.playwright_google_meet import GoogleMeetAutomation

# Setup logger
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Join a scheduled Google Meet meeting'

    def add_arguments(self, parser):
        parser.add_argument('--meeting', type=str, help='Meeting details in JSON format')
        parser.add_argument('--test', action='store_true', help='Run in test mode')

    def handle(self, *args, **options):
        log_file = os.path.join(settings.BASE_DIR, 'cron_execution.log')

        try:
            with open(log_file, 'a') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"\n[{timestamp}] Cron job started\n")

            if not options.get('meeting'):
                error_msg = "No meeting data provided"
                logger.error(error_msg)
                with open(log_file, 'a') as f:
                    f.write(f"Error: {error_msg}\n")
                return

            meeting_data = json.loads(options['meeting'])
            meet_link = meeting_data['meet_link']
            summary = meeting_data['summary']

            with open(log_file, 'a') as f:
                f.write(f"Attempting to join meeting: {summary} at {meet_link}\n")

            google_meet = GoogleMeetAutomation(meeting_link=meet_link)
            response = google_meet.join_google_meet()

            with open(log_file, 'a') as f:
                f.write(f"Join attempt response: {response}\n")

            if response["status"] == "success":
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully joined meeting: {summary}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Failed to join meeting: {response["message"]}')
                )

        except Exception as e:
            error_msg = f'Error in join_meeting command: {str(e)}'
            logger.error(error_msg)
            with open(log_file, 'a') as f:
                f.write(f"Error: {error_msg}\n")
        finally:
            if 'google_meet' in locals():
                google_meet.close_browser()