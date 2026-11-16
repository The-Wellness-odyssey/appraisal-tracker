"""
Test suite for the Vehicle Appraisal Tracker.

Run it with:  python manage.py test
GitHub Actions runs the same command on every push and pull request
(see .github/workflows/tests.yml).

Groups:
  1. Model tests          - what the models store and how they print
  2. View tests           - the pages people visit, using the test Client
  3. Form tests           - what AppraisalForm accepts and rejects
  4. Relationship tests   - valuations and tags reached through their relationships
  5. API tests            - the JSON endpoint and the single-page Files section
"""
from datetime import date, timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import AppraisalForm
from .models import AppraisalFile, VehicleValuation, Tag


# ---------------------------------------------------------------------------
# 1. Model tests
# ---------------------------------------------------------------------------

class ModelTests(TestCase):
    def setUp(self):
        self.tag = Tag.objects.create(name="Total Loss")
        self.file = AppraisalFile.objects.create(
            claim_number="CLM-001", vehicle_desc="1998 Lexus ES300", date_assigned=date(2026, 9, 15))
        self.valuation = VehicleValuation.objects.create(
            appraisal_file=self.file, market_value=3500, diminished_value=0)

    # Makes sure a file shows as "claim number - vehicle" everywhere Django prints it
    # (admin lists, dropdowns), so files can be told apart at a glance.
    def test_appraisal_file_str_shows_claim_and_vehicle(self):
        self.assertEqual(str(self.file), "CLM-001 - 1998 Lexus ES300")

    # Makes sure a tag prints as just its name, which is what the admin and tag pages show.
    def test_tag_str_is_its_name(self):
        self.assertEqual(str(self.tag), "Total Loss")

    # Makes sure a valuation names the claim it belongs to, so the admin's valuation
    # list isn't a column of identical "VehicleValuation object" rows.
    def test_valuation_str_names_its_claim(self):
        self.assertEqual(str(self.valuation), "Valuation for CLM-001")

    # Makes sure a brand-new file starts as Open and not flagged as priority,
    # so a file created without those fields lands on the active list correctly.
    def test_new_file_defaults_to_open_and_not_priority(self):
        self.assertEqual(self.file.status, "Open")
        self.assertFalse(self.file.is_priority)

    # Makes sure the database itself refuses a second file with the same claim number,
    # even if something skips the form's validation.
    def test_claim_number_must_be_unique_in_the_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            AppraisalFile.objects.create(claim_number="CLM-001", vehicle_desc="Duplicate", date_assigned=date(2026, 9, 16))

    # Makes sure tags always come back in alphabetical order, which the tag
    # checkboxes and tag lists rely on.
    def test_tags_are_listed_alphabetically(self):
        Tag.objects.create(name="Diminished Value")
        Tag.objects.create(name="Negotiated")
        self.assertEqual([t.name for t in Tag.objects.all()], ["Diminished Value", "Negotiated", "Total Loss"])


# ---------------------------------------------------------------------------
# 2. View tests
# ---------------------------------------------------------------------------

