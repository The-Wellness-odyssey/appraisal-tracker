from django.db import models


class Tag(models.Model):
    """A label several appraisal files can share, e.g. "Total Loss" or "Diminished Value"."""
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


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
    # Many-to-many: one file can carry several tags, and one tag can be on many files.
    # related_name='appraisal_files' lets a tag list its files with tag.appraisal_files.all()
    tags = models.ManyToManyField(Tag, related_name='appraisal_files', blank=True)

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
