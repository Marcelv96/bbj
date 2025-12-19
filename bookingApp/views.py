from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseForbidden
from django.contrib import messages
from .models import Business, BookingForm, Appointment, Service, Staff
from .forms import (
    AppointmentForm, 
    BookingFormForm, 
    BusinessForm, 
    StaffForm, 
    ServiceForm, 
    RescheduleAppointmentForm, 
    AppointmentStatusForm
)
from .signals import get_owner_gcal_link

def home(request):
    businesses = Business.objects.all().order_by('name')
    return render(request, 'bookingApp/home.html', {'businesses': businesses})

def business_detail(request, business_id):
    business = get_object_or_404(Business, id=business_id)
    booking_forms = business.booking_forms.all()
    return render(request, 'bookingApp/business_detail.html', {
        'business': business,
        'booking_forms': booking_forms,
    })

@login_required
def register_business(request):
    if request.method == 'POST':
        form = BusinessForm(request.POST)
        if form.is_valid():
            business = form.save(commit=False)
            business.owner = request.user
            business.save()
            return redirect('owner_dashboard', business_id=business.id)
    else:
        form = BusinessForm()
    return render(request, 'bookingApp/register_business.html', {'form': form})

@login_required
def owner_dashboard(request, business_id):
    # Owner manages appointments and resources for *their* business only
    business = get_object_or_404(Business, id=business_id, owner=request.user)

    # Fetch all data related to this business
    appointments = Appointment.objects.filter(booking_form__business=business).order_by('-appointment_date', '-appointment_start_time')
    booking_forms = business.booking_forms.all()
    services = business.services.all()  # Uses related_name='services' from models
    staff_members = business.staff_members.all()  # Uses related_name='staff_members'

    return render(request, 'bookingApp/owner_dashboard.html', {
        'business': business,
        'appointments': appointments,
        'booking_forms': booking_forms,
        'services': services,
        'staff_members': staff_members,
    })

@login_required
def booking_form_create(request, business_id):
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    if request.method == 'POST':
        form = BookingFormForm(request.POST)
        if form.is_valid():
            booking_form = form.save(commit=False)
            booking_form.business = business
            booking_form.save()
            return redirect('owner_dashboard', business_id=business.id)
    else:
        form = BookingFormForm()
    return render(request, 'bookingApp/booking_form_create.html', {'form': form, 'business': business})

@login_required
def booking_form_edit(request, business_id, booking_form_id):
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    booking_form = get_object_or_404(BookingForm, id=booking_form_id, business=business)
    if request.method == 'POST':
        form = BookingFormForm(request.POST, instance=booking_form)
        if form.is_valid():
            form.save()
            return redirect('owner_dashboard', business_id=business.id)
    else:
        form = BookingFormForm(instance=booking_form)
    return render(request, 'bookingApp/booking_form_edit.html', {'form': form, 'business': business, 'booking_form': booking_form})


from .forms import AppointmentForm, BookingFormForm, BusinessForm, ServiceForm, StaffForm

# ... (keep home, business_detail, register_business, owner_dashboard views) ...

@login_required
def service_create(request, business_id):
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.business = business
            service.save()
            return redirect('owner_dashboard', business_id=business.id)
    else:
        form = ServiceForm()
    return render(request, 'bookingApp/service_form.html', {'form': form, 'business': business})

