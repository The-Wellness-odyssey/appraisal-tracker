from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from .models import AppraisalFile, VehicleValuation, Tag


class TagRelationshipTests(TestCase):
    def setUp(self):
        self.shared = Tag.objects.create(name="Negotiated")
        self.a1 = AppraisalFile.objects.create(claim_number="CLM-001", vehicle_desc="1998 Lexus ES300", date_assigned=date(2026, 9, 15))
        self.a2 = AppraisalFile.objects.create(claim_number="CLM-002", vehicle_desc="2019 Porsche Cayenne", date_assigned=date(2026, 10, 2))
        self.a1.tags.add(self.shared)
        self.a2.tags.add(self.shared)
        VehicleValuation.objects.create(appraisal_file=self.a2, market_value=51200, diminished_value=0)
        VehicleValuation.objects.create(appraisal_file=self.a1, market_value=3500, diminished_value=0)

    def test_tag_shared_by_several_files(self):
        self.assertEqual(self.shared.appraisal_files.count(), 2)

    def test_tag_detail_lists_related_files_and_count(self):
        response = self.client.get(reverse('tag_detail', args=[self.shared.id]))
        self.assertContains(response, "CLM-001")
        self.assertContains(response, "CLM-002")
        self.assertContains(response, "2 appraisal files with this tag")

    def test_detail_views_return_404_for_missing_ids(self):
        self.assertEqual(self.client.get(reverse('detail', args=[999])).status_code, 404)
        self.assertEqual(self.client.get(reverse('tag_detail', args=[999])).status_code, 404)

    def test_search_is_case_insensitive(self):
        response = self.client.get(reverse('search'), {'q': 'lexus'})
        self.assertContains(response, "1 result for")
        self.assertContains(response, "CLM-001 - 1998 Lexus ES300")

    def test_top_five_orders_by_market_value(self):
        response = self.client.get(reverse('search'))
        top = list(response.context['top_five'])
        self.assertEqual(top[0].market_value, 51200)
        self.assertLessEqual(len(top), 5)


class AppraisalApiTests(TestCase):
    def setUp(self):
        dv = Tag.objects.create(name="Diminished Value")
        a = AppraisalFile.objects.create(claim_number="CLM-001", vehicle_desc="1998 Lexus ES300", date_assigned=date(2026, 9, 15), status="Settled")
        b = AppraisalFile.objects.create(claim_number="CLM-003", vehicle_desc="2009 Toyota Camry Hybrid", date_assigned=date(2026, 8, 10), status="Pending")
        AppraisalFile.objects.create(claim_number="CLM-002", vehicle_desc="2019 Porsche Cayenne", date_assigned=date(2026, 10, 2), status="Open")
        b.tags.add(dv)
        VehicleValuation.objects.create(appraisal_file=b, market_value=6200, diminished_value=1200)
        VehicleValuation.objects.create(appraisal_file=b, market_value=6500, diminished_value=1500)
        self.url = reverse('api_appraisals')

    def test_returns_json_list_of_dicts(self):
        response = self.client.get(self.url)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertEqual(data['count'], 3)
        self.assertIsInstance(data['results'], list)
        self.assertIsInstance(data['results'][0], dict)

    def test_query_parameter_returns_fewer_rows(self):
        data = self.client.get(self.url, {'q': 'camry'}).json()
        self.assertEqual(data['count'], 1)
        row = data['results'][0]
        self.assertEqual(row['claim_number'], 'CLM-003')
        self.assertEqual(row['tags'], ['Diminished Value'])
        self.assertEqual(row['valuation_count'], 2)
        self.assertEqual(row['top_market_value'], 6500)

    def test_status_and_limit(self):
        self.assertEqual(self.client.get(self.url, {'status': 'Open'}).json()['count'], 1)
        self.assertEqual(self.client.get(self.url, {'limit': 2}).json()['count'], 2)

    def test_empty_result_is_valid_json(self):
        response = self.client.get(self.url, {'q': 'no-such-car'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['results'], [])
        self.assertEqual(response.json()['count'], 0)

    def test_bad_parameters_return_json_error(self):
        for params in ({'limit': 'abc'}, {'status': 'Lost'}):
            response = self.client.get(self.url, params)
            self.assertEqual(response.status_code, 400)
            self.assertIn('error', response.json())

    def test_lookup_page_renders(self):
        self.assertContains(self.client.get(reverse('lookup')), 'id="lookup-form"')


class FilesSectionTests(TestCase):
    """Pagination, detail and create endpoints behind the single-page Files section."""

    def setUp(self):
        for i in range(1, 26):
            AppraisalFile.objects.create(claim_number=f"CLM-{i:03d}", vehicle_desc=f"Vehicle {i}",
                                         date_assigned=date(2026, 1, 1) + timedelta(days=i))
        self.api = reverse('api_appraisals')

    def test_pages_are_sliced_on_the_server(self):
        first = self.client.get(self.api, {'limit': 10, 'page': 1}).json()
        last = self.client.get(self.api, {'limit': 10, 'page': 3}).json()
        self.assertEqual((first['count'], first['total'], first['num_pages']), (10, 25, 3))
        self.assertTrue(first['has_next'])
        self.assertFalse(first['has_previous'])
        self.assertEqual(last['count'], 5)
        self.assertFalse(last['has_next'])
        # Newest first, and no row appears on two pages
        self.assertEqual(first['results'][0]['claim_number'], 'CLM-025')
        ids = {r['id'] for p in (1, 2, 3) for r in self.client.get(self.api, {'limit': 10, 'page': p}).json()['results']}
        self.assertEqual(len(ids), 25)

    def test_page_out_of_range_and_bad_page(self):
        self.assertEqual(self.client.get(self.api, {'limit': 10, 'page': 9}).status_code, 404)
        self.assertEqual(self.client.get(self.api, {'page': 'two'}).status_code, 400)

    def test_detail_endpoint(self):
        f = AppraisalFile.objects.get(claim_number='CLM-007')
        VehicleValuation.objects.create(appraisal_file=f, market_value=12000, diminished_value=900, negotiation_notes='n')
        data = self.client.get(reverse('api_appraisal_detail', args=[f.id])).json()
        self.assertEqual(data['claim_number'], 'CLM-007')
        self.assertEqual(data['valuations'][0]['market_value'], 12000)
        self.assertEqual(data['spa_url'], f'/files/{f.id}/')
        self.assertEqual(self.client.get(reverse('api_appraisal_detail', args=[999])).status_code, 404)

    def test_create_via_api(self):
        ok = self.client.post(self.api, {'claim_number': 'CLM-100', 'vehicle_desc': '2007 Toyota Camry LE',
                                         'date_assigned': '2026-11-01', 'status': 'Open'})
        self.assertEqual(ok.status_code, 201)
        self.assertEqual(ok.json()['claim_number'], 'CLM-100')
        dup = self.client.post(self.api, {'claim_number': 'CLM-100', 'vehicle_desc': 'x',
                                          'date_assigned': '2026-11-01', 'status': 'Open'})
        self.assertEqual(dup.status_code, 400)
        self.assertIn('claim_number', dup.json()['errors'])

    def test_every_files_url_serves_the_shell(self):
        f = AppraisalFile.objects.first()
        for url in ('/files/', '/files/?page=2', '/files/new/', f'/files/{f.id}/'):
            self.assertContains(self.client.get(url), 'id="files-app"')
        self.assertEqual(self.client.get('/files/999/').status_code, 404)
