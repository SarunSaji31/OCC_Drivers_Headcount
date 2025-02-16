# duty/management/commands/import_bus_master.py

import os
import pandas as pd
from django.core.management.base import BaseCommand
from duty.models import BusMasterList

class Command(BaseCommand):
    help = "Import Bus Master List from an Excel file"

    def handle(self, *args, **options):
        # Define the file path (including the extra space in the file name)
        file_path = r"D:\Sarun_App\ekg_production\Drivers_Master\Bus_master_lsit .xlsx"

        # Check if the file exists
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        # Read the Excel file
        df = pd.read_excel(file_path)
        # Clean column names (remove any extra whitespace)
        df.columns = df.columns.str.strip()

        # Optional: Print the columns for debugging
        self.stdout.write(f"Cleaned Columns: {df.columns.tolist()}")

        # Import each row into the BusMasterList model
        for index, row in df.iterrows():
            BusMasterList.objects.create(
                bus_no=row['Bus_No'],
                capacity=row['Capacity']
            )

        self.stdout.write(self.style.SUCCESS("Bus master data imported successfully."))
