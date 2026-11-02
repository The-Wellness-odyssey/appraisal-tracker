from django.db.models import Count, Max, Q, Sum
from django.http import JsonResponse
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


def lookup(request):
    """Live Lookup page. The results are filled in by lookup.js calling api_appraisals."""
    return render(request, 'appraising/lookup.html', {
        'status_choices': AppraisalFile._meta.get_field('status').choices,
    })

def api_appraisals(request):
    """
    JSON endpoint: GET /api/appraisals/

    Query parameters (all optional):
      q       - text matched against claim number or vehicle description (__icontains)
      status  - one of Open, Pending, Settled, Closed (exact match)
      limit   - how many rows to return, 1 to 50 (default 20)

    Always answers with JSON, including when nothing matches (count 0, results []).
    """
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    valid_statuses = [value for value, _ in AppraisalFile._meta.get_field('status').choices]

    # Bad parameters get a JSON error with status 400, not an HTML error page
    if status and status not in valid_statuses:
        return JsonResponse({'error': f"status must be one of: {', '.join(valid_statuses)}"}, status=400)
    try:
        limit = int(request.GET.get('limit', 20))
    except ValueError:
        return JsonResponse({'error': 'limit must be a whole number'}, status=400)
    limit = max(1, min(limit, 50))

    files = AppraisalFile.objects.all()
    if q:
        files = files.filter(Q(claim_number__icontains=q) | Q(vehicle_desc__icontains=q))
    if status:
        files = files.filter(status=status)

    files = (files.annotate(valuation_count=Count('valuations'),
                            top_market_value=Max('valuations__market_value'))
                  .prefetch_related('tags')
                  .order_by('-date_assigned')[:limit])

    # Serialise each row into a plain dictionary JsonResponse can turn into JSON
    results = [
        {
            'id': f.id,
            'claim_number': f.claim_number,
            'vehicle': f.vehicle_desc,
            'status': f.status,
            'is_priority': f.is_priority,
            'date_assigned': f.date_assigned.isoformat(),
            'tags': [tag.name for tag in f.tags.all()],
            'valuation_count': f.valuation_count,
            'top_market_value': f.top_market_value,
            'detail_url': reverse('detail', args=[f.id]),
        }
        for f in files
    ]

    return JsonResponse({
        'query': {'q': q, 'status': status, 'limit': limit},
        'count': len(results),
        'results': results,
    })
