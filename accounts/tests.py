from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


class AccountsViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.home_url = reverse('home')
        self.test_username = 'testuser'
        self.test_password = 'Password123!'

    def test_register_get(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register.html')

    def test_register_success(self):
        response = self.client.post(self.register_url, {
            'username': self.test_username,
            'password': self.test_password,
            'confirm_password': self.test_password,
        })
        self.assertRedirects(response, self.login_url)
        self.assertTrue(User.objects.filter(username=self.test_username).exists())

    def test_register_password_mismatch(self):
        response = self.client.post(self.register_url, {
            'username': self.test_username,
            'password': self.test_password,
            'confirm_password': 'DifferentPassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'confirm_password', "Passwords do not match.")
        self.assertFalse(User.objects.filter(username=self.test_username).exists())

    def test_register_duplicate_username(self):
        User.objects.create_user(username=self.test_username, password=self.test_password)
        response = self.client.post(self.register_url, {
            'username': self.test_username,
            'password': self.test_password,
            'confirm_password': self.test_password,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'username', "A user with that username already exists.")

    def test_login_get(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')

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

    def test_home_unauthenticated_redirects(self):
        response = self.client.get(self.home_url)
        self.assertRedirects(response, f"{self.login_url}?next=/")

    def test_home_authenticated_displays_username(self):
        User.objects.create_user(username=self.test_username, password=self.test_password)
        self.client.login(username=self.test_username, password=self.test_password)
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/home.html')
        self.assertContains(response, f"You are logged in as {self.test_username}")

    def test_logout(self):
        User.objects.create_user(username=self.test_username, password=self.test_password)
        self.client.login(username=self.test_username, password=self.test_password)
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, self.login_url)
        # Check that user is no longer logged in
        response_home = self.client.get(self.home_url)
        self.assertRedirects(response_home, f"{self.login_url}?next=/")
