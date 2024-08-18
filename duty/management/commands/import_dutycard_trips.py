# duty/management/commands/import_dutycard_trips.py

import csv
import os
from django.core.management.base import BaseCommand, CommandError
from duty.models import DutyCardTrip

class Command(BaseCommand):
    help = 'Import duty card trips from a CSV file'

    def handle(self, *args, **kwargs):
        # Specify the CSV file path directly in the code
        csv_file_path = '/home/ubuntu/OCC_Drivers_Headcount/Drivers_Master/Dutycard_trips.csv'

        if not os.path.exists(csv_file_path):
            raise CommandError(f"File {csv_file_path} does not exist")

        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    DutyCardTrip.objects.create(
                        duty_card_no=row['Duty Card No'],
                        route_name=row['Route Name'],
                        trip_type=row['Trip Type'],
                        pick_up_time=row['Pick Up Time'],
                        drop_off_time=row['Drop Off Time'],
                        shift_time=row['Shift Time']
                    )
                    self.stdout.write(self.style.SUCCESS(f"Duty Card Trip {row['Duty Card No']} imported successfully"))
                except KeyError as e:
                    self.stderr.write(self.style.ERROR(f"Missing column in CSV: {e}"))
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Error importing duty card trip {row['Duty Card No']}: {e}"))
