import os
import django
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'appraisal_tracker.settings')
django.setup()

from appraising.models import AppraisalFile, VehicleValuation, Tag

def run_seed():
    AppraisalFile.objects.all().delete()
    VehicleValuation.objects.all().delete()
    Tag.objects.all().delete()

    # Create 4 shared Tags
    total_loss = Tag.objects.create(name="Total Loss")
    dim_value = Tag.objects.create(name="Diminished Value")
    structural = Tag.objects.create(name="Structural Repair")
    negotiated = Tag.objects.create(name="Negotiated")

    # Create 3 Appraisal Files
    a1 = AppraisalFile.objects.create(claim_number="CLM-001", vehicle_desc="1998 Lexus ES300", date_assigned=date(2026, 9, 15), is_priority=False, status="Settled")
    a2 = AppraisalFile.objects.create(claim_number="CLM-002", vehicle_desc="2019 Porsche Cayenne (Bordeaux Red)", date_assigned=date(2026, 10, 2), is_priority=True, status="Open")
    a3 = AppraisalFile.objects.create(claim_number="CLM-003", vehicle_desc="2009 Toyota Camry Hybrid (Project Celsior)", date_assigned=date(2026, 8, 10), is_priority=False, status="Pending")

    # Attach tags (many-to-many: "Negotiated" is shared by two files, CLM-003 has two tags)
    a1.tags.add(negotiated)
    a2.tags.add(total_loss, negotiated)
    a3.tags.add(dim_value, structural)

    # Create 5 Vehicle Valuations
    VehicleValuation.objects.create(appraisal_file=a1, market_value=3500, diminished_value=0, negotiation_notes="Minor rear bumper impact. No diminished value applied for this age.")
    VehicleValuation.objects.create(appraisal_file=a2, market_value=48500, diminished_value=0, negotiation_notes="Total loss valuation based on market comparables and option scarcity.")
    VehicleValuation.objects.create(appraisal_file=a2, market_value=51200, diminished_value=0, negotiation_notes="Negotiated increase with independent adjuster based on build sheet data.")
    VehicleValuation.objects.create(appraisal_file=a3, market_value=6200, diminished_value=1200, negotiation_notes="Initial structural assembly repair valuation.")
    VehicleValuation.objects.create(appraisal_file=a3, market_value=6200, diminished_value=1500, negotiation_notes="Revised diminished value post-repair inspection.")

    # 22 more files so the Files section has several pages to paginate through
    more = [
        ("2015 Honda Accord EX-L", "Open"), ("2018 Toyota RAV4 XLE", "Pending"), ("2012 Lexus RX350", "Settled"),
        ("2020 Tesla Model 3 Long Range", "Open"), ("2016 Ford F-150 Lariat", "Closed"), ("2011 Nissan Altima 2.5 S", "Settled"),
        ("2021 Subaru Outback Limited", "Open"), ("2014 BMW 328i", "Pending"), ("2017 Mazda CX-5 Grand Touring", "Settled"),
        ("2006 Lexus GS300", "Closed"), ("2022 Hyundai Tucson SEL", "Open"), ("2013 Toyota Prius", "Settled"),
        ("2019 Honda Odyssey EX", "Pending"), ("2010 Mercedes-Benz E350", "Closed"), ("2023 Kia Telluride SX", "Open"),
        ("2008 Toyota Camry LE", "Settled"), ("2016 Audi Q5 Premium Plus", "Pending"), ("2020 Chevrolet Silverado 1500", "Open"),
        ("2015 Lexus IS250", "Settled"), ("2018 Volkswagen Jetta SE", "Open"), ("2012 Toyota Sienna XLE", "Closed"),
        ("2021 Toyota Highlander Hybrid", "Pending"),
    ]
    tag_cycle = [[], [dim_value], [total_loss], [structural], [negotiated, dim_value], []]
    for i, (vehicle, status) in enumerate(more, start=4):
        f = AppraisalFile.objects.create(
            claim_number=f"CLM-{i:03d}", vehicle_desc=vehicle,
            date_assigned=date(2026, 6, 1) + timedelta(days=i * 6),
            is_priority=(i % 7 == 0), status=status)
        f.tags.add(*tag_cycle[i % len(tag_cycle)])
        base = 9000 + (i * 1373) % 30000
        VehicleValuation.objects.create(appraisal_file=f, market_value=base, diminished_value=(base // 10) if i % 2 else 0,
                                        negotiation_notes="Initial valuation from market comparables.")

    print(f"Successfully seeded the database with {Tag.objects.count()} Tags, "
          f"{AppraisalFile.objects.count()} AppraisalFiles and {VehicleValuation.objects.count()} VehicleValuations.")

if __name__ == '__main__':
    run_seed()
