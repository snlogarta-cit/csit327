from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


class RegisterViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.test_username = 'testuser'
        self.test_password = 'Password123!'

    def test_register_get(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register/register.html')

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
