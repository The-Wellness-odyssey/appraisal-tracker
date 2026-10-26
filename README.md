# Vehicle Appraisal Tracker
A Django application for tracking vehicle damage evaluations and diminished value assessments.

## Getting Started
```bash
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python seed.py                      # optional: loads sample files, valuations and tags
python manage.py createsuperuser    # see "Admin Site" below
python manage.py runserver
```
Then open http://127.0.0.1:8000/ for the site and http://127.0.0.1:8000/admin/ for the admin.

## Security & State
* **CSRF Token:** The `{% csrf_token %}` tag is included in the Django forms to generate a hidden, cryptographic token validated by the server upon submission. This prevents Cross-Site Request Forgery attacks, ensuring malicious sites cannot submit fake appraisal assignments on behalf of an authenticated user.
* **Sessions:** Django Sessions are used to store a user's "Recently Viewed Appraisals" list. When navigating between the main list and detail pages, the session persists the viewing history across page reloads without requiring a database, allowing the user to easily jump back to active files.

## Relationships
* **One-to-many (last week):** each `AppraisalFile` has many `VehicleValuation` rows (`related_name='valuations'`).
* **Many-to-many (this week):** I added a `Tag` model and a `tags = ManyToManyField(Tag, related_name='appraisal_files')` field on `AppraisalFile`.

**Why a Tag (many-to-many) instead of a third one-to-many model:** in appraisal work the same label applies to many claims at once ("Total Loss", "Diminished Value", "Structural Repair", "Negotiated"), and one claim often needs more than one label. A ForeignKey would only allow one category per file. A many-to-many lets a file carry several tags and lets a tag be shared by any number of files, which matches how the files are actually sorted.

The tag page (`/tags/<id>/`) lists its files through the related name: `{% for app in tag.appraisal_files.all %}`.

## Migration
The new migration is `appraising/migrations/0002_tag_appraisalfile_tags.py`. It creates the `Tag` table and the join table that links tags to appraisal files.

`makemigrations` did **not** ask for a default. A `ManyToManyField` adds no column to the existing `appraising_appraisalfile` table; Django stores the links in a separate join table, so the existing rows had nothing to fill in. They simply start with no tags.

## Queries
* **Search page (`/search/`):** a search box that filters with `vehicle_desc__icontains` or `claim_number__icontains`, so "lexus" finds "1998 Lexus ES300".
* **Top five:** the same page shows the five highest valuations using `order_by('-market_value')[:5]`.
* **Counts:** counts are computed in the views with `.count()` (active files on the list page, valuations on a detail page, files on a tag page, results on the search page).
* **404s:** every detail view (`detail`, `tag_detail`, and the close action) uses `get_object_or_404`.

## Admin Site
All three models (`AppraisalFile`, `VehicleValuation`, `Tag`) are registered in `appraising/admin.py`. `AppraisalFile` is customised with `list_display`, `list_filter` (status, priority, tag), `search_fields`, a date drill-down, a tag picker, and inline valuations.

**Making your own superuser:** no admin account or password is stored in this repository, and the database (`db.sqlite3`) is ignored by git. After cloning, run:
```bash
python manage.py migrate
python manage.py createsuperuser
```
Django will prompt for a username, email and password of your choosing. Log in at `/admin/` with those.

## Tests
```bash
python manage.py test
```
