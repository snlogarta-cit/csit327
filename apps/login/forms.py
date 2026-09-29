from django import forms


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your username',
            'autocomplete': 'username',
            'class': 'form-input-custom font-medium text-slate-800 placeholder-slate-400'
        })
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
            'class': 'form-input-custom font-medium text-slate-800 placeholder-slate-400'
        })
    )
