from django import forms
from .models import Order


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['full_name', 'phone', 'email', 'address', 'city', 'state', 'pincode', 'delivery_instructions']
        widgets = {
            'delivery_instructions': forms.Textarea(attrs={'rows': 2, 'placeholder': 'e.g. Ring the bell, leave at the door...'}),
        }
