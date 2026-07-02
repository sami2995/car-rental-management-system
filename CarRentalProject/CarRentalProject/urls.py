
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from Rental.views import (
    user_login, user_logout, user_signup, dashboard,
    car_list, car_detail, rent_car,
    customer_admin, customer_edit, customer_delete,
    car_admin, car_edit, car_delete,
    rental_admin, rental_edit, rental_delete,
    customer_profile, cancel_rental
)

urlpatterns = [
    path('admin/customers/', customer_admin, name='customer_admin_url'),
    path('admin/customers/<int:customer_id>/edit/', customer_edit, name='customer_edit_url'),
    path('admin/customers/<int:customer_id>/delete/', customer_delete, name='customer_delete_url'),
    
    path('admin/cars/', car_admin, name='car_admin_url'),
    path('admin/cars/<int:car_id>/edit/', car_edit, name='car_edit_url'),
    path('admin/cars/<int:car_id>/delete/', car_delete, name='car_delete_url'),
    
    path('admin/rentals/', rental_admin, name='rental_admin_url'),
    path('admin/rentals/<int:rental_id>/edit/', rental_edit, name='rental_edit_url'),
    path('admin/rentals/<int:rental_id>/delete/', rental_delete, name='rental_delete_url'),

    path('admin/', admin.site.urls),
    
    path('login/', user_login, name='login_url'),
    path('logout/', user_logout, name='logout_url'),
    path('signup/', user_signup, name='signup_url'),
    
    path('dashboard/', dashboard, name='dashboard_url'),
    path('profile/', customer_profile, name='customer_profile_url'),
    path('rentals/<int:rental_id>/cancel/', cancel_rental, name='cancel_rental_url'),
    
    path('', car_list, name='car_list_url'),
    path('cars/<int:car_id>/', car_detail, name='car_detail_url'),
    path('rent/<int:car_id>/', rent_car, name='rent_car_url'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
