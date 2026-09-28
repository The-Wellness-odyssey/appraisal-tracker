from django.shortcuts import render
from django.http import Http404

APPRAISALS = {
    1: {"vehicle": "2009 Toyota Camry Hybrid", "issue": "ABS Module Line Flaring", "value": 1800, "status": "Pending"},
    2: {"vehicle": "Lexus SC430", "issue": "Diminished Value Assessment", "value": 850, "status": "Completed"},
    3: {"vehicle": "2010 Lexus HS250h", "issue": "EV/PWR Mode ECU Pinout", "value": 400, "status": "In Progress"}
}

def home(request):
    return render(request, 'appraising/home.html')

def appraisal_list(request):
    return render(request, 'appraising/list.html', {'appraisals': APPRAISALS})

def appraisal_detail(request, appraisal_id):
    if appraisal_id not in APPRAISALS:
        raise Http404("Appraisal record not found")
    return render(request, 'appraising/detail.html', {'appraisal': APPRAISALS[appraisal_id], 'id': appraisal_id})

def stats(request):
    total_value = sum(item['value'] for item in APPRAISALS.values())
    return render(request, 'appraising/stats.html', {'total': total_value})