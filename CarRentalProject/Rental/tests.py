from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import date, timedelta

from .models import Customer, Car, Rental, Review
from .forms import RentalForm


class CarModelTests(TestCase):
    def setUp(self):
        self.car = Car.objects.create(
            brand="Tesla",
            model="Model 3",
            year=2022,
            color="Red",
            plate_number="AA-3-B99999",
            transmission="automatic",
            daily_rate=1500.00
        )
        self.user1 = User.objects.create_user(username="cust1", password="pass123")
        self.customer1 = Customer.objects.create(
            user=self.user1,
            name="John Doe",
            email="john@example.com",
            phone="12345",
            address="Addis",
            license_number="DL1"
        )
        self.user2 = User.objects.create_user(username="cust2", password="pass123")
        self.customer2 = Customer.objects.create(
            user=self.user2,
            name="Jane Smith",
            email="jane@example.com",
            phone="67890",
            address="Addis",
            license_number="DL2"
        )

    def test_average_rating_no_reviews(self):
        self.assertEqual(self.car.average_rating, 0.0)
        self.assertEqual(len(self.car.star_range), 0)
        self.assertEqual(len(self.car.empty_star_range), 5)

    def test_average_rating_with_reviews(self):
        Review.objects.create(car=self.car, customer=self.customer1, rating=5, comment="Amazing!")
        Review.objects.create(car=self.car, customer=self.customer2, rating=4, comment="Good")
        
        self.assertEqual(self.car.average_rating, 4.5)
        # 4.5 rounds to 4 for stars in round() logic
        self.assertEqual(len(self.car.star_range), 4)
        self.assertEqual(len(self.car.empty_star_range), 1)


class RentalFormTests(TestCase):
    def setUp(self):
        self.car = Car.objects.create(
            brand="Toyota",
            model="Yaris",
            year=2020,
            color="Blue",
            plate_number="AA-3-Y11111",
            transmission="manual",
            daily_rate=1200.00
        )
        self.user = User.objects.create_user(username="cust", password="pass123")
        self.customer = Customer.objects.create(
            user=self.user,
            name="Abebe",
            email="abebe@example.com",
            phone="55555",
            address="Addis",
            license_number="DL3"
        )
        # Create an active rental for dates: June 15 to June 20
        self.existing_rental = Rental.objects.create(
            customer=self.customer,
            car=self.car,
            start_date=date(2026, 6, 15),
            end_date=date(2026, 6, 20),
            total_cost=7200.00,
            status="active"
        )

    def test_rental_no_overlap(self):
        # Book June 10 to June 14 (ends before existing starts)
        form_data = {
            "customer": self.customer.id,
            "car": self.car.id,
            "start_date": date(2026, 6, 10),
            "end_date": date(2026, 6, 14),
            "total_cost": 6000.00,
            "status": "active"
        }
        form = RentalForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_rental_overlap_start(self):
        # Book June 14 to June 16 (overlaps start on June 15)
        form_data = {
            "customer": self.customer.id,
            "car": self.car.id,
            "start_date": date(2026, 6, 14),
            "end_date": date(2026, 6, 16),
            "total_cost": 3600.00,
            "status": "active"
        }
        form = RentalForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("This car already has an active rental in that date range.", form.non_field_errors())
