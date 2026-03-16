from decimal import Decimal
from django.core.management.base import BaseCommand
from core.models import Cedant, Portfolio, Exposure

class Command(BaseCommand):
    help = "Seed demo data for Reinsight"

    def handle(self, *args, **options):
        cedant, _ = Cedant.objects.get_or_create(name="Cedant A", country="FR")
        portfolio, _ = Portfolio.objects.get_or_create(cedant=cedant, name="EU Portfolio", currency="EUR")

        # Clear old exposures to keep it deterministic
        Exposure.objects.filter(portfolio=portfolio).delete()

        rows = [
            # PROPERTY / FLOOD
            ("PROPERTY", "FLOOD", "FR", "IDF", 1200000),
            ("PROPERTY", "FLOOD", "FR", "NAQ", 800000),
            ("PROPERTY", "FLOOD", "DE", "BY", 600000),
            ("PROPERTY", "FLOOD", "FR", "IDF", 900000),
            # PROPERTY / WIND
            ("PROPERTY", "WIND", "FR", "BRE", 700000),
            ("PROPERTY", "WIND", "ES", "CAT", 500000),
            # ENERGY
            ("ENERGY", "WIND", "GB", "ENG", 1100000),
            ("ENERGY", "FLOOD", "NL", "NH", 650000),
            # MARINE
            ("MARINE", "STORM", "FR", "PACA", 400000),
        ]

        Exposure.objects.bulk_create([
            Exposure(
                portfolio=portfolio,
                lob=lob,
                peril=peril,
                country=country,
                region=region,
                tiv=Decimal(str(tiv)),
                premium=Decimal("0"),
                policy_id="",
                location_id="",
            )
            for (lob, peril, country, region, tiv) in rows
        ])

        self.stdout.write(self.style.SUCCESS(f"Seeded portfolio_id={portfolio.id} with {len(rows)} exposures"))