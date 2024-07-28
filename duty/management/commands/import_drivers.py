# duty/management/commands/import_drivers.py

import csv
from django.core.management.base import BaseCommand
from duty.models import Driver

class Command(BaseCommand):
    help = 'Import drivers and staff IDs from CSV file'

    def handle(self, *args, **kwargs):
        csvfile_path = r'C:\Users\ETIE-4\Desktop\python\Django_work\staff_transport\Drivers_Master\Driver_Staff_ data.csv'
        with open(csvfile_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                driver, created = Driver.objects.get_or_create(
                    driver_name=row['driver_name'],
                    staff_id=row['staff_id']
                )
                self.stdout.write(self.style.SUCCESS(f'Successfully imported {driver.driver_name}'))
