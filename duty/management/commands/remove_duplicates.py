from django.core.management.base import BaseCommand
from duty.models import DriverImportLog
from django.db.models import Count

class Command(BaseCommand):
    help = 'Remove duplicate entries from DriverImportLog'

    def handle(self, *args, **kwargs):
        duplicates = DriverImportLog.objects.values('staff_id', 'driver_name').annotate(count=Count('id')).filter(count__gt=1)
        
        for duplicate in duplicates:
            entries = DriverImportLog.objects.filter(staff_id=duplicate['staff_id'], driver_name=duplicate['driver_name']).order_by('id')
            entries_to_keep = entries.first()
            entries_to_delete = entries.exclude(id=entries_to_keep.id)
            
            entries_to_delete.delete()
            self.stdout.write(self.style.SUCCESS(f'Removed {entries_to_delete.count()} duplicate entries for {duplicate["staff_id"]}, {duplicate["driver_name"]}'))

        self.stdout.write(self.style.SUCCESS('Finished removing duplicates.'))
