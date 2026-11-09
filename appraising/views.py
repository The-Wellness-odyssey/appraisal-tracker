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

def serialize_file(f):
    """Turn one AppraisalFile into a plain dictionary JsonResponse can send.
    Expects valuation_count and top_market_value to be annotated on the row."""
    return {
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
        'spa_url': reverse('spa_detail', args=[f.id]),
    }

def annotated_files():
    """All appraisal files with their valuation count and top market value attached."""
    return (AppraisalFile.objects
            .annotate(valuation_count=Count('valuations'), top_market_value=Max('valuations__market_value'))
            .prefetch_related('tags'))

def api_appraisals(request):
    """
    JSON endpoint: /api/appraisals/

    GET returns one page of appraisal files. Query parameters (all optional):
      q       - text matched against claim number or vehicle description (__icontains)
      status  - one of Open, Pending, Settled, Closed (exact match)
      limit   - rows per page, 1 to 50 (default 20)
      page    - which page, starting at 1 (default 1)

    POST creates a new file from form data (used by the Files section's create view).

    Always answers with JSON, including when nothing matches (count 0, results []).
    """
    if request.method == 'POST':
        return api_create_appraisal(request)

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    valid_statuses = [value for value, _ in AppraisalFile._meta.get_field('status').choices]

    # Bad parameters get a JSON error with status 400, not an HTML error page
    if status and status not in valid_statuses:
        return JsonResponse({'error': f"status must be one of: {', '.join(valid_statuses)}"}, status=400)
    try:
        limit = int(request.GET.get('limit', 20))
        page = int(request.GET.get('page', 1))
    except ValueError:
        return JsonResponse({'error': 'limit and page must be whole numbers'}, status=400)
    limit = max(1, min(limit, 50))
    page = max(1, page)

    files = annotated_files()
    if q:
        files = files.filter(Q(claim_number__icontains=q) | Q(vehicle_desc__icontains=q))
    if status:
        files = files.filter(status=status)

    # Pagination happens here in the database query, not in the browser:
    # count the matches, then slice out only this page's rows (LIMIT/OFFSET in SQL).
    total = files.count()
    num_pages = max(1, (total + limit - 1) // limit)
    if page > num_pages:
        return JsonResponse({'error': f'page {page} does not exist; there are {num_pages}'}, status=404)
    start = (page - 1) * limit
    rows = files.order_by('-date_assigned', '-id')[start:start + limit]

    results = [serialize_file(f) for f in rows]

    return JsonResponse({
        'query': {'q': q, 'status': status, 'limit': limit, 'page': page},
        'count': len(results),
        'total': total,
        'page': page,
        'num_pages': num_pages,
        'has_previous': page > 1,
        'has_next': page < num_pages,
        'results': results,
    })

def api_create_appraisal(request):
    """POST /api/appraisals/ - validate with the same AppraisalForm as the classic Add page.
    201 with the new file on success, 400 with field errors otherwise."""
    form = AppraisalForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'errors': {field: [e['message'] for e in errs]
                                        for field, errs in form.errors.get_json_data().items()}}, status=400)
    new_file = form.save()
    return JsonResponse(serialize_file(annotated_files().get(id=new_file.id)), status=201)

def api_appraisal_detail(request, id):
    """GET /api/appraisals/<id>/ - one file with its valuations. Missing ids get a 404."""
    appraisal = get_object_or_404(annotated_files(), id=id)
    data = serialize_file(appraisal)
    data['valuations'] = [
        {
            'market_value': v.market_value,
            'diminished_value': v.diminished_value,
            'notes': v.negotiation_notes,
        }
        for v in appraisal.valuations.order_by('id')
    ]
    return JsonResponse(data)

def files_app(request, id=None):
    """
    The single-page Files section. /files/, /files/new/ and /files/<id>/ all return
    this same shell; spa.js reads the URL and shows the matching view.
    A missing id still gets a real 404 here, so a bad link is not a 200 page.
    """
    if id is not None:
        get_object_or_404(AppraisalFile, id=id)
    return render(request, 'appraising/files_app.html', {'form': AppraisalForm()})
