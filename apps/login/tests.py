from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


class LoginViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.home_url = reverse('home')
        self.test_username = 'testuser'
        self.test_password = 'Password123!'

    def test_login_get(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login/login.html')

    def test_login_success(self):
        User.objects.create_user(username=self.test_username, password=self.test_password)
        response = self.client.post(self.login_url, {
            'username': self.test_username,
            'password': self.test_password,
        })
        self.assertRedirects(response, self.home_url)

    def test_login_invalid_credentials(self):
        User.objects.create_user(username=self.test_username, password=self.test_password)
        response = self.client.post(self.login_url, {
            'username': self.test_username,
            'password': 'WrongPassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password.")

    def test_logout(self):
        User.objects.create_user(username=self.test_username, password=self.test_password)
        self.client.login(username=self.test_username, password=self.test_password)
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, self.login_url)
        # Check that user is no longer logged in
        response_home = self.client.get(self.home_url)
        self.assertRedirects(response_home, f"{self.login_url}?next=/")
