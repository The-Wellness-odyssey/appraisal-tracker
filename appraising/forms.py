from django import forms
from django.utils import timezone

from .models import AppraisalFile

class AppraisalForm(forms.ModelForm):
    class Meta:
        model = AppraisalFile
        fields = ['claim_number', 'vehicle_desc', 'date_assigned', 'is_priority', 'status', 'tags']
        widgets = {
            'date_assigned': forms.DateInput(attrs={'type': 'date'}),
            'tags': forms.CheckboxSelectMultiple,
        }
        labels = {
            'vehicle_desc': 'Vehicle Year/Make/Model',
            'is_priority': 'Flag as Priority',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Let the browser's date picker grey out future days too (Django still checks below)
        self.fields['date_assigned'].widget.attrs['max'] = timezone.localdate().isoformat()

    def clean_date_assigned(self):
        """A file can't be assigned in the future; this catches typos like 2062 for 2026."""
        assigned = self.cleaned_data['date_assigned']
        if assigned > timezone.localdate():
            raise forms.ValidationError("The assignment date can't be in the future.")
        return assigned
