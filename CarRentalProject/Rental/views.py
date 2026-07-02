from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum, Avg
from django.views.decorators.http import require_POST
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .models import Customer, Car, Rental, Review
from .forms import SignupForm, CustomerForm, CarForm, RentalForm, ReviewForm, UserRentalRequestForm


def sync_car_availability(car):
    has_active_rental = car.rentals.filter(status="active", visible=True).exists()
    should_be_available = not has_active_rental
    if car.available != should_be_available:
        car.available = should_be_available
        car.save(update_fields=["available"])


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
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data["username"],
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password"],
                )
                Customer.objects.create(
                    user=user,
                    name=form.cleaned_data["name"],
                    email=form.cleaned_data["email"],
                    phone=form.cleaned_data["phone"],
                    address=form.cleaned_data["address"],
                    license_number=form.cleaned_data["license_number"],
                )
            login(request, user)
            return redirect("car_list_url")
        except IntegrityError:
            messages.error(request, "Could not create account. Please verify your details and try again.")
    elif request.method == "POST":
        for error_list in form.errors.values():
            for error in error_list:
                messages.error(request, error)
    return render(request, "signup.html", {"form": form})


def user_logout(request):
    logout(request)
    return redirect("login_url")

@staff_member_required
def dashboard(request):
    # Total revenue from active or completed rentals
    revenue_data = Rental.objects.filter(
        visible=True, 
        status__in=["active", "completed"]
    ).aggregate(Sum("total_cost"))
    total_revenue = revenue_data["total_cost__sum"] or Decimal("0.00")

    # Fleet utilization / occupancy rate
    total_cars = Car.objects.filter(visible=True).count()
    active_rentals = Rental.objects.filter(status="active", visible=True).count()
    occupancy_rate = 0.0
    if total_cars > 0:
        occupancy_rate = round((active_rentals / total_cars) * 100, 1)

    # Average review rating
    avg_rating_data = Review.objects.aggregate(Avg("rating"))
    average_review_rating = avg_rating_data["rating__avg"] or 0.0
    average_review_rating = round(average_review_rating, 1)

    recent_reviews = Review.objects.select_related("car", "customer").order_by("-date_created")[:5]

    context = {
        "total_customers": Customer.objects.filter(visible=True).count(),
        "total_cars": total_cars,
        "available_cars": Car.objects.filter(visible=True, available=True).count(),
        "total_rentals": Rental.objects.filter(visible=True).count(),
        "active_rentals": active_rentals,
        "recent_rentals": Rental.objects.filter(visible=True).select_related("customer", "car")[:10],
        
        # New KPIs
        "total_revenue": total_revenue,
        "occupancy_rate": occupancy_rate,
        "average_review_rating": average_review_rating,
        "recent_reviews": recent_reviews,
    }
    return render(request, "dashboard.html", context)


def car_list(request):
    cars = Car.objects.filter(visible=True)
    search = request.GET.get("search", "").strip()
    if not search:
        search = request.GET.get("brand", "").strip()

    category = request.GET.get("category", "").strip()
    if not category:
        category = request.GET.get("transmission", "").strip()

    max_price = request.GET.get("max_price", "").strip()
    min_year = request.GET.get("min_year", "").strip()
    brand_filter = request.GET.get("brand_filter", "").strip()
    sort_by = request.GET.get("sort_by", "").strip()

    if search:
        cars = cars.filter(
            Q(brand__icontains=search)
            | Q(model__icontains=search)
            | Q(color__icontains=search)
            | Q(plate_number__icontains=search)
        )

    if category in dict(Car.TRANSMISSION_CHOICES):
        cars = cars.filter(transmission=category)

    if max_price:
        try:
            max_price_value = Decimal(max_price)
            if max_price_value >= 0:
                cars = cars.filter(daily_rate__lte=max_price_value)
            else:
                max_price = ""
        except (InvalidOperation, ValueError):
            max_price = ""

    if min_year:
        try:
            min_year_value = int(min_year)
            cars = cars.filter(year__gte=min_year_value)
        except ValueError:
            min_year = ""

    if brand_filter:
        cars = cars.filter(brand__iexact=brand_filter)

    # Sorting
    if sort_by == "price_asc":
        cars = cars.order_by("daily_rate")
    elif sort_by == "price_desc":
        cars = cars.order_by("-daily_rate")
    elif sort_by == "year_desc":
        cars = cars.order_by("-year")
    else:
        # Default ordering matches Meta or standard brand, model
        pass

    # Unique brands for search dropdown
    unique_brands = Car.objects.filter(visible=True).values_list("brand", flat=True).distinct().order_by("brand")

    return render(
        request,
        "car_list.html",
        {
            "cars": cars,
            "current_search": search,
            "current_category": category,
            "current_max_price": max_price,
            "current_min_year": min_year,
            "current_brand_filter": brand_filter,
            "current_sort_by": sort_by,
            "unique_brands": unique_brands,
        },
    )


def car_detail(request, car_id):
    car = get_object_or_404(Car, id=car_id, visible=True)
    reviews = car.reviews.select_related("customer").all()
    can_review = request.user.is_authenticated and hasattr(request.user, "customer")
    form = ReviewForm(request.POST or None)

    if request.method == "POST" and can_review:
        if form.is_valid():
            review = form.save(commit=False)
            review.car = car
            review.customer = request.user.customer
            review.save()
            return redirect("car_detail_url", car_id=car.id)
    elif request.method == "POST" and request.user.is_authenticated and not can_review:
        messages.error(request, "Only customer accounts can submit reviews.")

    return render(
        request,
        "car_detail.html",
        {
            "car": car,
            "reviews": reviews,
            "form": form,
            "can_review": can_review,
        },
    )


