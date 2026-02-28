from django import forms
from django.contrib.auth.models import User
from .models import Customer, Car, Rental, Review


# ===============================
# AUTH FORMS
# ===============================

class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("password2"):
            raise forms.ValidationError("Passwords do not match")
        return cleaned


# ===============================
# MODEL FORMS
# ===============================

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        exclude = ['user', 'visible']


class CarForm(forms.ModelForm):
    class Meta:
        model = Car
        exclude = ['visible']


class RentalForm(forms.ModelForm):
    class Meta:
        model = Rental
        exclude = ['visible']


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']