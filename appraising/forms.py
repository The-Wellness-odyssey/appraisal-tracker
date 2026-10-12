from django import forms

class AppraisalForm(forms.Form):
    vehicle = forms.CharField(label="Vehicle Year/Make/Model", max_length=100)
    issue = forms.CharField(label="Damage/Issue Description", max_length=200)
    value = forms.IntegerField(label="Estimated Value ($)")
    date_assigned = forms.DateField(label="Date Assigned", widget=forms.DateInput(attrs={'type': 'date'}))
    status = forms.ChoiceField(choices=[('Open', 'Open'), ('Pending', 'Pending'), ('Closed', 'Closed')])