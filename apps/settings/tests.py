from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


class SettingsViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('login')
        self.settings_url = reverse('settings')
        self.test_username = 'settingsuser'
        self.test_password = 'OldPassword123!'
        self.new_password = 'NewPassword456!'
        self.user = User.objects.create_user(
            username=self.test_username,
            password=self.test_password
        )

    def test_settings_unauthenticated_redirects(self):
        response = self.client.get(self.settings_url)
        self.assertRedirects(response, f"{self.login_url}?next=/settings/")

    def test_settings_authenticated_renders_template(self):
        self.client.login(username=self.test_username, password=self.test_password)
        response = self.client.get(self.settings_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'settings/settings.html')
        self.assertContains(response, 'Account Settings')

    def test_settings_password_change(self):
        self.client.login(username=self.test_username, password=self.test_password)
        response = self.client.post(self.settings_url, {
            'old_password': self.test_password,
            'new_password1': self.new_password,
            'new_password2': self.new_password,
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your password was updated successfully.')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))
