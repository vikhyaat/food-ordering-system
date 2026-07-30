import re
from datetime import date
from django import forms


class PaymentForm(forms.Form):
    cardholder_name = forms.CharField(max_length=150, label="Cardholder Name")
    card_number = forms.CharField(max_length=19, label="Card Number",
                                   widget=forms.TextInput(attrs={'placeholder': '1234 5678 9012 3456', 'autocomplete': 'off'}))
    expiry_month = forms.ChoiceField(choices=[(f"{m:02d}", f"{m:02d}") for m in range(1, 13)], label="Expiry Month")
    expiry_year = forms.ChoiceField(
        choices=[(str(y), str(y)) for y in range(date.today().year, date.today().year + 11)],
        label="Expiry Year"
    )
    cvv = forms.CharField(max_length=4, min_length=3, label="CVV", widget=forms.PasswordInput(attrs={'autocomplete': 'off'}))
    billing_address = forms.CharField(max_length=255, required=False, label="Billing Address (optional)")

    def clean_card_number(self):
        raw = self.cleaned_data['card_number'].replace(' ', '').replace('-', '')
        if not raw.isdigit() or not (13 <= len(raw) <= 19):
            raise forms.ValidationError("Enter a valid card number (13-19 digits).")
        return raw

    def clean_cvv(self):
        cvv = self.cleaned_data['cvv']
        if not cvv.isdigit():
            raise forms.ValidationError("CVV must be numeric.")
        return cvv

    def clean(self):
        cleaned_data = super().clean()
        month = cleaned_data.get('expiry_month')
        year = cleaned_data.get('expiry_year')
        if month and year:
            today = date.today()
            if int(year) < today.year or (int(year) == today.year and int(month) < today.month):
                raise forms.ValidationError("This card has expired.")
        return cleaned_data
