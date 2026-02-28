from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import IntegrityError
from datetime import datetime

from .models import Customer, Car, Rental
from .forms import SignupForm, CustomerForm, CarForm, RentalForm, ReviewForm


# ===============================
# AUTH
# ===============================

def user_login(request):
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password"),
        )
        if user:
            login(request, user)
            return redirect("dashboard_url" if user.is_staff else "car_list_url")
        messages.error(request, "Invalid credentials")
    return render(request, "login.html")


def user_signup(request):
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = User.objects.create_user(
            username=form.cleaned_data["username"],
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
        )
        Customer.objects.create(user=user)
        login(request, user)
        return redirect("car_list_url")
    return render(request, "signup.html", {"form": form})


def user_logout(request):
    logout(request)
    return redirect("login_url")


# ===============================
# DASHBOARD
# ===============================

@staff_member_required
def dashboard(request):
    context = {
        "total_customers": Customer.objects.filter(visible=True).count(),
        "total_cars": Car.objects.filter(visible=True).count(),
        "active_rentals": Rental.objects.filter(status="active", visible=True).count(),
    }
    return render(request, "dashboard.html", context)


# ===============================
# PUBLIC
# ===============================

def car_list(request):
    cars = Car.objects.filter(visible=True)
    return render(request, "car_list.html", {"cars": cars})


def car_detail(request, car_id):
    car = get_object_or_404(Car, id=car_id, visible=True)
    form = ReviewForm(request.POST or None)

    if request.method == "POST" and request.user.is_authenticated:
        if form.is_valid():
            review = form.save(commit=False)
            review.car = car
            review.customer = request.user.customer
            review.save()
            return redirect("car_detail_url", car_id=car.id)

    return render(request, "car_detail.html", {"car": car, "form": form})


@login_required
def rent_car(request, car_id):
    car = get_object_or_404(Car, id=car_id, visible=True)

    if not car.available:
        messages.error(request, "Car not available")
        return redirect("car_detail_url", car_id=car_id)

    form = RentalForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        rental = form.save(commit=False)
        rental.customer = request.user.customer
        rental.car = car
        rental.status = "active"
        rental.save()

        car.available = False
        car.save()

        return redirect("car_list_url")

    return render(request, "rent_car.html", {"form": form, "car": car})


# ===============================
# CUSTOMER ADMIN
# ===============================

@staff_member_required
def customer_admin(request):
    form = CustomerForm(request.POST or None)
    customers = Customer.objects.filter(visible=True)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("customer_admin_url")

    return render(request, "customer_admin.html", {"form": form, "customers": customers})


@staff_member_required
def customer_edit(request, id):
    customer = get_object_or_404(Customer, id=id)
    form = CustomerForm(request.POST or None, instance=customer)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("customer_admin_url")

    return render(request, "customer_edit.html", {"form": form})


@staff_member_required
def customer_delete(request, id):
    customer = get_object_or_404(Customer, id=id)
    customer.visible = False
    customer.save()
    return redirect("customer_admin_url")


# ===============================
# CAR ADMIN
# ===============================

@staff_member_required
def car_admin(request):
    form = CarForm(request.POST or None, request.FILES or None)
    cars = Car.objects.filter(visible=True)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("car_admin_url")

    return render(request, "car_admin.html", {"form": form, "cars": cars})


@staff_member_required
def car_edit(request, id):
    car = get_object_or_404(Car, id=id)
    form = CarForm(request.POST or None, request.FILES or None, instance=car)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("car_admin_url")

    return render(request, "car_edit.html", {"form": form})


@staff_member_required
def car_delete(request, id):
    car = get_object_or_404(Car, id=id)
    car.visible = False
    car.save()
    return redirect("car_admin_url")


# ===============================
# RENTAL ADMIN
# ===============================

@staff_member_required
def rental_admin(request):
    form = RentalForm(request.POST or None)
    rentals = Rental.objects.filter(visible=True)

    if request.method == "POST" and form.is_valid():
        rental = form.save()
        if rental.status == "active":
            rental.car.available = False
            rental.car.save()
        return redirect("rental_admin_url")

    return render(request, "rental_admin.html", {"form": form, "rentals": rentals})


@staff_member_required
def rental_edit(request, id):
    rental = get_object_or_404(Rental, id=id)
    form = RentalForm(request.POST or None, instance=rental)

    if request.method == "POST" and form.is_valid():
        rental = form.save()
        rental.car.available = rental.status != "active"
        rental.car.save()
        return redirect("rental_admin_url")

    return render(request, "rental_edit.html", {"form": form})


@staff_member_required
def rental_delete(request, id):
    rental = get_object_or_404(Rental, id=id)
    rental.visible = False
    rental.save()
    return redirect("rental_admin_url")