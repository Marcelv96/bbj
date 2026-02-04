from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import book_appointment, demo_booking_api, save_player_id
from django.urls import path, include
from django.urls import path
from .views import AnalyticsDashboardView, ClientListView, ExportAnalyticsCSVView, HomeView, SalonBookingView, BarberBookingView, ReduceNoShowsView
from .forms import FlexiblePasswordResetForm

urlpatterns = [

    path('', views.home, name='home'), # A view without the slug requirement

    path(
        "salon-booking-system-south-africa/",
        views.SalonBookingView.as_view(),
        name="salon-booking",
    ),
    path(
        "barber-booking-system/",
        views.BarberBookingView.as_view(),
        name="barber-booking",
    ),
    path(
        "reduce-no-shows/",
        views.ReduceNoShowsView.as_view(),
        name="reduce-no-shows",
    ),


    #path('explore/', views.home, name='home'),
    path('help/', views.user_guide, name='user_guide'),
    path('login-dispatch/', views.login_dispatch, name='login_dispatch'),
    path('business/<int:business_id>/', views.business_detail, name='business_detail'),
    path('business/register/', views.register_business, name='register_business'),
    path('business/<int:business_id>/owner/dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('business/<int:business_id>/owner/bookingform/create/', views.booking_form_create, name='booking_form_create'),
    path('business/<int:business_id>/owner/bookingform/<int:booking_form_id>/edit/', views.booking_form_edit, name='booking_form_edit'),
    path('analytics/export/', ExportAnalyticsCSVView.as_view(), name='export_analytics_csv'),

    path('clients/<int:client_id>/', views.client_detail, name='client_detail'),
    # urls.py
    path('book/<slug:business_slug>/', views.book_appointment, name='book_appointment'),
    path('booking/success/<int:appointment_id>/', views.booking_success, name='booking_success'),
    path('analytics/', AnalyticsDashboardView.as_view(), name='analytics_dashboard'),
    path('ajax/get-staff-for-service/', views.get_staff_for_service, name='get_staff_for_service'),
    path('get-manual-availability/<int:business_id>/', views.get_manual_availability, name='get_manual_availability'),
    path('business/<int:business_id>/manual-booking/', views.manual_booking, name='manual_booking'),
    path('save-player-id/', save_player_id, name='save_player_id'),
    path('appointments/<int:pk>/update-status/', views.update_appointment_status, name='update_appointment_status'),
    path('dashboard/clients/', ClientListView.as_view(), name='client-list'),
    path('toggle-exemption/<int:client_id>/', views.toggle_client_exemption, name='toggle_client_exemption'),
    path('business/<int:business_id>/service/<int:service_id>/delete/', views.service_delete, name='service_delete'),
    path('account-deactivated/', views.staff_deactivated, name='staff_deactivated'),

    path('clients/<int:client_id>/', views.client_detail, name='client_detail'),
    path('clients/<int:client_id>/update/', views.client_update_details, name='client_update_details'),




    # Add this new API endpoint
    path('business/<int:business_id>/api/availability/', views.get_business_availability, name='api_availability'),
    path('api/demo-booking/', demo_booking_api, name='demo_booking_api'),



    # Add this line to your urlpatterns
    path('book/<str:token>/', views.book_appointment_public, name='booking_form_public'),



    path('business/<int:business_id>/owner/service/add/', views.service_create, name='service_create'),
    path('business/<int:business_id>/owner/service/<int:service_id>/edit/', views.service_edit, name='service_edit'),
    path('business/<int:business_id>/owner/staff/add/', views.staff_create, name='staff_create'),
    path('appointment/<int:pk>/', views.appointment_detail, name='appointment_detail'),
    # urls.py
    path('appointment/reschedule/<str:token>/', views.appointment_reschedule, name='appointment_reschedule'),
    path('appointment/<int:pk>/cancel/', views.appointment_cancel, name='appointment_cancel'),
    # urls.py
    path('appointment/cancel/<str:token>/', views.appointment_cancel_guest, name='appointment_cancel_guest'),
    # urls.py
    path('appointments/update-status/<int:pk>/', views.update_appointment_status, name='update_appointment_status'),
    path('appointment/<int:pk>/decision/<str:action>/', views.appointment_email_decision, name='appointment_email_decision'),
    path('contact/', views.contact_view, name='contact_view_url_name'),
    # urls.py
    path('api/available-slots/', views.api_get_available_slots, name='api_available_slots'),
    path('api/get-available-slots/', views.api_get_available_slots, name='api_get_available_slots'),
    path('booking_form/<int:booking_form_id>/book/', book_appointment, name='book_appointment'),

    path('ajax/available-slots/', views.get_available_slots_ajax, name='ajax_available_slots'),
    path('staff/join/', views.join_staff, name='join_staff'),
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('account/profile/', views.profile_view, name='profile'),
    path('test-payment/<int:appointment_id>/', views.test_payment_flow, name='test_payment_flow'),
    path('payfast/itn/', views.payfast_itn, name='payfast_itn'),

    # Update your AJAX url to ensure it accepts the new logic
    path('ajax/available-slots/', views.get_available_slots_ajax, name='get_available_slots_ajax'),
    path('welcome/<slug:business_slug>/', views.business_landing, name='business_landing'),
    path('business/<int:business_id>/toggle-save/', views.toggle_save_business, name='toggle_save'),
    path('my-saved-places/', views.saved_places, name='saved_places'),
    path('business/<int:business_id>/review/', views.leave_review, name='leave_review'),
    path('review/<int:appointment_id>/', views.submit_guest_review, name='submit_guest_review'),
    path('leave-review-ajax/<int:business_id>/', views.leave_review_ajax, name='leave_review_ajax'),
    path('toggle-save-ajax/<int:business_id>/', views.toggle_save_ajax, name='toggle_save_ajax'),
    path('terms/', views.terms_of_service, name='terms'),
    path('privacy/', views.privacy_policy, name='privacy'),
    path('api/notifications/count/', views.get_notification_counts, name='notification_count'),


    path('business/onboarding/', views.business_onboarding, name='business_onboarding'),
    path('setup-choice/', views.business_setup_choice, name='business_setup_choice'),
    path('business/<int:business_id>/appointments/master/', views.master_appointments_view, name='master_appointments'),
    # urls.py
    path('appointments/<int:pk>/', views.appointment_detail, name='appointment_detail'),


    # Registration & Auth
    path('register/', views.register, name='register'),

    path('login/', auth_views.LoginView.as_view(template_name='bookingApp/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             form_class=FlexiblePasswordResetForm,
             # Added 'bookingApp/' prefix below
             template_name='bookingApp/password_reset.html'
         ),
         name='password_reset'),

    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='bookingApp/password_reset_done.html'
         ),
         name='password_reset_done'),

    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='bookingApp/password_reset_confirm.html'
         ),
         name='password_reset_confirm'),

    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='bookingApp/password_reset_complete.html'
         ),
         name='password_reset_complete'),

    path('<slug:business_slug>/', views.general_landing, name='general_landing'),

]