@login_required
def rent_car(request, car_id):
    car = get_object_or_404(Car, id=car_id, visible=True)

    if not car.available or car.is_currently_rented:
        messages.error(request, "Car not available")
        return redirect("car_detail_url", car_id=car_id)

    form = UserRentalRequestForm(request.POST or None, car=car)

    if request.method == "POST" and form.is_valid():
        start_date = form.cleaned_data["start_date"]
        end_date = form.cleaned_data["end_date"]
        rental_days = (end_date - start_date).days + 1
        total_cost = car.daily_rate * rental_days

        Rental.objects.create(
            customer=request.user.customer,
            car=car,
            start_date=start_date,
            end_date=end_date,
            total_cost=total_cost,
            status="active",
        )

        sync_car_availability(car)

        return redirect("car_list_url")

    return render(request, "rent_car.html", {"form": form, "car": car})



@staff_member_required
def customer_admin(request):
    form = CustomerForm(request.POST or None)
    customers = Customer.objects.filter(visible=True)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("customer_admin_url")

    return render(request, "customer_admin.html", {"form": form, "customers": customers})


@staff_member_required
def customer_edit(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    form = CustomerForm(request.POST or None, instance=customer)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("customer_admin_url")

    return render(
        request,
        "customer_edit.html",
        {
            "form": form,
            "customer": customer,
        },
    )


@staff_member_required
@require_POST
def customer_delete(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    customer.visible = False
    customer.save()
    return redirect("customer_admin_url")


@staff_member_required
def car_admin(request):
    form = CarForm(request.POST or None, request.FILES or None)
    cars = Car.objects.filter(visible=True)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("car_admin_url")

    return render(request, "car_admin.html", {"form": form, "cars": cars})


@staff_member_required
def car_edit(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    form = CarForm(request.POST or None, request.FILES or None, instance=car)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("car_admin_url")

    return render(
        request,
        "car_edit.html",
        {
            "form": form,
            "car": car,
        },
    )


@staff_member_required
@require_POST
def car_delete(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    car.visible = False
    car.save()
    return redirect("car_admin_url")


@staff_member_required
def rental_admin(request):
    form = RentalForm(request.POST or None)
    rentals = Rental.objects.filter(visible=True)
    customers = Customer.objects.filter(visible=True)
    cars = Car.objects.filter(visible=True)

    if request.method == "POST" and form.is_valid():
        rental = form.save()
        sync_car_availability(rental.car)
        return redirect("rental_admin_url")
    elif request.method == "POST":
        for error_list in form.errors.values():
            for error in error_list:
                messages.error(request, error)

    return render(
        request,
        "rental_admin.html",
        {
            "form": form,
            "rentals": rentals,
            "customers": customers,
            "cars": cars,
        },
    )


@staff_member_required
def rental_edit(request, rental_id):
    rental = get_object_or_404(Rental, id=rental_id)
    previous_car = rental.car
    form = RentalForm(request.POST or None, instance=rental)

    if request.method == "POST" and form.is_valid():
        updated_rental = form.save()
        sync_car_availability(updated_rental.car)
        if previous_car.id != updated_rental.car_id:
            sync_car_availability(previous_car)
        return redirect("rental_admin_url")
    elif request.method == "POST":
        for error_list in form.errors.values():
            for error in error_list:
                messages.error(request, error)

    return render(
        request,
        "rental_edit.html",
        {
            "form": form,
            "rental": rental,
            "customers": Customer.objects.filter(visible=True),
            "cars": Car.objects.filter(visible=True),
        },
    )


@staff_member_required
@require_POST
def rental_delete(request, rental_id):
    rental = get_object_or_404(Rental, id=rental_id)
    car = rental.car
    rental.visible = False
    rental.save()
    sync_car_availability(car)
    return redirect("rental_admin_url")


@login_required
def customer_profile(request):
    if not hasattr(request.user, "customer"):
        messages.error(request, "Staff members do not have customer profiles.")
        return redirect("dashboard_url")

    customer = request.user.customer

    if request.method == "POST":
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("customer_profile_url")
        else:
            for error_list in form.errors.values():
                for error in error_list:
                    messages.error(request, error)
    else:
        form = CustomerForm(instance=customer)

    rentals = customer.rentals.filter(visible=True).select_related("car").order_by("-date_created")
    active_or_upcoming = rentals.filter(status__in=["active", "pending"])
    past_rentals = rentals.filter(status="completed")
    cancelled_rentals = rentals.filter(status="cancelled")

    return render(
        request,
        "profile.html",
        {
            "form": form,
            "customer": customer,
            "active_or_upcoming": active_or_upcoming,
            "past_rentals": past_rentals,
            "cancelled_rentals": cancelled_rentals,
        },
    )


@login_required
@require_POST
def cancel_rental(request, rental_id):
    if not hasattr(request.user, "customer"):
        messages.error(request, "Unauthorized.")
        return redirect("car_list_url")

    rental = get_object_or_404(Rental, id=rental_id, customer=request.user.customer, visible=True)
    if rental.status in ["pending", "active"]:
        rental.status = "cancelled"
        rental.save()
        sync_car_availability(rental.car)
        messages.success(request, f"Rental booking for {rental.car} has been cancelled.")
    else:
        messages.error(request, "This rental booking cannot be cancelled.")

    return redirect("customer_profile_url")
