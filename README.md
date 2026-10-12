# Vehicle Appraisal Tracker
A Django application for tracking vehicle damage evaluations and diminished value assessments. Run `python manage.py runserver` to start the local server.

## Security & State
* **CSRF Token:** The `{% csrf_token %}` tag is included in the Django forms to generate a hidden, cryptographic token validated by the server upon submission. This prevents Cross-Site Request Forgery attacks, ensuring malicious sites cannot submit fake appraisal assignments on behalf of an authenticated user.
* **Sessions:** Django Sessions are used to store a user's "Recently Viewed Appraisals" list. When navigating between the main list and detail pages, the session persists the viewing history across page reloads without requiring a database, allowing the user to easily jump back to active files.