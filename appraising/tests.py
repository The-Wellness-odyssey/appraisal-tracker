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
