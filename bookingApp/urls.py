from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('business/<int:business_id>/', views.business_detail, name='business_detail'),
    path('business/register/', views.register_business, name='register_business'),
    path('business/<int:business_id>/owner/dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('business/<int:business_id>/owner/bookingform/create/', views.booking_form_create, name='booking_form_create'),
    path('business/<int:business_id>/owner/bookingform/<int:booking_form_id>/edit/', views.booking_form_edit, name='booking_form_edit'),
    path('bookingform/<int:booking_form_id>/book/', views.book_appointment, name='book_appointment'),
    path('my-appointments/', views.my_appointments, name='my_appointments'),
    path('business/<int:business_id>/owner/service/add/', views.service_create, name='service_create'),
    path('business/<int:business_id>/owner/staff/add/', views.staff_create, name='staff_create'),
    path('appointment/<int:pk>/', views.appointment_detail, name='appointment_detail'),
    path('appointment/<int:pk>/reschedule/', views.appointment_reschedule, name='appointment_reschedule'),
    path('appointment/<int:pk>/cancel/', views.appointment_cancel, name='appointment_cancel'),
    path('appointment/<int:pk>/decision/<str:action>/', views.appointment_email_decision, name='appointment_email_decision'),

    # Registration & Auth
    path('register/', views.register, name='register'),
    # Passing next_page to LogoutView ensures it goes home
    path('login/', auth_views.LoginView.as_view(template_name='bookingApp/login.html', next_page='home'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
]