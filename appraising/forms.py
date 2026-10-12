from django import forms
from .models import AppraisalFile

class AppraisalForm(forms.ModelForm):
    class Meta:
        model = AppraisalFile
        fields = ['claim_number', 'vehicle_desc', 'date_assigned', 'is_priority', 'status']
        widgets = {
            'date_assigned': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'vehicle_desc': 'Vehicle Year/Make/Model',
            'is_priority': 'Flag as Priority',
        }