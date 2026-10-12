from django.shortcuts import render, redirect
from django.urls import reverse
from .forms import AppraisalForm

# Mock data dictionary acting as the temporary database
appraisals = {
    1: {'vehicle': '1998 Lexus ES300', 'issue': 'Rear bumper impact', 'value': 850, 'status': 'Open'},
    2: {'vehicle': '2019 Porsche Cayenne', 'issue': 'Total loss valuation', 'value': 45000, 'status': 'Pending'},
    3: {'vehicle': '2009 Toyota Camry Hybrid', 'issue': 'Structural assembly repair', 'value': 3200, 'status': 'Closed'}
}

def home(request):
    return render(request, 'appraising/home.html')

def list_appraisals(request):
    recently_viewed = request.session.get('recently_viewed', [])
    return render(request, 'appraising/list.html', {
        'appraisals': appraisals,
        'recently_viewed': recently_viewed
    })

def detail(request, id):
    appraisal = appraisals.get(id)
    if appraisal:
        # Session state: Update the recently viewed list
        recently_viewed = request.session.get('recently_viewed', [])
        if appraisal['vehicle'] not in recently_viewed:
            recently_viewed.insert(0, appraisal['vehicle'])
            request.session['recently_viewed'] = recently_viewed[:5] # Keep the last 5
    
    return render(request, 'appraising/detail.html', {'id': id, 'appraisal': appraisal})

def add_appraisal(request):
    # POST Branch
    if request.method == 'POST':
        form = AppraisalForm(request.POST)
        if form.is_valid():
            new_id = max(appraisals.keys()) + 1 if appraisals else 1
            appraisals[new_id] = {
                'vehicle': form.cleaned_data['vehicle'],
                'issue': form.cleaned_data['issue'],
                'value': form.cleaned_data['value'],
                'status': form.cleaned_data['status']
            }
            return redirect(reverse('list'))
    # GET Branch
    else:
        form = AppraisalForm()
        
    return render(request, 'appraising/add.html', {'form': form})

def stats(request):
    return render(request, 'appraising/stats.html')