class ViewTests(TestCase):
    def setUp(self):
        self.shared = Tag.objects.create(name="Negotiated")
        self.a1 = AppraisalFile.objects.create(claim_number="CLM-001", vehicle_desc="1998 Lexus ES300",
                                               date_assigned=date(2026, 9, 15), status="Settled")
        self.a2 = AppraisalFile.objects.create(claim_number="CLM-002", vehicle_desc="2019 Porsche Cayenne",
                                               date_assigned=date(2026, 10, 2))
        self.closed = AppraisalFile.objects.create(claim_number="CLM-009", vehicle_desc="2006 Lexus GS300",
                                                   date_assigned=date(2026, 7, 1), status="Closed")
        self.a1.tags.add(self.shared)
        self.a2.tags.add(self.shared)
        VehicleValuation.objects.create(appraisal_file=self.a2, market_value=51200, diminished_value=0)
        VehicleValuation.objects.create(appraisal_file=self.a1, market_value=3500, diminished_value=1500)

    # Makes sure the Active Appraisals list loads, shows open files with the right
    # count, and leaves closed files off the list.
    def test_list_page_shows_active_files_only(self):
        response = self.client.get(reverse('list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CLM-002 - 2019 Porsche Cayenne")
        self.assertContains(response, "2 active files")
        self.assertNotContains(response, "CLM-009")

    # Makes sure a file's detail page loads and shows its valuations and its tags.
    def test_detail_page_shows_valuations_and_tags(self):
        response = self.client.get(reverse('detail', args=[self.a1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1998 Lexus ES300")
        self.assertContains(response, "1 valuation")
        self.assertContains(response, "Negotiated")

    # Checks the detail pages 404 for a missing id instead of crashing with a server error.
    def test_detail_pages_return_404_for_missing_ids(self):
        self.assertEqual(self.client.get(reverse('detail', args=[999])).status_code, 404)
        self.assertEqual(self.client.get(reverse('tag_detail', args=[999])).status_code, 404)
        self.assertEqual(self.client.get(reverse('spa_detail', args=[999])).status_code, 404)

    # Makes sure the Statistics page actually prints the total diminished value
    # (this was blank for weeks because the view never passed it to the template).
    def test_stats_page_shows_total_diminished_value(self):
        response = self.client.get(reverse('stats'))
        self.assertContains(response, "Open Files:</strong> 1")
        self.assertContains(response, "$1500")

    # Makes sure "Mark File Closed" only closes a file on a POST, so following a
    # link or a browser prefetch (a GET) can never close a file by accident.
    def test_close_only_happens_on_post(self):
        self.client.get(reverse('close_appraisal', args=[self.a2.id]))
        self.a2.refresh_from_db()
        self.assertEqual(self.a2.status, "Open")
        response = self.client.post(reverse('close_appraisal', args=[self.a2.id]))
        self.assertRedirects(response, reverse('detail', args=[self.a2.id]))
        self.a2.refresh_from_db()
        self.assertEqual(self.a2.status, "Closed")

    # Makes sure the Add Appraisal page saves a new file and sends the user back to the list.
    def test_add_page_creates_file_and_redirects(self):
        response = self.client.post(reverse('add'), {
            'claim_number': 'CLM-050', 'vehicle_desc': '2007 Toyota Camry LE',
            'date_assigned': '2026-11-01', 'status': 'Open', 'tags': [self.shared.id]})
        self.assertRedirects(response, reverse('list'))
        self.assertTrue(AppraisalFile.objects.filter(claim_number='CLM-050', tags=self.shared).exists())

    # Makes sure search matches regardless of capitals, so "lexus" finds "Lexus".
    def test_search_is_case_insensitive(self):
        response = self.client.get(reverse('search'), {'q': 'lexus'})
        self.assertContains(response, "2 results for")
        self.assertContains(response, "CLM-001 - 1998 Lexus ES300")

    # Makes sure the "top five" table puts the highest market value first and never shows more than five.
    def test_top_five_orders_by_market_value(self):
        response = self.client.get(reverse('search'))
        top = list(response.context['top_five'])
        self.assertEqual(top[0].market_value, 51200)
        self.assertLessEqual(len(top), 5)

    # Makes sure a tag's page lists every file with that tag and shows the right count.
    def test_tag_detail_lists_related_files_and_count(self):
        response = self.client.get(reverse('tag_detail', args=[self.shared.id]))
        self.assertContains(response, "CLM-001")
        self.assertContains(response, "CLM-002")
        self.assertContains(response, "2 appraisal files with this tag")

    # Makes sure every page loads the shared JavaScript files from static/,
    # since the live filter, lookup and Files section all depend on them.
    def test_layout_loads_static_javascript(self):
        response = self.client.get(reverse('home'))
        for script in ('appraising/app.js', 'appraising/lookup.js', 'appraising/spa.js'):
            self.assertContains(response, script)


# ---------------------------------------------------------------------------
# 3. Form tests
# ---------------------------------------------------------------------------

class AppraisalFormTests(TestCase):
    def setUp(self):
        self.tag = Tag.objects.create(name="Structural Repair")
        self.valid = {'claim_number': 'CLM-010', 'vehicle_desc': '2015 Honda Accord EX-L',
                      'date_assigned': '2026-10-20', 'status': 'Pending', 'tags': [self.tag.id]}

    # Makes sure a complete, sensible appraisal is accepted and saves with its tag.
    def test_valid_data_is_accepted(self):
        form = AppraisalForm(data=self.valid)
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertEqual(list(saved.tags.all()), [self.tag])

    # Makes sure the form refuses to save a file with the required fields left empty,
    # and says which ones are missing.
    def test_missing_required_fields_are_rejected(self):
        form = AppraisalForm(data={'status': 'Open'})
        self.assertFalse(form.is_valid())
        for field in ('claim_number', 'vehicle_desc', 'date_assigned'):
            self.assertIn(field, form.errors)

    # Makes sure the form catches a duplicate claim number with a friendly error
    # instead of letting it reach the database and crash.
    def test_duplicate_claim_number_is_rejected(self):
        AppraisalFile.objects.create(claim_number='CLM-010', vehicle_desc='Existing', date_assigned=date(2026, 1, 1))
        form = AppraisalForm(data=self.valid)
        self.assertFalse(form.is_valid())
        self.assertIn('claim_number', form.errors)

    # Makes sure a vehicle description longer than the 100-character column is refused.
    def test_vehicle_description_over_100_characters_is_rejected(self):
        form = AppraisalForm(data={**self.valid, 'vehicle_desc': 'x' * 101})
        self.assertFalse(form.is_valid())
        self.assertIn('vehicle_desc', form.errors)

    # Makes sure nobody can save a file assigned in the future (a typo like 2062 for 2026
    # would otherwise sit at the top of every "newest first" list), while today still works.
    # Written before the rule existed: it failed first, then the form was changed to pass it.
    def test_future_date_assigned_is_rejected(self):
        today = timezone.localdate()
        future = AppraisalForm(data={**self.valid, 'date_assigned': (today + timedelta(days=1)).isoformat()})
        self.assertFalse(future.is_valid())
        self.assertIn('date_assigned', future.errors)
        self.assertIn("can't be in the future", future.errors['date_assigned'][0])
        self.assertTrue(AppraisalForm(data={**self.valid, 'date_assigned': today.isoformat()}).is_valid())

    # Makes sure only the four real statuses can be saved, not a made-up one.
    def test_unknown_status_is_rejected(self):
        form = AppraisalForm(data={**self.valid, 'status': 'Lost'})
        self.assertFalse(form.is_valid())
        self.assertIn('status', form.errors)


# ---------------------------------------------------------------------------
# 4. Relationship tests
# ---------------------------------------------------------------------------

class RelationshipTests(TestCase):
    def setUp(self):
        self.parent = AppraisalFile.objects.create(claim_number="CLM-003", vehicle_desc="2009 Toyota Camry Hybrid",
                                                   date_assigned=date(2026, 8, 10))
        self.first = VehicleValuation.objects.create(appraisal_file=self.parent, market_value=6200, diminished_value=1200)
        self.second = VehicleValuation.objects.create(appraisal_file=self.parent, market_value=6200, diminished_value=1500)

    # Makes sure a file's valuations can be reached through related_name='valuations'
    # and that both of its valuations come back, which the detail page depends on.
    def test_file_returns_both_of_its_valuations(self):
        self.assertEqual(set(self.parent.valuations.all()), {self.first, self.second})

    # Makes sure one file's valuations never show up under a different file.
    def test_valuations_stay_with_their_own_file(self):
        other = AppraisalFile.objects.create(claim_number="CLM-004", vehicle_desc="Other", date_assigned=date(2026, 8, 11))
        VehicleValuation.objects.create(appraisal_file=other, market_value=100, diminished_value=0)
        self.assertEqual(self.parent.valuations.count(), 2)
        self.assertEqual(other.valuations.count(), 1)

    # Makes sure deleting a file also deletes its valuations, so no orphan
    # valuations are left pointing at a file that no longer exists.
    def test_deleting_a_file_deletes_its_valuations(self):
        self.parent.delete()
        self.assertEqual(VehicleValuation.objects.count(), 0)

    # Makes sure the many-to-many works both ways: one tag reaches both of its files
    # (related_name='appraisal_files'), and one file reaches both of its tags.
    def test_tags_and_files_work_in_both_directions(self):
        dv = Tag.objects.create(name="Diminished Value")
        sr = Tag.objects.create(name="Structural Repair")
        other = AppraisalFile.objects.create(claim_number="CLM-005", vehicle_desc="Other", date_assigned=date(2026, 8, 12))
        self.parent.tags.add(dv, sr)
        other.tags.add(dv)
        self.assertEqual(set(dv.appraisal_files.all()), {self.parent, other})
        self.assertEqual(set(self.parent.tags.all()), {dv, sr})


# ---------------------------------------------------------------------------
# 5. API tests: the JSON endpoint and the single-page Files section
# ---------------------------------------------------------------------------

class AppraisalApiTests(TestCase):
    def setUp(self):
        dv = Tag.objects.create(name="Diminished Value")
        AppraisalFile.objects.create(claim_number="CLM-001", vehicle_desc="1998 Lexus ES300", date_assigned=date(2026, 9, 15), status="Settled")
        b = AppraisalFile.objects.create(claim_number="CLM-003", vehicle_desc="2009 Toyota Camry Hybrid", date_assigned=date(2026, 8, 10), status="Pending")
        AppraisalFile.objects.create(claim_number="CLM-002", vehicle_desc="2019 Porsche Cayenne", date_assigned=date(2026, 10, 2), status="Open")
        b.tags.add(dv)
        VehicleValuation.objects.create(appraisal_file=b, market_value=6200, diminished_value=1200)
        VehicleValuation.objects.create(appraisal_file=b, market_value=6500, diminished_value=1500)
        self.url = reverse('api_appraisals')

    # Makes sure the API answers with real JSON: a list of dictionaries, one per file.
    def test_returns_json_list_of_dicts(self):
        response = self.client.get(self.url)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertEqual(data['count'], 3)
        self.assertIsInstance(data['results'], list)
        self.assertIsInstance(data['results'][0], dict)

    # Makes sure ?q= narrows the results and each row carries its tags and valuation figures.
    def test_query_parameter_returns_fewer_rows(self):
        data = self.client.get(self.url, {'q': 'camry'}).json()
        self.assertEqual(data['count'], 1)
        row = data['results'][0]
        self.assertEqual(row['claim_number'], 'CLM-003')
        self.assertEqual(row['tags'], ['Diminished Value'])
        self.assertEqual(row['valuation_count'], 2)
        self.assertEqual(row['top_market_value'], 6500)

    # Makes sure the ?status= and ?limit= filters both narrow the results.
    def test_status_and_limit(self):
        self.assertEqual(self.client.get(self.url, {'status': 'Open'}).json()['count'], 1)
        self.assertEqual(self.client.get(self.url, {'limit': 2}).json()['count'], 2)

    # Makes sure a search with no matches still returns valid JSON (count 0, empty list), not an error.
    def test_empty_result_is_valid_json(self):
        response = self.client.get(self.url, {'q': 'no-such-car'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['results'], [])
        self.assertEqual(response.json()['count'], 0)

    # Makes sure bad parameters get a JSON error with status 400 instead of an HTML error page.
    def test_bad_parameters_return_json_error(self):
        for params in ({'limit': 'abc'}, {'status': 'Lost'}):
            response = self.client.get(self.url, params)
            self.assertEqual(response.status_code, 400)
            self.assertIn('error', response.json())

    # Makes sure the Live Lookup page loads with the form its JavaScript attaches to.
    def test_lookup_page_renders(self):
        self.assertContains(self.client.get(reverse('lookup')), 'id="lookup-form"')


class FilesSectionTests(TestCase):
    def setUp(self):
        for i in range(1, 26):
            AppraisalFile.objects.create(claim_number=f"CLM-{i:03d}", vehicle_desc=f"Vehicle {i}",
                                         date_assigned=date(2026, 1, 1) + timedelta(days=i))
        self.api = reverse('api_appraisals')

    # Makes sure the list is paged on the server: 10 per page, newest first,
    # and no file shows up on two pages or gets skipped.
    def test_pages_are_sliced_on_the_server(self):
        first = self.client.get(self.api, {'limit': 10, 'page': 1}).json()
        last = self.client.get(self.api, {'limit': 10, 'page': 3}).json()
        self.assertEqual((first['count'], first['total'], first['num_pages']), (10, 25, 3))
        self.assertTrue(first['has_next'])
        self.assertFalse(first['has_previous'])
        self.assertEqual(last['count'], 5)
        self.assertFalse(last['has_next'])
        self.assertEqual(first['results'][0]['claim_number'], 'CLM-025')
        ids = {r['id'] for p in (1, 2, 3) for r in self.client.get(self.api, {'limit': 10, 'page': p}).json()['results']}
        self.assertEqual(len(ids), 25)

    # Makes sure a page number past the end gives a 404 and a non-number gives a 400.
    def test_page_out_of_range_and_bad_page(self):
        self.assertEqual(self.client.get(self.api, {'limit': 10, 'page': 9}).status_code, 404)
        self.assertEqual(self.client.get(self.api, {'page': 'two'}).status_code, 400)

    # Makes sure one file's JSON includes its valuations, and a missing id gives a 404.
    def test_detail_endpoint(self):
        f = AppraisalFile.objects.get(claim_number='CLM-007')
        VehicleValuation.objects.create(appraisal_file=f, market_value=12000, diminished_value=900, negotiation_notes='n')
        data = self.client.get(reverse('api_appraisal_detail', args=[f.id])).json()
        self.assertEqual(data['claim_number'], 'CLM-007')
        self.assertEqual(data['valuations'][0]['market_value'], 12000)
        self.assertEqual(data['spa_url'], f'/files/{f.id}/')
        self.assertEqual(self.client.get(reverse('api_appraisal_detail', args=[999])).status_code, 404)

    # Makes sure the Files section can create a file through the API, and that the
    # API uses the same validation as the form (a duplicate claim number is refused).
    def test_create_via_api(self):
        ok = self.client.post(self.api, {'claim_number': 'CLM-100', 'vehicle_desc': '2007 Toyota Camry LE',
                                         'date_assigned': '2026-11-01', 'status': 'Open'})
        self.assertEqual(ok.status_code, 201)
        self.assertEqual(ok.json()['claim_number'], 'CLM-100')
        dup = self.client.post(self.api, {'claim_number': 'CLM-100', 'vehicle_desc': 'x',
                                          'date_assigned': '2026-11-01', 'status': 'Open'})
        self.assertEqual(dup.status_code, 400)
        self.assertIn('claim_number', dup.json()['errors'])

    # Makes sure every Files URL can be opened directly (bookmark, refresh, shared link)
    # and gets the single-page shell, while a missing file still gets a real 404.
    def test_every_files_url_serves_the_shell(self):
        f = AppraisalFile.objects.first()
        for url in ('/files/', '/files/?page=2', '/files/new/', f'/files/{f.id}/'):
            self.assertContains(self.client.get(url), 'id="files-app"')
        self.assertEqual(self.client.get('/files/999/').status_code, 404)
