from django import forms
from django.contrib.auth.models import User


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input-custom',
            'placeholder': 'First Name',
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input-custom',
            'placeholder': 'Last Name',
        })
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-input-custom',
            'placeholder': 'Email Address',
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
