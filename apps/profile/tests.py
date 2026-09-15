from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


class ProfileViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('login')
        self.profile_url = reverse('profile')
        self.test_username = 'profileuser'
        self.test_password = 'Password123!'
        self.user = User.objects.create_user(
            username=self.test_username,
            password=self.test_password,
            email='profile@example.com',
            first_name='John',
            last_name='Doe'
        )

    def test_profile_unauthenticated_redirects(self):
        response = self.client.get(self.profile_url)
        self.assertRedirects(response, f"{self.login_url}?next=/profile/")

    def test_profile_authenticated_displays_info(self):
        self.client.login(username=self.test_username, password=self.test_password)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile/profile.html')
        self.assertContains(response, self.test_username)
        self.assertContains(response, 'profile@example.com')

    def test_profile_update(self):
        self.client.login(username=self.test_username, password=self.test_password)
        response = self.client.post(self.profile_url, {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane.smith@example.com'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Jane')
        self.assertEqual(self.user.last_name, 'Smith')
        self.assertEqual(self.user.email, 'jane.smith@example.com')
        self.assertContains(response, 'Your profile details have been updated successfully.')
