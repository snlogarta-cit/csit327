from django import forms
from django.contrib.auth.forms import PasswordChangeForm


class CalmPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-input-custom'
            })
