from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


class HomeViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('login')
        self.home_url = reverse('home')
        self.test_username = 'testuser'
        self.test_password = 'Password123!'

    def test_home_unauthenticated_redirects(self):
        response = self.client.get(self.home_url)
        self.assertRedirects(response, f"{self.login_url}?next=/")

    def test_home_authenticated_displays_username(self):
        User.objects.create_user(username=self.test_username, password=self.test_password)
        self.client.login(username=self.test_username, password=self.test_password)
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home/home.html')
        self.assertContains(response, f"You are logged in as {self.test_username}")
