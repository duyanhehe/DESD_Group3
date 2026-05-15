from django.core.management.base import BaseCommand
from apps.orders.services import RecurringOrderService

class Command(BaseCommand):
    help = "TC-018: Process all due recurring orders and generate new master/sub orders."

    def handle(self, *args, **options):
        self.stdout.write("Starting recurring order processing...")
        
        results = RecurringOrderService.process_due_subscriptions()
        
        for detail in results["details"]:
            self.stdout.write(detail)
            
        summary = f"Success: {results['processed']}, Failed: {results['failed']}"
        self.stdout.write(self.style.SUCCESS(summary))
