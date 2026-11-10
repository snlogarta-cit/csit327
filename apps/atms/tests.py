import json
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from apps.atms.models import (
    ATM,
    ATMNetwork,
    ATMReport,
    Bank,
    CardNetwork,
    StatusReport,
    HAS_GIS,
)

User = get_user_model()


class ATMFeatureTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.username = 'atm_tester'
        self.password = 'SecurePass123!'
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email='tester@atmosphere.ph'
        )

        self.bank = Bank.objects.create(
            bank_name='Test Metro Bank',
            logo_url='https://example.com/bank.png'
        )
        self.network_bancnet = CardNetwork.objects.create(
            network_name='BancNet',
            logo_url='https://example.com/bancnet.png'
        )
        self.network_visa = CardNetwork.objects.create(
            network_name='Visa',
            logo_url='https://example.com/visa.png'
        )

        self.atm = ATM.objects.create(
            name='Test Central Branch ATM',
            bank=self.bank,
            latitude=Decimal('14.55470000'),
            longitude=Decimal('121.02440000'),
            address_line='123 Ayala Avenue, Makati City',
            is_active=True,
        )
        self.atm.networks.add(self.network_bancnet, self.network_visa)

    def test_unauthenticated_cannot_add_atm(self):
        url_add = reverse('atms:atm-add')
        url_list = reverse('atms:atm-list')
        payload = {
            'name': 'Unauthorized ATM',
            'bank': self.bank.bank_id,
            'address_line': 'Nowhere',
            'latitude': 14.5000,
            'longitude': 121.0000,
        }

        # POST to /api/atms/add/
        res_add = self.client.post(url_add, data=json.dumps(payload), content_type='application/json')
        self.assertIn(res_add.status_code, [401, 403])

        # POST to /api/atms/
        res_list = self.client.post(url_list, data=json.dumps(payload), content_type='application/json')
        self.assertIn(res_list.status_code, [401, 403])

    def test_authenticated_add_atm_success(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse('atms:atm-add')
        payload = {
            'name': 'New BGC High Street ATM',
            'bank': self.bank.bank_id,
            'address_line': 'Bonifacio High Street, Taguig City',
            'latitude': 14.5512,
            'longitude': 121.0505,
            'network_ids': [self.network_bancnet.network_id, self.network_visa.network_id],
        }

        res = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 201)

        data = res.json()
        props = data.get('properties', data)
        self.assertEqual(props['name'], 'New BGC High Street ATM')
        self.assertEqual(props['bank_id'], self.bank.bank_id)

        # Check DB persistence
        created_atm = ATM.objects.get(name='New BGC High Street ATM')
        self.assertEqual(created_atm.bank, self.bank)
        self.assertEqual(created_atm.networks.count(), 2)

        if HAS_GIS:
            self.assertIsNotNone(created_atm.location)
            self.assertAlmostEqual(created_atm.location.x, 121.0505, places=4)
            self.assertAlmostEqual(created_atm.location.y, 14.5512, places=4)

    def test_authenticated_add_atm_via_root_endpoint(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse('atms:atm-list')
        payload = {
            'name': 'Root Endpoint ATM',
            'bank': self.bank.bank_id,
            'address': 'Taft Avenue, Manila',
            'latitude': 14.5800,
            'longitude': 120.9800,
            'networks': [self.network_bancnet.network_id],
        }

        res = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(ATM.objects.filter(name='Root Endpoint ATM').exists())

    def test_add_atm_validation_errors(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse('atms:atm-add')

        # Invalid latitude (> 90)
        res = self.client.post(url, data=json.dumps({
            'name': 'Bad Lat ATM',
            'bank': self.bank.bank_id,
            'address_line': 'Sample Address',
            'latitude': 95.0,
            'longitude': 121.0,
        }), content_type='application/json')
        self.assertEqual(res.status_code, 400)

        # Invalid longitude (> 180)
        res = self.client.post(url, data=json.dumps({
            'name': 'Bad Lng ATM',
            'bank': self.bank.bank_id,
            'address_line': 'Sample Address',
            'latitude': 14.0,
            'longitude': 195.0,
        }), content_type='application/json')
        self.assertEqual(res.status_code, 400)

        # Missing bank
        res = self.client.post(url, data=json.dumps({
            'name': 'No Bank ATM',
            'address_line': 'Sample Address',
            'latitude': 14.0,
            'longitude': 121.0,
        }), content_type='application/json')
        self.assertEqual(res.status_code, 400)

        # Non-existent bank
        res = self.client.post(url, data=json.dumps({
            'name': 'Ghost Bank ATM',
            'bank': 999999,
            'address_line': 'Sample Address',
            'latitude': 14.0,
            'longitude': 121.0,
        }), content_type='application/json')
        self.assertEqual(res.status_code, 400)

    def test_unauthenticated_cannot_report(self):
        url_status = reverse('atms:atm-status-report')
        url_issue = reverse('atms:atm-issue-report')

        res_s = self.client.post(url_status, data=json.dumps({
            'atm': self.atm.atm_id,
            'is_online': True,
            'has_cash': True,
        }), content_type='application/json')
        self.assertIn(res_s.status_code, [401, 403])

        res_i = self.client.post(url_issue, data=json.dumps({
            'atm': self.atm.atm_id,
            'report_type': 'GENERAL_NOTE',
            'comment': 'Test issue',
        }), content_type='application/json')
        self.assertIn(res_i.status_code, [401, 403])

    def test_authenticated_status_report_creation(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse('atms:atm-status-report')

        payload = {
            'atm': self.atm.atm_id,
            'is_online': True,
            'has_cash': False,
        }
        res = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 201)

        # Verify report in DB
        report = StatusReport.objects.filter(atm=self.atm).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.user, self.user)
        self.assertTrue(report.is_online)
        self.assertFalse(report.has_cash)

        # Verify latest_status on ATM
        self.assertEqual(self.atm.latest_status.has_cash, False)

    def test_authenticated_status_report_with_helper_string(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse('atms:atm-status-report')

        # Test 'ONLINE'
        res = self.client.post(url, data=json.dumps({
            'atm': self.atm.atm_id,
            'status': 'ONLINE',
        }), content_type='application/json')
        self.assertEqual(res.status_code, 201)
        latest = self.atm.status_reports.latest('created_at')
        self.assertTrue(latest.is_online)
        self.assertTrue(latest.has_cash)

        # Test 'OFFLINE'
        res = self.client.post(url, data=json.dumps({
            'atm': self.atm.atm_id,
            'status': 'OFFLINE',
        }), content_type='application/json')
        self.assertEqual(res.status_code, 201)
        latest = self.atm.status_reports.latest('created_at')
        self.assertFalse(latest.is_online)

    def test_authenticated_issue_report_creation(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse('atms:atm-issue-report')

        payload = {
            'atm': self.atm.atm_id,
            'report_type': 'FEE_DISCREPANCY',
            'actual_fee': '25.00',
            'comment': 'Interbank fee was charged 25 pesos instead of fee-free.',
        }
        res = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 201)

        issue = ATMReport.objects.filter(atm=self.atm).first()
        self.assertIsNotNone(issue)
        self.assertEqual(issue.user, self.user)
        self.assertEqual(issue.report_type, 'FEE_DISCREPANCY')
        self.assertEqual(issue.actual_fee, Decimal('25.00'))

    def test_authenticated_issue_report_normalization(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse('atms:atm-issue-report')

        # Lowercase 'location' should normalize to 'LOCATION_INACCURATE'
        res = self.client.post(url, data=json.dumps({
            'atm': self.atm.atm_id,
            'report_type': 'location',
            'note': 'The pin is across the street near the grocery store.',
        }), content_type='application/json')
        self.assertEqual(res.status_code, 201)

        issue = ATMReport.objects.filter(atm=self.atm).latest('created_at')
        self.assertEqual(issue.report_type, 'LOCATION_INACCURATE')
        self.assertIn('across the street', issue.comment)

    def test_status_report_delegation_to_issue_report(self):
        """If a client posts issue report fields to /api/atms/report/, it handles it gracefully."""
        self.client.login(username=self.username, password=self.password)
        url = reverse('atms:atm-status-report')

        res = self.client.post(url, data=json.dumps({
            'atm': self.atm.atm_id,
            'report_type': 'GENERAL_NOTE',
            'comment': 'Hand sanitizer dispenser is empty beside ATM.',
        }), content_type='application/json')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(ATMReport.objects.filter(comment__contains='Hand sanitizer').exists())

    def test_public_read_endpoints(self):
        # 1. ATM list (FeatureCollection)
        res_list = self.client.get(reverse('atms:atm-list'))
        self.assertEqual(res_list.status_code, 200)
        data = res_list.json()
        self.assertEqual(data.get('type'), 'FeatureCollection')
        self.assertGreaterEqual(len(data.get('features', [])), 1)

        # 2. Nearby ATMs
        res_nearby = self.client.get(f"{reverse('atms:atm-nearby')}?lat=14.5547&lng=121.0244&radius=5000")
        self.assertEqual(res_nearby.status_code, 200)
        nearby_data = res_nearby.json()
        self.assertEqual(nearby_data.get('type'), 'FeatureCollection')

        # 3. Banks list
        res_banks = self.client.get(reverse('atms:bank-list'))
        self.assertEqual(res_banks.status_code, 200)
        banks = res_banks.json()
        self.assertTrue(any(b['bank_name'] == 'Test Metro Bank' for b in banks))

        # 4. Card networks list
        res_nets = self.client.get(reverse('atms:network-list'))
        self.assertEqual(res_nets.status_code, 200)
        networks = res_nets.json()
        self.assertTrue(any(n['network_name'] == 'BancNet' for n in networks))
