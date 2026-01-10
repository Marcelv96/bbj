# ===========================
# Django Core
# ===========================
from django.shortcuts import render, redirect, get_object_or_404
from django.http import (
    JsonResponse,
    HttpResponse,
    HttpResponseForbidden,
)
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import TemplateView
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import localtime
from django.db.models import (
    Q,
    Avg,
    Count,
    Sum,
    Prefetch,
)
from django.db.models.functions import ExtractHour
from django.core.mail import send_mail, EmailMessage
from django.core.serializers.json import DjangoJSONEncoder
from django.core.paginator import Paginator

# ===========================
# Python Standard Library
# ===========================
import json
import logging
import hashlib
import urllib.parse
from datetime import (
    datetime,
    date,
    time,
    timedelta,
)
from urllib.parse import urlencode

# ===========================
# Third-Party
# ===========================
import requests

# ===========================
# Local Models
# ===========================
from .models import (
    Business,
    BookingForm,
    Appointment,
    Service,
    Staff,
    Review,
    Profile,
    OperatingHours,
    BusinessBlock,
    StaffBlock,
    StaffOperatingHours,
    SavedBusiness,
)

# ===========================
# Local Forms
# ===========================
from .forms import (
    AppointmentForm,
    BookingFormForm,
    BusinessForm,
    BusinessOnboardingForm,
    ServiceForm,
    StaffForm,
    StaffServicesForm,
    StaffFormSet,
    ServiceFormSet,
    ManualBookingForm,
    RescheduleAppointmentForm,
    AppointmentStatusForm,
    CustomUserCreationForm,
)

# ===========================
# Local Utilities / Signals
# ===========================
from .utils import (
    get_available_times,
    trigger_pending_reminders,
    cleanup_expired_appointments,
    generate_payfast_url,
    generate_appointment_payfast_url,
    send_deposit_request_email,
    send_owner_paid_notification,
)
from .signals import get_owner_gcal_link

# ===========================
# Logging
# ===========================
logger = logging.getLogger(__name__)


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # ✅ auto-login
            return redirect('business_onboarding')  # ✅ redirect here
    else:
        form = CustomUserCreationForm()

    return render(request, 'bookingApp/register.html', {'form': form})


@login_required
def login_dispatch(request):
    # 1. Check for Business Ownership (Priority 1)
    # Using hasattr to check the OneToOne relationship defined in your models
    if hasattr(request.user, 'business'):
        return redirect('owner_dashboard', business_id=request.user.business.id)

    # 2. Check for Staff Profile (Priority 2)
    # This identifies employees who joined via a join_code
    if hasattr(request.user, 'staff_profile'):
        return redirect('staff_dashboard')

    # 3. Authenticated but neither Owner nor Staff
    # Send them to the onboarding page to register their business
    return redirect('business_onboarding')
# bookingApp/views.py
def user_guide(request):
    return render(request, 'bookingApp/help_page.html')

def error_404(request, exception):
    return render(request, '404.html', status=404)

def error_500(request):
    return render(request, '500.html', status=500)

def error_400(request, exception):
    return render(request, '400.html', status=400)


# def home(request):
#     # -----------------------------
#     # Capture search inputs from URL
#     # -----------------------------
#     query = request.GET.get('q', '')          # Search by business name / service
#     location = request.GET.get('location', '')  # Search by city / address
#
#     # -----------------------------
#     # Determine current weekday
#     # -----------------------------
#     now = datetime.now()
#     today_weekday = now.weekday()  # Monday = 0, Sunday = 6
#
#     # Map weekday to operating hours type
#     if today_weekday < 5:
#         current_day_type = 'mon_fri'
#     elif today_weekday == 5:
#         current_day_type = 'sat'
#     else:
#         current_day_type = 'sun'
#
#     # -----------------------------
#     # Prefetch ONLY today's operating hours
#     # -----------------------------
#     hours_prefetch = Prefetch(
#         'operating_hours',
#         queryset=OperatingHours.objects.filter(day_type=current_day_type),
#         to_attr='today_hours'  # Accessible as business.today_hours
#     )
#
#     # -----------------------------
#     # Base queryset for businesses
#     # -----------------------------
#     businesses = Business.objects.annotate(
#         calculated_rating=Avg('reviews__rating'),
#         total_reviews=Count('reviews')
#     ).prefetch_related(
#         hours_prefetch,
#         'services'
#     ).order_by('name')
#
#     # -----------------------------
#     # Filter by Name / Industry / Service
#     # -----------------------------
#     if query:
#         businesses = businesses.filter(
#             Q(name__icontains=query) |
#             Q(industry__icontains=query) |
#             Q(services__name__icontains=query)
#         )
#
#     # -----------------------------
#     # Filter by Location (Address / City)
#     # -----------------------------
#     if location:
#         businesses = businesses.filter(address__icontains=location)
#
#     # -----------------------------
#     # Remove duplicates caused by joins
#     # -----------------------------
#     if query or location:
#         businesses = businesses.distinct()
#
#     # -----------------------------
#     # Context for template
#     # -----------------------------
#     context = {
#         'businesses': businesses,
#         'search_query': query,
#         'location_query': location,
#     }
#
#     return render(request, 'bookingApp/home.html', context)


from django.shortcuts import render, redirect
from .models import Business, Staff

def home(request):
    if request.user.is_authenticated:
        # 1. Check if the user is a Business Owner
        owned_business = Business.objects.filter(owner=request.user).first()
        if owned_business:
            return redirect('owner_dashboard', business_id=owned_business.id)

        # 2. Check if the user is a Staff Member (but not the owner)
        is_staff = Staff.objects.filter(user=request.user).exists()
        if is_staff:
            return redirect('staff_dashboard')

        # 3. If they are just a regular customer/user
        return redirect('business_onboarding')

    # If not logged in, show the marketing landing page
    return render(request, 'bookingApp/landing.html')

def general_landing(request, business_slug):
    # This renders a specific business's booking page
    business = get_object_or_404(Business, slug=business_slug)
    return render(request, 'bookingApp/landing.html', {'business': business})

def business_detail(request, business_id):
    business = get_object_or_404(Business, id=business_id)

    # Core data
    reviews = business.reviews.all().order_by('-created_at')
    average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 5.0

    # Booking Modal data
    services = business.services.all()
    staff_members = business.staff_members.all()
    booking_form = business.booking_forms.first()

    # User-specific flags
    is_saved = False
    is_owner = False
    user_business_id = None

    if request.user.is_authenticated:
        # Check if user saved this business
        is_saved = SavedBusiness.objects.filter(
            user=request.user,
            business=business
        ).exists()

        # Check ownership safely
        # Assuming your User model has an 'is_owner' field or property
        is_owner = getattr(request.user, 'is_owner', False)

        # Safely get the business ID for the owner dashboard link
        if hasattr(request.user, 'business') and request.user.business:
            user_business_id = request.user.business.id

    # Operating Hours
    DAY_LABELS = {'mon_fri': 'Mon - Fri', 'sat': 'Sat', 'sun': 'Sun'}
    operating_hours_display = {
        DAY_LABELS[o.day_type]: o for o in business.operating_hours.all()
    }

    context = {
        'business': business,
        'services': services,
        'staff_members': staff_members,
        'booking_form': booking_form,
        'operating_hours': operating_hours_display,
        'reviews': reviews,
        'average_rating': round(average_rating, 1),
        'is_saved': is_saved,
        'is_owner': is_owner,
        'user_business_id': user_business_id, # Passed for the template link
    }

    return render(request, 'bookingApp/business_detail.html', context)

def get_business_availability(request, business_id):
    business = get_object_or_404(Business, id=business_id)
    date_str = request.GET.get('date')
    staff_id = request.GET.get('staff_id')
    service_id = request.GET.get('service_id') # Added to support dynamic length

    if not date_str:
        return JsonResponse({'slots': []})

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({'slots': []})

    # 1. Determine Day Type
    weekday = target_date.weekday()
    day_key = 'mon_fri' if weekday <= 4 else ('sat' if weekday == 5 else 'sun')

    # 2. Get Service Duration
    service = Service.objects.filter(id=service_id).first()
    duration = service.default_length_minutes if service else 30

    # 3. Use the robust utility for availability calculation
    # This utility handles BusinessBlocks, StaffBlocks, and existing Appointments
    available_slots = get_available_times(
        business=business,
        appointment_date=target_date,
        service_length=duration,
        staff_id=staff_id if staff_id and staff_id != 'None' else None
    )

    # Format for the frontend: both as a simple list and as objects for the wizard
    # This prevents the script from breaking if it expects one or the other
    formatted_slots = [{'value': s, 'label': s} for s in available_slots]

    return JsonResponse({
        'slots': formatted_slots,      # For the Wizard/Modal
        'simple_slots': available_slots # For the Quick-View widget
    })

