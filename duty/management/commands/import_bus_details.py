import csv
import os
from django.core.management.base import BaseCommand
from duty.models import BusDetails

class Command(BaseCommand):
    help = "Import bus details from a CSV file"

    def handle(self, *args, **kwargs):
        # Define the file path
        file_path = "D:/Sarun_App/OCC_Drivers_Headcount/Drivers_Master/bus_details.csv"

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        # Read the CSV file
        with open(file_path, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    # Validate seat capacity
                    seat_capacity = int(row['seat_capacity'].strip())
                    bus_no = row['bus_no'].strip()

                    # Update or create bus details
                    BusDetails.objects.update_or_create(
                        bus_no=bus_no,
                        defaults={'seat_capacity': seat_capacity}
                    )
                except ValueError as e:
                    self.stdout.write(self.style.WARNING(
                        f"Skipping row with invalid data: {row} (Error: {e})"
                    ))

        self.stdout.write(self.style.SUCCESS("Bus details imported successfully."))
