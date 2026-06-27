from django import forms
from .models import Order


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['full_name', 'email', 'address', 'city', 'postal_code', 'country', 'note']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Jane Doe', 'autocomplete': 'name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'jane@example.com', 'autocomplete': 'email'}),
            'address': forms.TextInput(attrs={'placeholder': '221B Baker Street', 'autocomplete': 'street-address'}),
            'city': forms.TextInput(attrs={'placeholder': 'London', 'autocomplete': 'address-level2'}),
            'postal_code': forms.TextInput(attrs={'placeholder': 'NW1 6XE', 'autocomplete': 'postal-code'}),
            'country': forms.TextInput(attrs={'placeholder': 'United Kingdom', 'autocomplete': 'country-name'}),
            'note': forms.Textarea(attrs={'placeholder': 'Anything we should know? (optional)', 'rows': 3}),
        }
