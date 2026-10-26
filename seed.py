import os
import django
from datetime import date

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

    print("Successfully seeded the database with 4 Tags, 3 AppraisalFiles and 5 VehicleValuations.")

if __name__ == '__main__':
    run_seed()
