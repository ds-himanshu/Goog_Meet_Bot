from django.core.management.base import BaseCommand
from google_auth.views import extract_meeting_details
from django.http import HttpRequest
import logging
import json

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Runs the extract_meeting_details function as a scheduled task.'

    def handle(self, *args, **options):
        logger.info('Starting calendar extraction task')
        request = HttpRequest()

        try:
            response = extract_meeting_details(request)

            if hasattr(response, 'content'):
                # Decode and log the response content
                response_data = json.loads(response.content.decode('utf-8'))
                logger.info(f'Calendar extraction successful. Events found: {len(response_data.get("events", []))}')

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully executed calendar extraction. Found {len(response_data.get("events", []))} events')
                )
            else:
                logger.error('Response has no content')
                self.stdout.write(
                    self.style.ERROR('Response has no content')
                )

        except json.JSONDecodeError as je:
            logger.error(f'Failed to parse response content: {str(je)}')
            self.stdout.write(
                self.style.ERROR(f'Failed to parse response content: {str(je)}')
            )
        except Exception as e:
            logger.error(f'Failed to extract calendar events: {str(e)}')
            self.stdout.write(
                self.style.ERROR(f'Failed to extract calendar events: {str(e)}')
            )