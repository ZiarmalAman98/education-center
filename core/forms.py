from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from .models import ContactMessage

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ('name', 'phone', 'email', 'message')
        widgets = {'message': forms.Textarea(attrs={'rows': 5})}


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label='Email address', widget=forms.EmailInput(attrs={'autocomplete': 'email', 'placeholder': 'name@example.com'}))

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if email and password:
            user = get_user_model().objects.filter(email__iexact=email).first()
            self.user_cache = authenticate(self.request, username=user.get_username(), password=password) if user else None
            if self.user_cache is None:
                raise ValidationError('Email یا Password سم نه دی.')
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data