@login_required
def toggle_save_ajax(request, business_id):
    business = get_object_or_404(Business, id=business_id)
    saved_item, created = SavedBusiness.objects.get_or_create(user=request.user, business=business)
    if not created:
        saved_item.delete()
        saved = False
    else:
        saved = True
    return JsonResponse({'saved': saved})

@login_required
def leave_review_ajax(request, business_id):
    if request.method == 'POST':
        business = get_object_or_404(Business, id=business_id)
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        review = Review.objects.create(
            business=business,
            user=request.user,
            rating=rating,
            comment=comment
        )

        # Render just the single new review item to prepend
        html = render_to_string('bookingApp/includes/review_item.html', {'review': review})
        return JsonResponse({'success': True, 'html': html})
# Standalone Toggle, Saved Places, and Review functions remain as you provided...
@login_required
def toggle_save_business(request, business_id):
    """Toggles the 'Saved' status of a business for the current user."""
    business = get_object_or_404(Business, id=business_id)
    saved, created = SavedBusiness.objects.get_or_create(user=request.user, business=business)

    if not created:
        saved.delete()
        is_saved = False
        messages.info(request, f"Removed {business.name} from your saved places.") #
    else:
        is_saved = True
        messages.success(request, f"Saved {business.name} to your places!") #

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'is_saved': is_saved})
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def saved_places(request):
    """Displays a list of businesses saved by the user."""
    saved_items = SavedBusiness.objects.filter(user=request.user).select_related('business')

    if not saved_items.exists():
        messages.info(request, "You haven't saved any places yet.") #

    return render(request, 'bookingApp/saved_places.html', {'saved_items': saved_items})

@login_required
def leave_review(request, business_id):
    """Handles submission or update of business reviews."""
    business = get_object_or_404(Business, id=business_id)

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        # We use filter().first() to ensure we don't crash if duplicates exist
        # and then update that specific one, or create a new one.
        review = Review.objects.filter(user=request.user, business=business).first()

        if review:
            review.rating = rating
            review.comment = comment
            review.save()
        else:
            Review.objects.create(
                user=request.user,
                business=business,
                rating=rating,
                comment=comment
            )

        messages.success(request, "Review submitted successfully!")
        return redirect('business_detail', business_id=business.id)

    return redirect('business_detail', business_id=business.id)




@login_required
def register_business(request):
    # 🔒 HARD BLOCK: user already has a business
    if hasattr(request.user, 'business'):
        messages.warning(
            request,
            "You can only register one business. Please contact sales to add additional locations."
        )
        return redirect('owner_dashboard')  # or owner_dashboard of their existing business

    if request.method == 'POST':
        form = BusinessForm(request.POST, request.FILES)
        if form.is_valid():
            business = form.save(commit=False)
            business.owner = request.user
            business.save()

            day_types = [
                ('mon_fri', form.cleaned_data.get('mon_fri_open'), form.cleaned_data.get('mon_fri_close')),
                ('sat', form.cleaned_data.get('sat_open'), form.cleaned_data.get('sat_close')),
                ('sun', form.cleaned_data.get('sun_open'), form.cleaned_data.get('sun_close')),
            ]

            for day_type, open_time, close_time in day_types:
                if open_time and close_time:
                    OperatingHours.objects.update_or_create(
                        business=business,
                        day_type=day_type,
                        defaults={'open_time': open_time, 'close_time': close_time}
                    )
                else:
                    OperatingHours.objects.filter(
                        business=business,
                        day_type=day_type
                    ).delete()

            return redirect('owner_dashboard', business_id=business.id)
    else:
        form = BusinessForm()

    return render(request, 'bookingApp/register_business.html', {'form': form})



@login_required
def business_onboarding(request, business_id=None):
    business = None
    if business_id:
        business = get_object_or_404(Business, id=business_id, owner=request.user)
    elif hasattr(request.user, 'business'):
        return redirect('owner_dashboard', business_id=request.user.business.id)

    if request.method == 'POST':
        form = BusinessOnboardingForm(request.POST, request.FILES, instance=business)
        service_formset = ServiceFormSet(request.POST, instance=business)

        if form.is_valid() and service_formset.is_valid():
            is_new_business = business is None
            business = form.save(commit=False)
            business.owner = request.user

            # --- MANDATORY: Save the business to generate an ID ---
            business.save()

            # Handle Operating Hours
            OperatingHours.objects.filter(business=business).delete()
            day_configs = [
                ('mon_fri', form.cleaned_data.get('mon_fri_open'), form.cleaned_data.get('mon_fri_close')),
                ('sat', form.cleaned_data.get('sat_open'), form.cleaned_data.get('sat_close')),
                ('sun', form.cleaned_data.get('sun_open'), form.cleaned_data.get('sun_close')),
            ]
            for day_type, open_t, close_t in day_configs:
                if open_t and close_t:
                    OperatingHours.objects.create(
                        business=business, day_type=day_type,
                        open_time=open_t, close_time=close_t
                    )

            # Save Services
            services = service_formset.save(commit=False)
            for service in services:
                service.business = business
                service.save()

            for obj in service_formset.deleted_objects:
                obj.delete()

            # --- REDIRECT LOGIC ---
            if is_new_business:
                # Generate the URL now that the ID is valid
                pay_url = get_subscription_url(business, 149.00)

                # JavaScript Breakout to escape modals/iframes
                return HttpResponse(f"""
                    <html>
                        <head><title>Redirecting...</title></head>
                        <body style="text-align:center; padding-top:50px; font-family:sans-serif;">
                            <h2>Redirecting to Secure Payment...</h2>
                            <p>If not redirected, <a href="{pay_url}" target="_top">click here</a>.</p>
                            <script type="text/javascript">
                                window.top.location.href = "{pay_url}";
                            </script>
                        </body>
                    </html>
                """)

            messages.success(request, f"Changes saved for {business.name}!")
            return redirect('owner_dashboard', business_id=business.id)

    else:
        form = BusinessOnboardingForm(instance=business)
        service_formset = ServiceFormSet(instance=business)

    return render(request, 'bookingApp/onboarding.html', {
        'form': form,
        'service_formset': service_formset,
        'is_editing': bool(business)
    })


import hashlib
import urllib.parse
import hashlib
import urllib.parse
from django.utils import timezone
from django.conf import settings

def get_subscription_url(business, amount):
    """
    Generates a ONCE-OFF PayFast URL.
    Includes timestamp in m_payment_id to prevent 'Duplicate Transaction' errors.
    """
    m_id = '33083387'
    m_key = 'su9wfcs6tngdj'
    passphrase = 'VanWyknBake420'

    # 1. Build parameters
    # Note: We use a timestamp here so every payment attempt is unique (required by PayFast)
    params = [
        ('merchant_id', m_id),
        ('merchant_key', m_key),
        ('return_url', 'https://www.getmebooked.co.za/help/'),
        ('cancel_url', 'https://www.getmebooked.co.za/business/onboarding/'),
        ('notify_url', 'https://www.getmebooked.co.za/payfast/itn/'),
        ('name_first', str(business.owner.first_name or "Partner")),
        ('email_address', str(business.owner.email or "")),
        # ADDED TIMESTAMP HERE:
        ('m_payment_id', f"SUB-{business.id}-{int(timezone.now().timestamp())}"),
        ('amount', f"{amount:.2f}"),
        ('item_name', f"30 Day Platform Activation: {business.name}"),
        ('custom_int1', str(business.id)),
    ]

    # 2. Generate Signature String & Filter Empty Values
    # PayFast signatures must skip empty values, so we filter them out first.
    clean_params = [(k, v) for k, v in params if v.strip()]

    pf_common = ""
    for key, value in clean_params:
        pf_common += f"{key}={urllib.parse.quote_plus(str(value).strip())}&"

    pf_string = pf_common.rstrip('&')
    if passphrase:
        pf_string += f"&passphrase={urllib.parse.quote_plus(passphrase.strip())}"

    signature = hashlib.md5(pf_string.encode()).hexdigest()

    # 3. Final URL Construction
    # We convert clean_params to dict to ensure we don't send empty keys that weren't signed
    final_params = dict(clean_params)
    final_params['signature'] = signature

    return f"https://www.payfast.co.za/eng/process?{urllib.parse.urlencode(final_params)}"



logger = logging.getLogger(__name__)

