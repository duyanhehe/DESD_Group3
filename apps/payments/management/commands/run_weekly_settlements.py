from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now, make_aware
from apps.payments.services import SettlementService


class Command(BaseCommand):
    help = "Run weekly settlements for all producers"

    def add_arguments(self, parser):
        parser.add_argument(
            "--week",
            type=str,
            help="Target week date (YYYY-MM-DD). Defaults to last week.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Calculate settlements without creating database records",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output for each producer",
        )

    def handle(self, *args, **options):
        week_str = options.get("week")
        dry_run = options.get("dry_run")
        verbose = options.get("verbose")

        # Parse week date
        if week_str:
            try:
                target_date = datetime.strptime(week_str, "%Y-%m-%d")
                target_date = make_aware(target_date)
            except ValueError:
                raise CommandError(f"Invalid date format: {week_str}. Use YYYY-MM-DD.")
        else:
            target_date = None

        # Get week boundaries
        week_start, week_end = SettlementService.get_week_boundaries(target_date)

        self.stdout.write(
            self.style.NOTICE(
                f"Processing weekly settlements for {week_start} to {week_end}"
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE — No database records will be created")
            )

        # Run settlements
        try:
            results = SettlementService.run_weekly_settlements(
                target_date=target_date,
                dry_run=dry_run,
                performed_by=None,  # System-generated
            )
        except Exception as e:
            raise CommandError(f"Settlement calculation failed: {e}")

        # Output results
        created_count = 0
        no_sales_count = 0
        error_count = 0

        for result in results:
            status = result.get("status")
            producer = result.get("producer")

            if status == "created":
                created_count += 1
                if verbose:
                    total_sales = result.get("total_sales")
                    payout = result.get("payout_amount")
                    self.stdout.write(
                        f"  ✓ {producer}: Sales={total_sales}, Payout={payout}"
                    )
            elif status == "no_sales":
                no_sales_count += 1
                if verbose:
                    self.stdout.write(f"  - {producer}: No sales")
            else:
                error_count += 1
                error_msg = result.get("error", "Unknown error")
                self.stdout.write(
                    self.style.ERROR(f"  ✗ {producer}: {error_msg}")
                )

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Settlement Run Complete"))
        self.stdout.write(f"  Created: {created_count}")
        self.stdout.write(f"  No sales: {no_sales_count}")
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"  Errors: {error_count}"))

        if dry_run:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING("This was a dry run. No records were created.")
            )
