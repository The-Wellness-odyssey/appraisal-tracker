from django.db import models

class AppraisalFile(models.Model):
    claim_number = models.CharField(max_length=50, unique=True)
    vehicle_desc = models.CharField(max_length=100)
    date_assigned = models.DateField()
    is_priority = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20, 
        choices=[('Open', 'Open'), ('Pending', 'Pending'), ('Settled', 'Settled'), ('Closed', 'Closed')], 
        default='Open'
    )

    def __str__(self):
        return f"{self.claim_number} - {self.vehicle_desc}"

class VehicleValuation(models.Model):
    # The related_name 'valuations' allows us to call appraisal.valuations.all() in the template
    appraisal_file = models.ForeignKey(AppraisalFile, on_delete=models.CASCADE, related_name='valuations')
    market_value = models.IntegerField()
    diminished_value = models.IntegerField()
    negotiation_notes = models.TextField(blank=True)

    def __str__(self):
        return f"Valuation for {self.appraisal_file.claim_number}"