@csrf_exempt
def payfast_itn(request):
    """
    Unified ITN listener with Referral Bonus logic.
    """
    if request.method == 'POST':
        data = request.POST.dict()
        payment_status = data.get('payment_status')
        m_payment_id = data.get('m_payment_id', '')

        if payment_status == 'COMPLETE':
            try:
                # --- ROUTE 1: Business Subscription ---
                if m_payment_id.startswith('SUB-'):
                    business_id = int(data.get('custom_int1'))
                    business = Business.objects.get(id=business_id)
                    now = timezone.now()

                    # Determine if this is the FIRST time they are paying
                    is_first_payment = business.subscription_end_date is None

                    # Base days for any payment is 30
                    days_to_add = 30

                    if is_first_payment:
                        # First-time signup bonus: Add an extra 30 days (60 total) - back to 30 for now
                        days_to_add = 30
                        logger.info(f"FIRST SIGNUP: Granting 60 days to Business {business_id}")
                    elif business.referred_by:
                        # Optional: Keep your existing referral bonus logic for renewals
                        # if that was your intention, otherwise this can be removed.
                        # days_to_add = 30
                        pass

                    # Calculate new end date
                    if business.subscription_end_date and business.subscription_end_date > now:
                        business.subscription_end_date += timedelta(days=days_to_add)
                    else:
                        # If subscription expired or is brand new, start from now
                        business.subscription_end_date = now + timedelta(days=days_to_add)

                    business.save()
                    logger.info(f"SUCCESS: Subscription extended by {days_to_add} days for Business {business_id}")

                # --- ROUTE 2: Appointment Deposit ---
                elif m_payment_id.startswith('APP-'):
                    appointment_id = data.get('custom_int1') or m_payment_id.split('-')[1]
                    appointment = Appointment.objects.select_related('booking_form__business').get(id=appointment_id)

                    expiry_limit = timezone.now() - timedelta(minutes=2)

                    if appointment.status == 'pending' and appointment.created_at < expiry_limit:
                        overlap = Appointment.objects.filter(
                            booking_form__business=appointment.booking_form.business,
                            appointment_date=appointment.appointment_date,
                            appointment_start_time=appointment.appointment_start_time,
                            status='confirmed'
                        ).exists()

                        if overlap:
                            appointment.status = 'cancelled'
                            appointment.save()
                            logger.warning(f"CONFLICT: Appt {appointment_id} paid late. Marked Cancelled.")
                            return HttpResponse(status=200)

                    appointment.status = 'confirmed'
                    appointment.deposit_paid = True
                    appointment.save()
                    logger.info(f"SUCCESS: Deposit paid for Appointment {appointment_id}")

                return HttpResponse(status=200)

            except Exception as e:
                logger.error(f"ITN Error: {str(e)} | Data: {data}")
                return HttpResponse(status=400)

        return HttpResponse(status=200)

    return HttpResponse(status=400)





@login_required
def owner_dashboard(request, business_id):
    business = get_object_or_404(Business, id=business_id)

    # --- 1. CLEANUP TRIGGER ---
    # Automatically cancels 'pending' appointments that didn't pay deposit within 2 hours
    cleanup_expired_appointments(business)

    # --- 2. PERMISSION CHECK ---
    is_owner = business.owner == request.user
    is_admin_staff = Staff.objects.filter(user=request.user, business=business, role='ADMIN').exists()

    if not (is_owner or is_admin_staff):
        messages.error(request, "Access Denied.")
        return redirect('home')

    # --- 3. SUBSCRIPTION GUARD ---
    SUBSCRIPTION_PRICE = 149.00
    if not business.subscription_end_date or business.subscription_end_date < timezone.now():
        return render(request, 'bookingApp/dashboard_locked.html', {
            'business': business,
            'pay_url': generate_payfast_url(business, SUBSCRIPTION_PRICE)
        })

    # --- 4. HANDLE POST UPDATES ---
    if request.method == "POST":
        action = request.POST.get('action')

        # Profile Update (including Name, Contact, Address, Cover Image, and Socials)
        if action == "update_profile":
            business.name = request.POST.get('name')
            business.contact_number = request.POST.get('phone_number')
            business.address = request.POST.get('address')
            business.description = request.POST.get('description')

            # Social Links
            business.instagram_url = request.POST.get('instagram_url')
            business.facebook_url = request.POST.get('facebook_url')
            business.twitter_url = request.POST.get('twitter_url')

            if 'cover_image' in request.FILES:
                business.cover_image = request.FILES['cover_image']

            business.save()
            messages.success(request, "Business profile and social links updated successfully.")

        # Inside owner_dashboard(request, business_id):


        # Payment Credentials & Deposit Policy
        elif action == "update_payfast":
            business.payfast_merchant_id = request.POST.get('payfast_merchant_id')
            business.payfast_merchant_key = request.POST.get('payfast_merchant_key')

            # NEW: Handle Types and Window
            business.deposit_type = request.POST.get('deposit_type', 'fixed')

            # Handle Percent
            dep_percent = request.POST.get('deposit_percentage')
            business.deposit_percentage = int(dep_percent) if dep_percent else 0

            # Handle Fixed Amount
            deposit_amt = request.POST.get('deposit_amount')
            business.deposit_amount = float(deposit_amt) if deposit_amt else 0.00

            # Handle Reschedule Window
            res_window = request.POST.get('reschedule_window_hours')
            business.reschedule_window_hours = int(res_window) if res_window else 24

            business.deposit_policy = request.POST.get('deposit_policy')

            business.save()
            messages.success(request, "Deposit settings and payment credentials updated.")

        # Operating Hours Update
        elif action == "update_hours":
            days_to_process = [('mon_fri', 'mon_fri'), ('sat', 'sat'), ('sun', 'sun')]
            for field_name, day_type in days_to_process:
                open_t = request.POST.get(f'open_{field_name}')
                close_t = request.POST.get(f'close_{field_name}')

                if open_t and close_t:
                    OperatingHours.objects.update_or_create(
                        business=business,
                        day_type=day_type,
                        defaults={'open_time': open_t, 'close_time': close_t}
                    )
            messages.success(request, "Operating hours updated.")

        # Blocked Days Logic
        elif action == "add_block":
            block_date = request.POST.get('block_date')
            if block_date:
                BusinessBlock.objects.get_or_create(business=business, block_date=block_date)
                messages.success(request, f"Date blocked: {block_date}")

        elif action == "delete_block":
            block_id = request.POST.get('block_id')
            BusinessBlock.objects.filter(id=block_id, business=business).delete()
            messages.success(request, "Blocked date removed.")

        return redirect('owner_dashboard', business_id=business.id)

    # --- 5. DATA FETCHING FOR UI ---
    today = timezone.now().date()

    # Get all booking forms for this business
    booking_forms = business.booking_forms.all()

    # Base query for appointments
    base_appointments = Appointment.objects.filter(
        booking_form__business=business
    ).select_related('service', 'customer').order_by('appointment_start_time')

    # Prepare Calendar JSON
    calendar_events = [{
        'title': appt.customer.get_full_name() if appt.customer else f"{appt.guest_name} (Guest)",
        'start': f"{appt.appointment_date.isoformat()}T{appt.appointment_start_time.strftime('%H:%M:%S')}",
        'backgroundColor': '#6366f1' if appt.status == 'confirmed' else ('#ef4444' if appt.status == 'cancelled' else '#f59e0b'),
    } for appt in base_appointments]

    context = {
        'business': business,
        'booking_forms': booking_forms,
        'days_left': business.days_remaining,
        'pay_url': get_subscription_url(business, SUBSCRIPTION_PRICE),

        # Appointment Lists
        'today_appointments': base_appointments.filter(
            appointment_date=today
        ).exclude(status__in=['cancelled', 'declined','completed']).order_by('appointment_start_time'),

        'upcoming_appointments': base_appointments.filter(
            appointment_date__gte=today
        ).exclude(status__in=['completed', 'cancelled', 'declined']).order_by('appointment_date', 'appointment_start_time'),

        'past_appointments': base_appointments.filter(
            Q(appointment_date__lt=today) | Q(status__in=['completed', 'cancelled', 'declined'])
        ).order_by('-appointment_date', '-appointment_start_time'),

        # Configuration Data
        'operating_hours': {oh.day_type: oh for oh in business.operating_hours.all()},
        'business_blocks': business.blocks.filter(block_date__gte=today),
        'services': business.services.all(),
        'staff_members': business.staff_members.all().select_related('user__profile'),

        # UI Helpers
        'calendar_events': calendar_events,
        'is_admin': (is_owner or is_admin_staff),
        'deposit_required': business.deposit_required,
    }

    return render(request, 'bookingApp/owner_dashboard.html', context)



def book_appointment_public(request, token):
    # Fetch the form by its unique token
    booking_form = get_object_or_404(BookingForm, embed_token=token)
    trigger_pending_reminders()

    # Reuse your existing book_appointment logic or call it
    return book_appointment(request, booking_form.id)

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
def service_edit(request, business_id, service_id):
    # Ensure the user owns the business associated with this service
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    service = get_object_or_404(Service, id=service_id, business=business)

    if request.method == 'POST':
        # Pass the instance to the form so it updates instead of creates
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            return redirect('owner_dashboard', business_id=business.id)
    else:
        # Pre-fill the form with service data
        form = ServiceForm(instance=service)

    # We use the same template as service_create
    return render(request, 'bookingApp/service_form.html', {
        'form': form,
        'business': business,
        'edit_mode': True  # Added to toggle UI text
    })

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



import logging
from datetime import date, datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.clickjacking import xframe_options_exempt

