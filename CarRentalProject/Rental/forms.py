from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Customer, Car, Rental, Review


# ===============================
# AUTH FORMS
# ===============================

class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)
    name = forms.CharField(max_length=200)
    phone = forms.CharField(max_length=20)
    address = forms.CharField(widget=forms.Textarea)
    license_number = forms.CharField(max_length=50)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if Customer.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email is already registered.")
        return email

    def clean_license_number(self):
        license_number = self.cleaned_data.get("license_number", "").strip()
        if Customer.objects.filter(license_number__iexact=license_number).exists():
            raise forms.ValidationError("License number is already registered.")
        return license_number

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

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get("start_date")
        end_date = cleaned.get("end_date")
        car = cleaned.get("car")
        status = cleaned.get("status")

        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", "End date must be on or after start date.")

        if car and start_date and end_date and status == "active":
            overlaps = Rental.objects.filter(
                car=car,
                visible=True,
                status="active",
                start_date__lte=end_date,
                end_date__gte=start_date,
            )
            if self.instance.pk:
                overlaps = overlaps.exclude(pk=self.instance.pk)
            if overlaps.exists():
                raise forms.ValidationError("This car already has an active rental in that date range.")

        return cleaned


class UserRentalRequestForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, **kwargs):
        self.car = kwargs.pop("car", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get("start_date")
        end_date = cleaned.get("end_date")

        if start_date and start_date < timezone.localdate():
            self.add_error("start_date", "Start date cannot be in the past.")

        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", "End date must be on or after start date.")

        if self.car and start_date and end_date:
            overlaps = self.car.rentals.filter(
                visible=True,
                status="active",
                start_date__lte=end_date,
                end_date__gte=start_date,
            ).exists()
            if overlaps:
                raise forms.ValidationError("This car is already booked for the selected dates.")

        return cleaned


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
