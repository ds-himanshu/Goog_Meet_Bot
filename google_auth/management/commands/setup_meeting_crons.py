from django.core.management.base import BaseCommand
from datetime import datetime
import csv
import pytz
import json
from django.conf import settings
import os
from crontab import CronTab


class Command(BaseCommand):
    help = 'Sets up cron jobs for upcoming meetings from CSV'

    def add_arguments(self, parser):
        # Add a show option
        parser.add_argument(
            '--show',
            action='store_true',
            help='Show all meeting crons'
        )

    def show_crons(self):
        """Display all meeting crons"""
        cron = CronTab(user=True)
        meeting_jobs = [job for job in cron if job.comment == 'meeting_join']

        if meeting_jobs:
            self.stdout.write("\nCurrently active meeting crons:")
            for job in meeting_jobs:
                self.stdout.write(f"\nSchedule: {job.slices}")
                self.stdout.write(f"Command: {job.command}")
                self.stdout.write(f"Comment: {job.comment}")
                self.stdout.write("-" * 50)
        else:
            self.stdout.write("\nNo meeting crons currently active")

    def handle(self, *args, **options):
        if options['show']:
            self.show_crons()
            return

        try:
            self.stdout.write('Removing existing meeting cron jobs...')
            cron = CronTab(user=True)
            cron.remove_all(comment='meeting_join')

            project_path = os.getcwd()
            jobs_added = 0

            with open('meeting_invites.csv', 'r') as file:
                csv_reader = csv.DictReader(file)
                current_time = datetime.now(pytz.UTC)

                for row in csv_reader:
                    meeting_time = datetime.fromisoformat(row['Start Time'])

                    if meeting_time > current_time:
                        minute = meeting_time.minute
                        hour = meeting_time.hour
                        day = meeting_time.day
                        month = meeting_time.month

                        meeting_data = json.dumps({
                            'summary': row['Summary'],
                            'meet_link': row['Meet Link']
                        })

                        cron_time = f'{minute} {hour} {day} {month} *'
                        command = f'cd {project_path} && python3 manage.py join_meeting --meeting=\'{meeting_data}\''

                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Setting up cron for "{row["Summary"]}" at {meeting_time}'
                            )
                        )

                        job = cron.new(command=command, comment='meeting_join')
                        job.setall(cron_time)
                        jobs_added += 1

            # Write the crontab if we added any jobs
            if jobs_added > 0:
                cron.write()
                self.stdout.write(self.style.SUCCESS(f'Successfully set up {jobs_added} meeting cron jobs'))
                self.show_crons()  # Show the crons after adding them
            else:
                self.stdout.write('No future meetings found to schedule')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to setup meeting crons: {str(e)}')
            )