@login_required
def staff_create(request, business_id):
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            staff = form.save(commit=False)
            staff.business = business
            staff.save()
            return redirect('owner_dashboard', business_id=business.id)
    else:
        form = StaffForm()
    return render(request, 'bookingApp/staff_form.html', {'form': form, 'business': business})

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.http import HttpResponseForbidden
from django.http import JsonResponse, HttpResponseForbidden
@login_required
def appointment_email_decision(request, pk, action):
    appointment = get_object_or_404(Appointment, pk=pk)
    business = appointment.booking_form.business
    
    if business.owner != request.user:
        return HttpResponseForbidden()

    if action == 'confirm':
        appointment.status = 'confirmed'
        appointment.save()
        
        # Provides the owner with the rich calendar link immediately
        # Generates the link including Service, Staff, Times, and Notes
        gcal_url = get_owner_gcal_link(appointment)
        
        messages.success(request, 
            f'✅ <strong>Appointment Confirmed!</strong><br>'
            f'Customer notified. <a href="{gcal_url}" target="_blank" class="btn btn-sm btn-dark ms-2 shadow-sm">Add to My Calendar</a>', 
            extra_tags='safe'
        )
    elif action == 'decline':
        appointment.status = 'declined'
        appointment.save()
        messages.warning(request, "Appointment declined.")

    return redirect('owner_dashboard', business_id=business.id)

@login_required
def book_appointment(request, booking_form_id):
    booking_form = get_object_or_404(BookingForm, id=booking_form_id)
    business = booking_form.business
    services = Service.objects.filter(business=business)
    staff = Staff.objects.filter(business=business)
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST, services=services, staff=staff)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.booking_form = booking_form
            appointment.customer = request.user
            appointment.save()
            messages.success(request, "Request sent to owner.")
            return redirect('my_appointments')
    else:
        form = AppointmentForm(services=services, staff=staff)
    return render(request, 'bookingApp/book_appointment.html', {'form': form, 'business': business})

@login_required
def my_appointments(request):
    appointments = request.user.appointments.all().order_by('-appointment_date', '-appointment_start_time')
    return render(request, 'bookingApp/my_appointments.html', {'appointments': appointments})

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'bookingApp/register.html', {'form': form})


@login_required
def appointment_detail(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    is_owner = appointment.booking_form.business.owner == request.user
    is_customer = appointment.customer == request.user

    if not (is_owner or is_customer):
        return HttpResponseForbidden("Access Denied")

    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # 1. Handle Customer Reschedule
        if is_customer and 'reschedule_submit' in request.POST:
            form = RescheduleAppointmentForm(request.POST, instance=appointment)
            if form.is_valid():
                appt = form.save(commit=False)
                appt.status = 'pending'  # Reset status upon reschedule
                appt.save()
                return JsonResponse({
                    'status': 'success',
                    'new_status_display': appt.get_status_display(),
                    'new_status_raw': appt.status
                })
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

        # 2. Handle Owner Status Update
        if is_owner:
            status_form = AppointmentStatusForm(request.POST, instance=appointment)
            if status_form.is_valid():
                appt = status_form.save()
                return JsonResponse({
                    'status': 'success',
                    'new_status_display': appt.get_status_display(),
                    'new_status_raw': appt.status
                })
            return JsonResponse({'status': 'error', 'errors': status_form.errors}, status=400)

    # Standard GET request or non-AJAX fallback
    status_form = AppointmentStatusForm(instance=appointment)
    reschedule_form = RescheduleAppointmentForm(instance=appointment)
    
    return render(request, 'bookingApp/appointment_detail.html', {
        'appointment': appointment,
        'is_owner': is_owner,
        'is_customer': is_customer,
        'status_form': status_form,
        'reschedule_form': reschedule_form
    })

@login_required
def appointment_reschedule(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    
    # Only allow if pending or owner requested reschedule
    if appointment.customer != request.user:
         return HttpResponseForbidden()

    if request.method == 'POST':
        form = RescheduleAppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            appt = form.save(commit=False)
            appt.status = 'pending' # Reset to pending after customer reschedules
            appt.save()
            return redirect('my_appointments')
    else:
        form = RescheduleAppointmentForm(instance=appointment)
    
    return render(request, 'bookingApp/appointment_reschedule.html', {'form': form, 'appointment': appointment})

@login_required
def appointment_cancel(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, customer=request.user)
    if request.method == 'POST':
        appointment.status = 'cancelled'
        appointment.save()
        return redirect('my_appointments')
    
    # This must match the folder name exactly
    return render(request, 'bookingApp/appointment_confirm_cancel.html', {'appointment': appointment})