from .models import (
    BookingForm, Service, Staff, Appointment, ClientProfile
)
from .forms import AppointmentForm
from .utils import get_available_times, calculate_deposit_amount, generate_appointment_payfast_url
from .utils import send_deposit_request_email

logger = logging.getLogger(__name__)

@xframe_options_exempt
@ensure_csrf_cookie
def book_appointment(request, booking_form_id):
    """
    Handles the complete booking logic for public users.
    Includes dynamic staff filtering, availability calculation,
    and PayFast redirection for deposits (with Client-specific exemptions).
    """
    booking_form = get_object_or_404(BookingForm, id=booking_form_id)
    business = booking_form.business
    services = Service.objects.filter(business=business)
    staff_members = Staff.objects.filter(business=business)
    is_embedded = request.GET.get('embed') == 'true'

    if request.method == 'POST':
        selected_date_str = request.POST.get('appointment_date')
        selected_service_id = request.POST.get('service')
        selected_staff_id = request.POST.get('staff')

        # 1. Fetch Service & Filter Staff strictly by service qualification
        selected_service = services.filter(id=selected_service_id).first() if selected_service_id else None

        # We MUST filter staff here so the form validation (ChoiceField) passes
        if selected_service:
            staff_members = staff_members.filter(services=selected_service)
        else:
            staff_members = staff_members.none()

        selected_date = None
        available_times = []

        # 2. Re-calculate availability for validation context
        if selected_date_str and selected_service:
            try:
                selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
                available_times = get_available_times(
                    business,
                    selected_date,
                    selected_service.default_length_minutes,
                    staff_id=selected_staff_id if selected_staff_id and selected_staff_id != 'None' else None
                )
            except (ValueError, AttributeError):
                pass

        # 3. Initialize Form with filtered querysets
        form = AppointmentForm(
            request.POST,
            services=services,
            staff=staff_members,
            available_times=available_times
        )

        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.booking_form = booking_form
            appointment.service = selected_service

            # Extract email to check for deposit exemption
            email = form.cleaned_data.get('guest_email')
            service_price = selected_service.price if selected_service else 0

            # --- DEPOSIT EXEMPTION LOGIC ---
            # Check if this specific client is marked as exempt for this business
            is_exempt = ClientProfile.objects.filter(
                business=business,
                email=email,
                deposit_exempt=True
            ).exists()

            if is_exempt:
                # Client is trusted: bypass payment logic
                appointment.amount_to_pay = 0.00
                appointment.deposit_paid = True
                appointment.status = 'confirmed'
                requires_payment = False
            else:
                # Standard business rules
                deposit_req = calculate_deposit_amount(business, service_price)
                appointment.amount_to_pay = deposit_req
                appointment.status = 'pending'
                # Payment is required only if business settings require it and amount > 0
                requires_payment = business.deposit_required and deposit_req > 0
            # --- END EXEMPTION LOGIC ---

            # Capture Guest details from form
            appointment.guest_name = form.cleaned_data.get('guest_name')
            appointment.guest_email = email
            appointment.guest_phone = form.cleaned_data.get('guest_phone') or ""

            # Handle Authenticated User Linkage
            if request.user.is_authenticated:
                appointment.customer = request.user
                appointment.guest_name = appointment.guest_name or request.user.get_full_name()
                appointment.guest_email = appointment.guest_email or request.user.email
                if not appointment.guest_phone and hasattr(request.user, 'profile'):
                    appointment.guest_phone = request.user.profile.phone_number
            else:
                appointment.customer = None

            # Assign Staff
            if selected_staff_id and selected_staff_id != 'None':
                appointment.staff_id = selected_staff_id

            appointment.save()

            # 4. Handle Redirection / Success
            if requires_payment:
                try:
                    pay_url = generate_appointment_payfast_url(request, appointment)

                    # Send backup email with payment link
                    send_deposit_request_email(appointment, pay_url)

                    # Return JavaScript Breakout for iFrames/Embedded forms
                    return HttpResponse(f"""
                        <html>
                            <head><title>Redirecting...</title></head>
                            <body style="text-align:center; padding-top:50px; font-family:sans-serif;">
                                <h2>Redirecting to Secure Payment...</h2>
                                <p>If not redirected, <a href="{pay_url}" target="_top">click here</a>.</p>
                                <script type="text/javascript">
                                    // The 'top' ensures we break out of any potential iframes or modals
                                    window.top.location.href = "{pay_url}";
                                </script>
                            </body>
                        </html>
                    """)
                except Exception as e:
                    logger.error(f"Payment Redirect Error: {e}")
                    messages.warning(request, "Payment redirect failed, but a link has been emailed to you.")
                    return render(request, 'bookingApp/booking_success_guest.html', {'appointment': appointment})

            else:
                # Case: Deposit Exempt OR Business doesn't require deposit
                messages.success(request, "Appointment requested successfully!")
                return render(request, 'bookingApp/booking_success_guest.html', {'appointment': appointment})

    else:
        # GET REQUEST - Initial Page Load
        selected_date = date.today()
        selected_service = services.first()

        # Initial staff filter for the default selected service
        if selected_service:
            staff_members = staff_members.filter(services=selected_service)

        duration = selected_service.default_length_minutes if selected_service else 30
        available_times = get_available_times(business, selected_date, duration)

        # Pre-fill data for logged-in users
        initial_data = {}
        if request.user.is_authenticated:
            initial_data['guest_name'] = request.user.get_full_name() or request.user.username
            initial_data['guest_email'] = request.user.email
            if hasattr(request.user, 'profile'):
                initial_data['guest_phone'] = request.user.profile.phone_number

        form = AppointmentForm(
            services=services,
            staff=staff_members,
            available_times=available_times,
            initial=initial_data
        )

    return render(request, 'bookingApp/book_appointment.html', {
        'form': form,
        'is_embedded': is_embedded,
        'business': business,
        'booking_form': booking_form,
        'available_times': available_times,
    })


