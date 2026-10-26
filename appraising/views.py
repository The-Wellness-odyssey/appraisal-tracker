from django.db.models import Count, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import AppraisalFile, VehicleValuation, Tag
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
        'recently_viewed': recently_viewed,
        'active_count': active_appraisals.count(),
    })

def detail(request, id):
    # REQUIRED 404 HANDLING: Will throw a 404 page if the ID doesn't exist in the DB
    appraisal = get_object_or_404(AppraisalFile, id=id)

    # Session state: Update recently viewed list with the database ID
    recently_viewed = request.session.get('recently_viewed', [])
    if id not in recently_viewed:
        recently_viewed.insert(0, id)
        request.session['recently_viewed'] = recently_viewed[:5]

    return render(request, 'appraising/detail.html', {
        'appraisal': appraisal,
        'valuation_count': appraisal.valuations.count(),
    })

def add_appraisal(request):
    if request.method == 'POST':
        form = AppraisalForm(request.POST)
        if form.is_valid():
            # Writes the new row, and its tag links, to the database
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
    total_dv = VehicleValuation.objects.aggregate(total=Sum('diminished_value'))['total'] or 0
    return render(request, 'appraising/stats.html', {'total_open': total_open, 'total': total_dv})

def search(request):
    """Search box (__icontains) plus a "top five by market value" list."""
    q = request.GET.get('q', '').strip()
    results = AppraisalFile.objects.none()
    if q:
        # Case-insensitive match on the vehicle description OR the claim number
        results = (AppraisalFile.objects.filter(vehicle_desc__icontains=q)
                   | AppraisalFile.objects.filter(claim_number__icontains=q)).distinct().order_by('claim_number')

    # Top five valuations, highest market value first
    top_five = VehicleValuation.objects.select_related('appraisal_file').order_by('-market_value')[:5]

    return render(request, 'appraising/search.html', {
        'q': q,
        'results': results,
        'result_count': results.count(),
        'top_five': top_five,
    })

def tag_list(request):
    # Each tag with how many files use it, most used first
    tags = Tag.objects.annotate(file_count=Count('appraisal_files')).order_by('-file_count', 'name')
    return render(request, 'appraising/tag_list.html', {'tags': tags})

def tag_detail(request, id):
    tag = get_object_or_404(Tag, id=id)
    # The template lists the files through the related_name: tag.appraisal_files.all
    return render(request, 'appraising/tag_detail.html', {
        'tag': tag,
        'file_count': tag.appraisal_files.count(),
    })
