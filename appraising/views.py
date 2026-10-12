from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import AppraisalFile, VehicleValuation
from .forms import AppraisalForm

def home(request):
    return render(request, 'appraising/home.html')

def list_appraisals(request):
    # REQUIRED QUERY: Not just .all(). This filters out closed files and orders by date.
    # Returns a QuerySet of active files, newest first.
    active_appraisals = AppraisalFile.objects.exclude(status='Closed').order_by('-date_assigned')
    
    recently_viewed_ids = request.session.get('recently_viewed', [])
    recently_viewed = AppraisalFile.objects.filter(id__in=recently_viewed_ids)

    return render(request, 'appraising/list.html', {
        'appraisals': active_appraisals,
        'recently_viewed': recently_viewed
    })

def detail(request, id):
    # REQUIRED 404 HANDLING: Will throw a 404 page if the ID doesn't exist in the DB
    appraisal = get_object_or_404(AppraisalFile, id=id)
    
    # Session state: Update recently viewed list with the database ID
    recently_viewed = request.session.get('recently_viewed', [])
    if id not in recently_viewed:
        recently_viewed.insert(0, id)
        request.session['recently_viewed'] = recently_viewed[:5]
    
    return render(request, 'appraising/detail.html', {'appraisal': appraisal})

def add_appraisal(request):
    if request.method == 'POST':
        form = AppraisalForm(request.POST)
        if form.is_valid():
            # Automatically writes the new row to the database
            form.save()
            return redirect(reverse('list'))
    else:
        form = AppraisalForm()
        
    return render(request, 'appraising/add.html', {'form': form})

# REQUIRED CUSTOM ACTION: Mark an appraisal as closed
def close_appraisal(request, id):
    if request.method == 'POST':
        appraisal = get_object_or_404(AppraisalFile, id=id)
        appraisal.status = 'Closed'
        appraisal.save()
    return redirect(reverse('detail', args=[id]))

def stats(request):
    total_open = AppraisalFile.objects.filter(status='Open').count()
    return render(request, 'appraising/stats.html', {'total_open': total_open})