def booking_success(request, appointment_id):
    """
    This is the RETURN URL for PayFast.
    The user lands here after clicking 'Return to Merchant' or auto-redirect from PayFast.
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)
    business = appointment.booking_form.business

    # Optional: Run your cleanup logic if needed
    # cleanup_expired_appointments(business)

    # Refresh DB status (in case ITN processed faster than the redirect)
    appointment.refresh_from_db()

    # Determine message based on payment status
    if appointment.deposit_paid or appointment.status == 'confirmed':
        messages.success(request, "Payment successful! Your appointment is confirmed.")
    else:
        # User returned, but ITN might not have fired yet, or they clicked return without paying.
        messages.info(request, "Thank you for your booking. If you completed payment, your appointment will be confirmed shortly. Please check your email.")

    return render(request, 'bookingApp/booking_success_guest.html', {
        'appointment': appointment
    })



@staff_member_required
def test_payment_flow(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    business_id = appointment.booking_form.business.id

    try:
        # 1. Simulate ITN logic
        appointment.deposit_paid = True
        appointment.payfast_reference = "TEST_DEBUG_123"
        appointment.status = 'confirmed'

        # 2. Save triggers the 'confirmed' customer signal
        appointment.save()

        # 3. Trigger the Owner notification manually
        send_owner_paid_notification(appointment)

        messages.success(request, f"Success! Emails sent for {appointment.guest_name}.")
    except Exception as e:
        messages.error(request, f"Error sending test emails: {e}")

    return redirect('owner_dashboard', business_id=business_id)

from django.core.mail import send_mail
from django.conf import settings

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import Staff, StaffOperatingHours, StaffBlock, Appointment
from .forms import StaffServicesForm  # Assuming this is your form name

@login_required
def staff_dashboard(request):
    # 1. Profile & Identity Check
    staff_profile = getattr(request.user, 'staff_profile', None)
    if not staff_profile:
        messages.error(request, "Staff profile not found.")
        return redirect('home')

    # 2. Subscription Lock Logic
    business = staff_profile.business
    if not business.subscription_end_date or business.subscription_end_date < timezone.now():
        return render(request, 'bookingApp/dashboard_locked.html', {
            'business': business,
            'is_staff': True,
        })

    today = timezone.now().date()

    # 3. POST Logic (Signals handle notifications automatically)
    if request.method == "POST":

        # Update Services
        if 'update_services' in request.POST:
            service_form = StaffServicesForm(request.POST, instance=staff_profile, business=business)
            if service_form.is_valid():
                service_form.save() # Triggers m2m_changed signal
                messages.success(request, "Your services have been updated.")
            return redirect('staff_dashboard')

        # Update Operating Hours
        elif 'update_hours' in request.POST:
            for day in ['mon_fri', 'sat', 'sun']:
                open_t = request.POST.get(f'{day}_open')
                close_t = request.POST.get(f'{day}_close')
                if open_t and close_t:
                    StaffOperatingHours.objects.update_or_create(
                        staff=staff_profile,
                        day_type=day,
                        defaults={'open_time': open_t, 'close_time': close_t}
                    ) # Triggers post_save signal
            messages.success(request, "Hours updated.")

        # Add Time Block
        elif 'add_block' in request.POST:
            StaffBlock.objects.create(
                staff=staff_profile,
                block_date=request.POST.get('block_date'),
                start_time=request.POST.get('start_time'),
                end_time=request.POST.get('end_time'),
                reason=request.POST.get('reason', 'Personal')
            ) # Triggers post_save signal
            messages.success(request, "Time blocked.")

        # Delete Time Block
        elif 'delete_block' in request.POST:
            StaffBlock.objects.filter(id=request.POST.get('block_id'), staff=staff_profile).delete()
            messages.info(request, "Block removed.")

        # Mark Appointment as Completed
        elif 'complete_appointment' in request.POST:
            appt_id = request.POST.get('appointment_id')
            Appointment.objects.filter(
                id=appt_id,
                staff=staff_profile,
                status='confirmed'
            ).update(status='completed')
            messages.success(request, "Appointment marked as completed.")

        return redirect('staff_dashboard')

    # 4. Display Logic (GET request)
    base_query = Appointment.objects.filter(staff=staff_profile).select_related('service', 'customer')

    todays_appointments = base_query.filter(
        appointment_date=today
    ).exclude(
        status__in=['cancelled', 'declined', 'completed']
    ).order_by('appointment_start_time')

    upcoming = base_query.filter(
        appointment_date__gt=today
    ).exclude(
        status__in=['completed', 'cancelled', 'declined', 'rescheduled']
    ).order_by('appointment_date', 'appointment_start_time')

    past = base_query.filter(
        Q(appointment_date__lt=today) |
        Q(status__in=['completed', 'cancelled', 'declined', 'rescheduled'])
    ).order_by('-appointment_date', '-appointment_start_time')

    context = {
        'staff': staff_profile,
        'business': business,
        'todays_appointments': todays_appointments,
        'upcoming': upcoming,
        'past': past,
        'service_form': StaffServicesForm(instance=staff_profile, business=business),
        'blocks': StaffBlock.objects.filter(staff=staff_profile, block_date__gte=today),
        'hours': {oh.day_type: oh for oh in staff_profile.work_hours.all()},
        'day_choices': [('mon_fri', 'Mon-Fri'), ('sat', 'Saturday'), ('sun', 'Sunday')]
    }
    return render(request, 'bookingApp/staff_dashboard.html', context)

# In views.py





def get_staff_for_service(request):
    service_id = request.GET.get('service_id')
    if not service_id:
        return JsonResponse({'staff_list': []})

    # Get staff who provide this specific service
    staff_members = Staff.objects.filter(services__id=service_id)

    staff_data = [
        {'id': s.id, 'name': s.name} for s in staff_members
    ]

    return JsonResponse({'staff_list': staff_data})




def get_available_slots_ajax(request):
    # 1. Extract parameters from the AJAX GET request
    b_id = request.GET.get('business_id')
    s_id = request.GET.get('service_id')
    d_str = request.GET.get('date')
    staff_id = request.GET.get('staff_id')

    # Basic safety check
    if not all([b_id, s_id, d_str]):
        return JsonResponse({'slots': [], 'error': 'Missing required parameters'}, status=400)

    try:
        # 2. Fetch data
        business = get_object_or_404(Business, id=b_id)
        service = get_object_or_404(Service, id=s_id)
        date_obj = datetime.strptime(d_str, '%Y-%m-%d').date()

        # 3. Get Slots
        slots = get_available_times(
            business=business,
            appointment_date=date_obj,
            service_length=service.default_length_minutes,
            staff_id=staff_id
        )

        # 4. Format for JSON
        formatted_slots = [
            {'value': t.strftime('%H:%M'), 'label': t.strftime('%I:%M %p')}
            for t in slots
        ]

        return JsonResponse({'slots': formatted_slots})

    except Exception as e:
        # If this crashes, look at the browser console to see the 'error' text
        return JsonResponse({'error': str(e)}, status=400)



@login_required
def my_appointments(request):
    status_filter = request.GET.get('filter', 'all')
    now = timezone.now()

    base_appointments = request.user.appointments.all()

    if status_filter == 'upcoming':
        # Future appointments that are NOT cancelled or completed
        appointments = base_appointments.filter(
            Q(appointment_date__gt=now.date()) |
            Q(
                appointment_date=now.date(),
                appointment_start_time__gte=now.time()
            ),
            status__in=['pending', 'confirmed']
        ).order_by('appointment_date', 'appointment_start_time')

    elif status_filter == 'past':
        # ONLY cancelled or completed
        appointments = base_appointments.filter(
            status__in=['cancelled', 'completed', 'declined']
        ).order_by('-appointment_date', '-appointment_start_time')

    else:
        appointments = base_appointments.order_by(
            '-appointment_date',
            '-appointment_start_time'
        )

    context = {
        'appointments': appointments,
        'current_filter': status_filter,
        'total_count': base_appointments.count(),
    }

    return render(request, 'bookingApp/my_appointments.html', context)



def register(request):
    next_url = request.GET.get('next') or request.POST.get('next')

    # 🔒 SAFETY CHECK
    if not next_url or next_url == "None":
        next_url = None

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            if next_url:
                return redirect(next_url)
            return redirect('home')
    else:
        form = CustomUserCreationForm()

    return render(request, 'bookingApp/register.html', {
        'form': form,
        'next': next_url
    })




# views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.http import urlencode  # Required for encoding the WhatsApp message
from .models import Appointment, Staff
from .forms import RescheduleAppointmentForm
from .utils import generate_appointment_payfast_url

@login_required
def appointment_detail(request, pk):
    # 1. Fetch the appointment and related business
    appointment = get_object_or_404(Appointment, pk=pk)
    business = appointment.booking_form.business

    # 2. Permission Logic
    # Check if the user is the business owner or an admin staff member
    is_admin_staff = Staff.objects.filter(user=request.user, business=business, role='ADMIN').exists()
    is_owner = (business.owner == request.user or is_admin_staff)

    # Check if the user is the customer who booked it
    is_customer = (appointment.customer == request.user or appointment.guest_email == request.user.email)

    # 3. Handle Status Updates & Rescheduling (Existing POST Logic)
    if request.method == 'POST':
        action = request.POST.get('action')

        # Simple status update (Confirm/Cancel/Complete)
        if action == 'update_status' and is_owner:
            new_status = request.POST.get('status')
            if new_status in dict(Appointment.STATUS_CHOICES):
                appointment.status = new_status
                appointment.save()
                return JsonResponse({'status': 'success'})

        # Reschedule submission
        elif action == 'reschedule_submit' and is_customer:
            form = RescheduleAppointmentForm(request.POST, instance=appointment)
            if form.is_valid():
                # We set it to 'reschedule_requested' so the owner sees the change
                appt = form.save(commit=False)
                appt.status = 'reschedule_requested'
                appt.save()
                return JsonResponse({'status': 'success'})
            return JsonResponse({'status': 'error', 'errors': form.errors})

    # 4. Generate Link Sending Data (The New Part)
    pay_url = None
    payment_whatsapp_url = None

    # We only show these links if:
    # - Business requires a deposit
    # - Deposit hasn't been paid yet
    # - The appointment isn't already cancelled or declined
    if business.deposit_required and not appointment.deposit_paid and appointment.status not in ['cancelled', 'declined']:

        # Generate the secure PayFast URL using the helper from utils.py
        pay_url = generate_appointment_payfast_url(request, appointment)

        # Generate the WhatsApp Click-to-Chat URL
        # Uses the formatted_whatsapp_number property from your Appointment model
        if appointment.formatted_whatsapp_number:
            message_text = (
                f"Hi {appointment.guest_name}, this is {business.name}. "
                f"To confirm your booking for {appointment.service.name}, "
                f"please complete the deposit of R{business.deposit_amount} here: {pay_url}"
            )
            # URL encode the message so it works in a browser link
            params = {'text': message_text}
            payment_whatsapp_url = f"https://wa.me/{appointment.formatted_whatsapp_number}?{urlencode(params)}"

    # 5. Render
    context = {
        'appointment': appointment,
        'is_owner': is_owner,
        'is_customer': is_customer,
        'reschedule_form': RescheduleAppointmentForm(instance=appointment),
        'pay_url': pay_url, # New
        'payment_whatsapp_url': payment_whatsapp_url, # New
    }

    return render(request, 'bookingApp/appointment_detail.html', context)


from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.core.mail import send_mail

# Ensure these are imported from where they are defined in your project
from .models import Appointment
from .forms import RescheduleAppointmentForm
from .utils import (
    get_available_times,
    generate_appointment_payfast_url,
    send_deposit_request_email
)

def appointment_reschedule(request, token):
    appointment = get_object_or_404(Appointment, reschedule_token=token)
    business = appointment.booking_form.business

    # 1. Check the 24h window (using local timezone)
    appointment_datetime = timezone.make_aware(
        datetime.combine(appointment.appointment_date, appointment.appointment_start_time)
    )
    is_too_late = appointment_datetime < (timezone.now() + timedelta(hours=24))

    hours_window = business.reschedule_window_hours
    limit_time = timezone.now() + timedelta(hours=hours_window)

    is_too_late = appointment_datetime < limit_time

    if request.method == 'POST':
        form = RescheduleAppointmentForm(request.POST, instance=appointment)
        late_confirmation_given = request.POST.get('confirm_deposit_loss') == 'on'

        if is_too_late and not late_confirmation_given:
            form.add_error(None, "You must confirm that you understand the deposit will be lost.")

        # --- inside appointment_reschedule view ---
        elif form.is_valid():
            new_date = form.cleaned_data.get('appointment_date')
            new_time = form.cleaned_data.get('appointment_start_time')
            # If new_time is a time object, convert to string "HH:MM"
            if hasattr(new_time, 'strftime'):
                new_time_str = new_time.strftime('%H:%M')
            else:
                new_time_str = new_time

            selected_staff = appointment.staff # Usually reschedule stays with same staff

            available_slots = get_available_times(
                business=business,
                appointment_date=new_date,
                service_length=appointment.service.default_length_minutes,
                staff_id=selected_staff.id if selected_staff else None,
                service_obj=appointment.service
            )

            # Convert all available slots to strings for reliable comparison
            available_slots_str = [
                s.strftime('%H:%M') if hasattr(s, 'strftime') else s
                for s in available_slots
            ]

            if new_time_str not in available_slots_str:
                form.add_error('appointment_start_time', "The selected staff member is not available at this time.")

            else:
                # ====================================================
                # LOGIC BRANCH: LATE RESCHEDULE (FORFEIT DEPOSIT)
                # ====================================================
                if is_too_late:
                    # 1. Create a FRESH Appointment (New ID, New Deposit Required)
                    new_appt = Appointment(
                        booking_form=appointment.booking_form,
                        service=appointment.service,
                        customer=appointment.customer,
                        guest_name=appointment.guest_name,
                        guest_email=appointment.guest_email,
                        guest_phone=appointment.guest_phone,
                        appointment_date=new_date,
                        appointment_start_time=new_time,
                        staff=selected_staff,
                        status='pending',       # Reset to pending
                        deposit_paid=False,     # Reset deposit status
                        notes=f"Rescheduled from Appt #{appointment.id}. Previous deposit forfeited."
                    )
                    new_appt.save()

                    # 2. Cancel the OLD Appointment
                    appointment.status = 'cancelled'
                    appointment.notes = (appointment.notes or "") + "\n[SYSTEM]: Late reschedule. Deposit forfeited. Re-booked as new appointment."
                    appointment.save()

                    # 3. Trigger Payment Flow (Same as book_appointment)
                    if business.deposit_required:
                        try:
                            # Generate PayFast URL for the NEW appointment
                            pay_url = generate_appointment_payfast_url(request, new_appt)

                            # Send Backup Email
                            send_deposit_request_email(new_appt, pay_url)

                            # Javascript Breakout to Payment Gateway
                            return HttpResponse(f"""
                                <html>
                                    <body>
                                        <p>Reschedule accepted. Redirecting to secure payment for new deposit...</p>
                                        <script type="text/javascript">
                                            window.top.location.href = "{pay_url}";
                                        </script>
                                    </body>
                                </html>
                            """)
                        except Exception as e:
                            print(f"Reschedule Payment Redirect Error: {e}")
                            # Fallback if redirect fails
                            return render(request, 'bookingApp/booking_success_guest.html', {'appointment': new_appt})

                    # If no deposit required, just render success for the new appt
                    return render(request, 'bookingApp/reschedule_success.html', {
                        'appointment': new_appt,
                        'is_too_late': True
                    })

                # ====================================================
                # LOGIC BRANCH: EARLY RESCHEDULE (STANDARD)
                # ====================================================
                else:
                    # Update the EXISTING appointment
                    appt = form.save(commit=False)
                    appt.status = 'pending' # Set to pending for owner review
                    appt.save()

                    # --- NOTIFICATIONS (Standard Flow) ---
                    client_name = appt.customer.get_full_name() if appt.customer else appt.guest_name
                    customer_email = appt.guest_email or (appt.customer.email if appt.customer else None)

                    # Notify Staff/Owner
                    staff_recipient = appt.staff.user.email if (appt.staff and hasattr(appt.staff, 'user')) else business.owner.email

                    if staff_recipient:
                        staff_context = {
                            'appointment': appt,
                            'client_name': client_name,
                            'is_too_late': False,
                            'business': business,
                            'site_url': settings.SITE_URL
                        }
                        html_staff = render_to_string('bookingApp/owner_reschedule_notification.html', staff_context)
                        send_mail(
                            subject=f"Reschedule Request - {client_name}",
                            message=strip_tags(html_staff),
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[staff_recipient],
                            html_message=html_staff,
                            fail_silently=True,
                        )

                    # Notify Customer
                    if customer_email:
                        cust_context = {
                            'appointment': appt,
                            'business': business,
                            'client_name': client_name,
                            'is_too_late': False,
                            'site_url': settings.SITE_URL
                        }
                        html_cust = render_to_string('bookingApp/customer_status_update.html', cust_context)
                        send_mail(
                            subject=f"Reschedule Confirmed: {business.name}",
                            message=f"Hi {client_name}, we received your request to reschedule.",
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[customer_email],
                            html_message=html_cust,
                            fail_silently=True,
                        )

                    return render(request, 'bookingApp/reschedule_success.html', {'is_too_late': False})

    else:
        form = RescheduleAppointmentForm(instance=appointment)

    return render(request, 'bookingApp/appointment_reschedule.html', {
        'form': form,
        'appointment': appointment,
        'is_too_late': is_too_late
    })

@login_required
def appointment_cancel(request, pk):
    # Ensure only the customer who owns it can cancel
    appointment = get_object_or_404(Appointment, pk=pk, customer=request.user)

    if request.method == 'POST':
        appointment.status = 'cancelled'
        appointment.save() # This triggers the post_save signal
        return redirect('my_appointments')

    return render(request, 'bookingApp/appointment_confirm_cancel.html', {
        'appointment': appointment
    })

# Add this to your views.py
from django.shortcuts import get_object_or_404, redirect

def business_landing(request, business_slug):
    business = get_object_or_404(Business, slug=business_slug)
    booking_form = get_object_or_404(BookingForm, business=business)
    services = Service.objects.filter(business=business, is_active=True)

    return render(request, 'bookingApp/landing.html', {
        'business': business,
        'booking_form': booking_form,
        'services': services,
    })




def terms_of_service(request):
    return render(request, 'bookingApp/terms.html')

def privacy_policy(request):
    return render(request, 'bookingApp/privacy.html')

@login_required
def get_notification_counts(request):
    data = {
        'pending_business_count': 0,
        'pending_staff_count': 0
    }

    # Business Owner logic (for 'All Bookings' badge)
    if hasattr(request.user, 'business'):
        data['pending_business_count'] = Appointment.objects.filter(
            booking_form__business=request.user.business,
            status='pending'
        ).count()

    # Staff logic (for 'Schedule' badge)
    staff_profile = getattr(request.user, 'staff_profile', None)
    if staff_profile:
        data['pending_staff_count'] = Appointment.objects.filter(
            staff=staff_profile,
            status='pending'
        ).count()

    return JsonResponse(data)



def contact_view(request):
    if request.method == "POST":
        # 1. Grab data from the form
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject_selection = request.POST.get('subject') # Starter, Pro, or Support
        message = request.POST.get('message')

        # 2. Prepare the context for the email template
        context = {
            'name': name,
            'email': email,
            'subject': subject_selection,
            'message': message,
        }

        # 3. Render the HTML content
        html_content = render_to_string('bookingApp/contact_inquiry.html', context)

        # 4. Create and send the Email
        email_to_send = EmailMessage(
            subject=f"New Contact Inquiry: {subject_selection}",
            body=html_content,
            from_email="getmebookedinfo@gmail.com",
            to=["getmebookedinfo@gmail.com"], # Your email address
            reply_to=[email], # Allows you to hit 'Reply' and talk to the user directly
        )
        email_to_send.content_subtype = "html"  # CRITICAL: This tells Django it's HTML, not plain text

        try:
            email_to_send.send()
            messages.success(request, "Your message has been sent successfully!")
        except Exception as e:
            messages.error(request, "There was an error sending your message.")

        return redirect('home') # Redirect back to the landing page

    return render(request, 'bookingApp/landing.html')

# views.py
# views.py

@login_required
def join_staff(request):
    if request.method == 'POST':
        code = request.POST.get('company_code', '').strip().upper()
        business = Business.objects.filter(join_code=code).first()

        if not business:
            messages.error(request, "Invalid join code.")
            return redirect('join_staff')

        # Check if user already has a staff profile
        if hasattr(request.user, 'staff_profile'):
            messages.warning(request, "You are already linked to a business.")
            return redirect('owner_dashboard', business_id=request.user.staff_profile.business.id)

        # Create the staff profile with ADMIN privileges
        Staff.objects.create(
            business=business,
            user=request.user,
            name=request.user.get_full_name() or request.user.username,
            email=request.user.email,
            role='ADMIN' # Granting high-level access
        )

        # Optional: If you use the Profile model to gate access, update it here
        if hasattr(request.user, 'profile'):
            request.user.profile.is_business_owner = True
            request.user.profile.save()

        messages.success(request, f"Full Admin access granted for {business.name}!")
        return redirect('owner_dashboard', business_id=business.id)

    return render(request, 'bookingApp/join_staff.html')



@login_required
def profile_view(request):
    user = request.user
    # Ensure profile exists (defense-in-depth)
    profile, created = Profile.objects.get_or_create(user=user)

    if request.method == "POST":
        # Handle Account Deletion
        if "delete_account" in request.POST:
            user.delete()
            messages.success(request, "Account deleted.")
            return redirect('home')

        # Handle Profile Update
        if "update_profile" in request.POST:
            # Update User Model
            user.first_name = request.POST.get('first_name')
            user.last_name = request.POST.get('last_name')
            user.email = request.POST.get('email')
            user.save()

            # Update Profile Model
            profile.phone_number = request.POST.get('phone_number')
            profile.bio = request.POST.get('bio')
            profile.email_notifications = 'email_notifications' in request.POST
            profile.sms_notifications = 'sms_notifications' in request.POST

            if request.FILES.get('avatar'):
                profile.avatar = request.FILES.get('avatar')

            profile.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')

    return render(request, 'bookingApp/profile.html', {'user': user})
# views.py


# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.http import urlencode
from .models import Business, Staff, Appointment
from .forms import ManualBookingForm
from .utils import (
    trigger_pending_reminders,
    generate_appointment_payfast_url,
    send_deposit_request_email
)

@login_required
def manual_booking(request, business_id):
    business = get_object_or_404(Business, id=business_id)
    trigger_pending_reminders() #

    # Permission Check
    is_admin_staff = Staff.objects.filter(user=request.user, business=business, role='ADMIN').exists()
    if business.owner != request.user and not is_admin_staff:
        messages.error(request, "Unauthorized access.")
        return redirect('home')

    if request.method == 'POST':
        form = ManualBookingForm(request.POST, business=business)
        if form.is_valid():
            appointment = form.save(commit=False)
            target_form = business.booking_forms.first() #

            if not target_form:
                messages.error(request, "Please create a Booking Form first.")
                return redirect('owner_dashboard', business_id=business.id)

            appointment.booking_form = target_form

            # --- NEW LOGIC START ---
            if business.deposit_required:
                # 1. Save as Pending
                appointment.status = 'pending'
                appointment.save()

                # 2. Generate Payment Link
                pay_url = generate_appointment_payfast_url(request, appointment) #

                # 3. Auto-send Email if address provided
                email_sent = False
                if appointment.guest_email:
                    send_deposit_request_email(appointment, pay_url) #
                    email_sent = True

                # 4. Generate WhatsApp Link
                whatsapp_url = None
                if appointment.formatted_whatsapp_number: #
                    msg = f"Hi {appointment.guest_name}, please complete your deposit for {appointment.service.name} here: {pay_url}"
                    whatsapp_url = f"https://wa.me/{appointment.formatted_whatsapp_number}?{urlencode({'text': msg})}"

                # 5. Render Success/Action Screen
                return render(request, 'bookingApp/manual_booking_success.html', {
                    'appointment': appointment,
                    'pay_url': pay_url,
                    'whatsapp_url': whatsapp_url,
                    'email_sent': email_sent
                })

            else:
                # No Deposit Required - Standard Flow
                appointment.status = 'confirmed'
                appointment.save()
                messages.success(request, f"Booking for {appointment.guest_name} confirmed!")
                return redirect('owner_dashboard', business_id=business.id)
            # --- NEW LOGIC END ---

    else:
        form = ManualBookingForm(business=business)

    return render(request, 'bookingApp/manual_booking.html', {'form': form, 'business': business})
# views.py
def get_manual_availability(request, business_id):
    business = get_object_or_404(Business, id=business_id)
    staff_id = request.GET.get('staff_id')
    service_id = request.GET.get('service_id')
    date_str = request.GET.get('date')

    if not all([service_id, date_str]):
        return JsonResponse({'slots': []})

    try:
        appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        service = Service.objects.get(id=service_id)

        # Reuse your existing complex logic function
        slots = get_available_times(
            business=business,
            appointment_date=appointment_date,
            service_length=service.default_length_minutes,
            staff_id=staff_id
        )

        return JsonResponse({'slots': [s.strftime('%H:%M') for s in slots]})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def api_get_available_slots(request):
    """ Consolidated AJAX view for fetching available slots """
    date_str = request.GET.get('date')
    service_id = request.GET.get('service_id')
    staff_id = request.GET.get('staff_id')
    business_id = request.GET.get('business_id')

    # Basic validation
    if not all([date_str, service_id, business_id]):
        return JsonResponse({'slots': [], 'error': 'Missing parameters'}, status=400)

    try:
        business = get_object_or_404(Business, id=business_id)
        service = get_object_or_404(Service, id=service_id)

        # Convert string to date object
        appt_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Get available slots using your logic
        slots = get_available_times(
            business=business,
            appointment_date=appt_date,
            service_length=service.default_length_minutes,
            staff_id=staff_id if staff_id and staff_id != 'None' else None
        )

        # Return simple list of strings: ["09:00", "09:30", ...]
        return JsonResponse({'slots': [s.strftime('%H:%M') for s in slots]})

    except Exception as e:
        return JsonResponse({'slots': [], 'error': str(e)}, status=400)



def submit_guest_review(request, appointment_id):
    # Fetch the appointment to link the review to the correct business/client
    appointment = get_object_or_404(Appointment, id=appointment_id)
    business = appointment.booking_form.business

    # Prevent multiple reviews for the same appointment
    if hasattr(appointment, 'review'):
        messages.info(request, "You have already left a review for this appointment.")
        return redirect('general_landing', business_slug=business.slug)

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if not rating:
            messages.error(request, "Please select a star rating.")
        else:
            Review.objects.create(
                business=business,
                appointment=appointment,
                guest_name=appointment.guest_name,
                rating=int(rating),
                comment=comment,
                user=appointment.customer # Automatically link if the customer was logged in during booking
            )
            messages.success(request, "Thank you! Your review has been saved.")
            return redirect('general_landing', business_slug=business.slug)

    return render(request, 'bookingApp/guest_review_form.html', {
        'business': business,
        'appointment': appointment
    })



class AnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'bookingApp/analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # --- 1. Filter Parameters ---
        timeframe = self.request.GET.get('timeframe', 'month')
        staff_id = self.request.GET.get('staff_id')
        now = timezone.now()

        if timeframe == 'week':
            start_date = now - timedelta(days=7)
            days_label_format = '%a'
        elif timeframe == 'year':
            start_date = now.replace(month=1, day=1)
            days_label_format = '%b'
        else:  # month (default)
            start_date = now - timedelta(days=30)
            days_label_format = '%d %b'

        # --- 2. Base Querysets ---
        is_owner = hasattr(user, 'business')
        is_staff = hasattr(user, 'staff_profile')

        if is_owner:
            business = user.business
            context['staff_list_dropdown'] = business.staff_members.all()
            appointments = Appointment.objects.filter(staff__business=business)
            reviews = Review.objects.filter(business=business)
            context['scope_name'] = business.name

            if staff_id:
                appointments = appointments.filter(staff_id=staff_id)
                reviews = reviews.filter(appointment__staff_id=staff_id)
                try:
                    context['scope_name'] = Staff.objects.get(id=staff_id).name
                except Staff.DoesNotExist:
                    pass
        elif is_staff:
            staff_member = user.staff_profile
            appointments = Appointment.objects.filter(staff=staff_member)
            reviews = Review.objects.filter(appointment__staff=staff_member)
            context['scope_name'] = staff_member.name
        else:
            return context

        # --- 3. Apply Date Filters ---
        appointments = appointments.filter(appointment_date__gte=start_date.date())
        completed_apps = appointments.filter(status='completed')

        # --- 4. Revenue Chart Data ---
        revenue_chart_data = (
            completed_apps.values('appointment_date')
            .annotate(daily_revenue=Sum('service__price'))
            .order_by('appointment_date')
        )

        rev_labels = [d['appointment_date'].strftime(days_label_format) for d in revenue_chart_data]
        rev_values = [float(d['daily_revenue'] or 0) for d in revenue_chart_data]

        # --- 5. Busy Times (Hourly Distribution) ---
        busy_times_raw = (
            appointments.annotate(hour=ExtractHour('appointment_start_time'))
            .values('hour')
            .annotate(count=Count('id'))
            .order_by('hour')
        )

        busy_labels = []
        busy_values = []
        # Populate hours 08:00 to 20:00
        for h in range(8, 21):
            busy_labels.append(f"{h:02d}:00")
            match = next((item for item in busy_times_raw if item['hour'] == h), None)
            busy_values.append(match['count'] if match else 0)

        # --- 6. Leaderboards ---
        top_services = (
            appointments.values('service__name')
            .annotate(
                count=Count('id'),
                revenue=Sum('service__price', filter=Q(status='completed'))
            )
            .order_by('-count')[:5]
        )

        staff_performance = []
        if is_owner and not staff_id:
            staff_performance = business.staff_members.annotate(
                booking_count=Count('appointments', filter=Q(appointments__appointment_date__gte=start_date.date())),
                revenue=Sum('appointments__service__price', filter=Q(
                    appointments__appointment_date__gte=start_date.date(),
                    appointments__status='completed'
                ))
            ).order_by('-revenue')

        # --- 7. Metrics & Context ---
        deposit_val = business.deposit_amount if is_owner else 0
        no_show_appointments = appointments.filter(status='cancelled', deposit_paid=True)
        no_show_profit = no_show_appointments.count() * deposit_val

        context.update({
            'total_revenue': completed_apps.aggregate(Sum('service__price'))['service__price__sum'] or 0,
            'total_bookings': appointments.count(),
            'no_show_profit': no_show_profit,
            'avg_rating': reviews.aggregate(Avg('rating'))['rating__avg'] or 0,
            'completion_rate': (completed_apps.count() / appointments.count() * 100) if appointments.count() > 0 else 0,
            'chart_labels': json.dumps(rev_labels),
            'chart_values': json.dumps(rev_values),
            'busy_labels': json.dumps(busy_labels),
            'busy_values': json.dumps(busy_values),
            'current_filters': {'timeframe': timeframe, 'staff_id': staff_id},
            'top_services': top_services,
            'staff_performance': staff_performance,
            'is_owner': is_owner,
        })

        return context




from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.http import JsonResponse
from .models import Business, Appointment
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from django.db.models import Q
# Ensure you import your models: Business, Appointment

@login_required
def master_appointments_view(request, business_id):
    # 1. Get the business by ID first (without filtering by owner yet)
    business = get_object_or_404(Business, id=business_id)

    # 2. --- Security Check ---
    # Allow access if user is the Owner OR a Staff Member of this business
    is_owner = (business.owner == request.user)

    is_staff = False
    # Check if user has a staff profile and is linked to this business
    if hasattr(request.user, 'staff_profile'):
        if request.user.staff_profile.business == business:
            is_staff = True

    if not (is_owner or is_staff):
        # Return 404 to hide existence, or 403 for Forbidden
        raise Http404("You do not have permission to view this business.")

    # 3. --- Base Queryset ---
    appointments_list = Appointment.objects.filter(
        booking_form__business=business
    ).select_related('service', 'staff', 'customer').order_by('-appointment_date', '-appointment_start_time')

    # 4. --- Apply Filters ---
    q = request.GET.get('q')
    if q:
        appointments_list = appointments_list.filter(
            Q(customer__email__icontains=q) |
            Q(customer__first_name__icontains=q) |
            Q(guest_name__icontains=q) |
            Q(guest_email__icontains=q)
        )

    status = request.GET.get('status')
    if status:
        appointments_list = appointments_list.filter(status=status)

    staff_id = request.GET.get('staff')
    if staff_id:
        appointments_list = appointments_list.filter(staff_id=staff_id)

    service_id = request.GET.get('service')
    if service_id:
        appointments_list = appointments_list.filter(service_id=service_id)

    deposit = request.GET.get('deposit_paid')
    if deposit:
        appointments_list = appointments_list.filter(deposit_paid=(deposit == 'true'))

    reminders = request.GET.get('reminders')
    if reminders == 'sent':
        appointments_list = appointments_list.filter(Q(reminder_24h_sent=True) | Q(reminder_2h_sent=True))
    elif reminders == 'none':
        appointments_list = appointments_list.filter(reminder_24h_sent=False, reminder_2h_sent=False)

    apt_date = request.GET.get('date')
    if apt_date:
        appointments_list = appointments_list.filter(appointment_date=apt_date)

    created_at = request.GET.get('created_at')
    if created_at:
        appointments_list = appointments_list.filter(created_at__date=created_at)

    # 5. --- Pagination ---
    paginator = Paginator(appointments_list, 15)
    page_number = request.GET.get('page')
    appointments = paginator.get_page(page_number)

    # 6. --- Prepare Context ---
    context = {
        'business': business,
        'appointments': appointments,
        'staff_members': business.staff_members.all(),
        'services': business.services.all(),
        'status_choices': Appointment.STATUS_CHOICES,
    }

    # 7. --- AJAX Response Handling ---
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('bookingApp/master_appointments.html', context, request=request)
        return JsonResponse({'html': html})

    return render(request, 'bookingApp/master_appointments.html', context)

import json
from django.http import JsonResponse
from .signals import demo_completed # Import from where you defined it

import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
# Adjust the import below to match your actual folder structure
from .signals import demo_completed
from .models import DemoLead


@require_POST
def demo_booking_api(request):
    try:
        data = json.loads(request.body)

        email = data.get('email')
        send_email = data.get('send_email', True)

        email_context = {
            'name': data.get('name'),
            'service': data.get('service'),
            'staff': data.get('staff'),
            'time': data.get('time'),
        }

        if not email:
            return JsonResponse(
                {'status': 'error', 'message': 'Email address is required'},
                status=400
            )

        # 🔒 STORE DEMO EMAIL (always)
        DemoLead.objects.update_or_create(
            email=email,
            defaults=email_context
        )

        # ✉️ Optional: send demo email
        if send_email:
            demo_completed.send(
                sender=None,
                email=email,
                context=email_context
            )

        return JsonResponse({
            'status': 'success',
            'message': 'Demo processed'
        })

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)



import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

@login_required
@csrf_exempt
def save_player_id(request):
    """
    Receives OneSignal player_id from frontend and saves it to the user's profile.
    """
    if request.method == "POST":
        data = json.loads(request.body)
        player_id = data.get("player_id")
        if player_id:
            profile = request.user.profile
            profile.onesignal_player_id = player_id
            profile.save()
            return JsonResponse({"status": "ok"})
    return JsonResponse({"status": "error"}, status=400)


from django.shortcuts import get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from .models import Appointment

@staff_member_required
@require_POST
def update_appointment_status(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    new_status = request.POST.get('status')

    valid_statuses = [choice[0] for choice in Appointment.STATUS_CHOICES]

    if new_status in valid_statuses:
        appointment.status = new_status
        appointment.save()

    # Redirect back to the previous page or the registry list
    return redirect(request.META.get('HTTP_REFERER', 'appointment_registry'))

from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import ClientProfile

from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from .models import ClientProfile, Staff, Business

class ClientListView(LoginRequiredMixin, ListView):
    model = ClientProfile
    template_name = 'bookingApp/client_list.html'
    context_object_name = 'clients'

    def get_queryset(self):
        user = self.request.user

        # 1. Try to find business if user is the Owner
        try:
            business = user.business
        except Business.DoesNotExist:
            # 2. Try to find business if user is Staff
            staff_profile = Staff.objects.filter(user=user).first()
            if staff_profile:
                business = staff_profile.business
            else:
                # User has no business and is not staff
                return ClientProfile.objects.none()

        # 3. Return all clients for that business
        queryset = ClientProfile.objects.filter(business=business)

        # 4. Handle Search (the "Instant Search" bar in your template)
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                models.Q(name__icontains=query) |
                models.Q(email__icontains=query) |
                models.Q(phone__icontains=query)
            )

        return queryset.select_related('user', 'business')

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import ClientProfile

@login_required
@require_POST
def toggle_client_exemption(request, client_id):
    # Ensure the client belongs to the logged-in owner's business
    client = get_object_or_404(ClientProfile, id=client_id, business__owner=request.user)
    client.deposit_exempt = not client.deposit_exempt
    client.save()

    # Return the specific HTML fragment for the button to update it instantly
    icon = 'fa-star' if client.deposit_exempt else 'fa-star-half-stroke'
    btn_class = 'bg-blue-600 text-white' if client.deposit_exempt else 'bg-slate-100 text-slate-400'
    label = 'NO DEPOSIT' if client.deposit_exempt else 'DEPOSIT REQUIRED'

    return HttpResponse(f'''
        <button hx-post="/toggle-exemption/{client.id}/"
                hx-swap="outerHTML"
                class="inline-flex items-center px-3 py-1.5 rounded-lg font-bold text-[10px] transition-all {btn_class}">
            <i class="fa-solid {icon} mr-1.5"></i> {label}
        </button>
    ''')