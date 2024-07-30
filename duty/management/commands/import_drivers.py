import csv
from django.core.management.base import BaseCommand
from duty.models import Driver

class Command(BaseCommand):
    help = 'Import drivers and staff IDs from CSV file'

    def handle(self, *args, **kwargs):
        csvfile_path = r'C:\Users\ETIE-4\Desktop\python\Django_work\staff_transport\Drivers_Master\Driver_Staff_ data.csv'
        with open(csvfile_path, newline='', encoding='ISO-8859-1') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                driver_name = row.get('name', '').strip()
                staff_id = row.get('staff_id', '').strip()
                
                # Validate the data
                if driver_name and staff_id and staff_id != '-':
                    driver, created = Driver.objects.get_or_create(
                        driver_name=driver_name,
                        defaults={'staff_id': staff_id}
                    )
                    if not created:
                        driver.staff_id = staff_id
                        driver.save()
                    self.stdout.write(self.style.SUCCESS(f'Successfully imported {driver.driver_name}'))
                else:
                    self.stdout.write(self.style.ERROR(f'Skipping invalid row: {row}'))