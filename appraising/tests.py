from datetime import date

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
