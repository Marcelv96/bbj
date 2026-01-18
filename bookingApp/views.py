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


from django.shortcuts import render, redirect  # Ensure these are imported
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            # Try adding the namespace prefix 'bookingApp:' if 'business_setup_choice' alone failed
            try:
                return redirect('bookingApp:business_setup_choice')
            except:
                return redirect('business_setup_choice')
    else:
        form = CustomUserCreationForm()
    return render(request, 'bookingApp/register.html', {'form': form})

@login_required
def business_setup_choice(request):
    return render(request, 'bookingApp/business_setup_choice.html')



@login_required
def login_dispatch(request):
    # 1. Check for Business Ownership (Priority 1)
    # Using hasattr to check the OneToOne relationship defined in your models
    if hasattr(request.user, 'business'):
        return redirect('master_appointments', business_id=request.user.business.id)

    # 2. Check for Staff Profile (Priority 2)
    # This identifies employees who joined via a join_code
    if hasattr(request.user, 'staff_profile'):
        return redirect('master_appointments')

    # 3. Authenticated but neither Owner nor Staff
    # Send them to the onboarding page to register their business
    return redirect('business_setup_choice')
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
            return redirect('master_appointments', business_id=owned_business.id)

        # 2. Check if the user is a Staff Member (but not the owner)
        is_staff = Staff.objects.filter(user=request.user).exists()
        if is_staff:
            return redirect('staff_dashboard')

        # 3. If they are just a regular customer/user
        return redirect('business_setup_choice')

    # If not logged in, show the marketing landing page
    return render(request, 'bookingApp/landing.html')

def general_landing(request, business_slug):
    # This renders a specific business's booking page
    business = get_object_or_404(Business, slug=business_slug)
    return render(request, 'bookingApp/landing.html', {'business': business})

def business_detail(request, business_id):
    business = get_object_or_404(Business, id=business_id)

    reviews = business.reviews.all().order_by('-created_at')
    average_rating = business.average_rating # Using your model property

    services = business.services.all()
    staff_members = business.staff_members.all()

    is_owner = False
    user_business_id = None
    is_admin_staff = False

    if request.user.is_authenticated:
        # Check ownership
        if hasattr(request.user, 'business') and request.user.business == business:
            is_owner = True
            user_business_id = business.id

        # Check if staff
        if hasattr(request.user, 'staff_profile'):
            is_admin_staff = request.user.staff_profile.role in ['admin', 'manager']

    # Operating Hours - Correcting for your model structure
    operating_hours_display = {}
    for oh in business.operating_hours.all():
        operating_hours_display[oh.day_type] = oh

    context = {
        'business': business,
        'services': services,
        'staff_members': staff_members,
        'operating_hours': operating_hours_display,
        'reviews': reviews,
        'average_rating': average_rating,
        'is_owner': is_owner,
        'is_admin_staff': is_admin_staff,
        'user_business_id': user_business_id,
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


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse

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

            # --- TRIAL LOGIC: Set expiration to 14 days from now ---
            if is_new_business:
                business.subscription_end_date = timezone.now() + timedelta(days=14)

            # Mandatory save to generate ID and set trial date
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
                        business=business,
                        day_type=day_type,
                        open_time=open_t,
                        close_time=close_t
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
                messages.success(request, f"Welcome to {business.name}! Your 14-day free trial has started. Check out this guide to get started.")
                # Redirecting to the help page for first-time users
                return redirect('user_guide')

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



import logging
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

@csrf_exempt
def payfast_itn(request):
    """
    Unified ITN listener:
    - Extends paying business by 30 days.
    - Grants UNLIMITED referral bonuses (30 days per unique referred business).
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
                    business = Business.objects.select_related('referred_by').get(id=business_id)
                    now = timezone.now()

                    # 1. Extend the paying business's subscription
                    # If they are still in their 14-day trial, add 30 days to the end of that trial.
                    if business.subscription_end_date and business.subscription_end_date > now:
                        business.subscription_end_date += timedelta(days=30)
                    else:
                        business.subscription_end_date = now + timedelta(days=30)

                    # 2. Unlimited Referral Logic
                    # If they were referred, and we haven't rewarded the referrer yet
                    if business.referred_by and not business.referral_bonus_paid:
                        referrer = business.referred_by

                        # Add 30 days to the referrer's account
                        if referrer.subscription_end_date and referrer.subscription_end_date > now:
                            referrer.subscription_end_date += timedelta(days=30)
                        else:
                            referrer.subscription_end_date = now + timedelta(days=30)

                        referrer.save()

                        # Mark this business so it never pays out a bonus again
                        business.referral_bonus_paid = True
                        logger.info(f"REFERRAL PAYOUT: Business {referrer.id} gained 30 days from {business.id}")

                    business.save()
                    logger.info(f"SUBSCRIPTION SUCCESS: Business {business_id} updated.")

                # --- ROUTE 2: Appointment Deposit ---
                elif m_payment_id.startswith('APP-'):
                    appointment_id = data.get('custom_int1') or m_payment_id.split('-')[1]
                    appointment = Appointment.objects.get(id=appointment_id)
                    appointment.status = 'confirmed'
                    appointment.deposit_paid = True
                    appointment.save()
                    logger.info(f"DEPOSIT SUCCESS: Appointment {appointment_id} confirmed.")

                return HttpResponse(status=200)

            except Exception as e:
                logger.error(f"ITN Error: {str(e)} | Data: {data}")
                return HttpResponse(status=400)

        return HttpResponse(status=200)

    return HttpResponse(status=400)




from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
import requests
import hashlib
import urllib.parse

from .models import (
    Business, Staff, Appointment, OperatingHours, BusinessBlock
)
from .utils import cleanup_expired_appointments, generate_payfast_url


# --- HELPER FUNCTION: SOFT VALIDATION ---
def validate_payfast_format(merchant_id, merchant_key):
    if not merchant_id or not merchant_key:
        return False, "Merchant ID and Key are required."
    if not merchant_id.isdigit():
        return False, "Merchant ID must be numeric."
    if len(merchant_key) < 10:
        return False, "Merchant Key looks invalid."
    return True, None


# --- HELPER FUNCTION: REAL PAYFAST CHECK ---
def verify_payfast_credentials(merchant_id, merchant_key):
    """
    Basic sanity check for PayFast credentials.
    Returns True if they look valid enough to save.
    """
    # 1. Must exist
    if not merchant_id or not merchant_key:
        return False

    # 2. Merchant ID: numeric only
    if not str(merchant_id).isdigit():
        return False

    # 3. Merchant Key: at least 10 chars
    if len(merchant_key.strip()) < 10:
        return False

    # 4. Optional: sandbox/live API call here in future
    # For now, we allow saving
    return True


@login_required
def owner_dashboard(request, business_id):
    business = get_object_or_404(Business, id=business_id)

    # --- 1. CLEANUP ---
    cleanup_expired_appointments(business)

    # --- 2. PERMISSION CHECK ---
    is_owner = business.owner == request.user
    is_admin_staff = Staff.objects.filter(user=request.user, business=business, role='ADMIN').exists()
    if not (is_owner or is_admin_staff):
        messages.error(request, "Access Denied.")
        return redirect('home')

    # --- 3. SUBSCRIPTION CHECK ---
    SUBSCRIPTION_PRICE = 199.00
    if not business.subscription_end_date or business.subscription_end_date < timezone.now():
        return render(request, 'bookingApp/dashboard_locked.html', {
            'business': business,
            'pay_url': generate_payfast_url(business, SUBSCRIPTION_PRICE)
        })

    # --- 4. HANDLE POST REQUESTS ---
    if request.method == "POST":
        action = request.POST.get('action')

        # --- PROFILE UPDATE ---
        if action == "update_profile":
            business.name = request.POST.get('name')
            business.contact_number = request.POST.get('phone_number')
            business.address = request.POST.get('address')
            business.buffer_time = request.POST.get('buffer_time', 0)
            business.description = request.POST.get('description')
            business.instagram_url = request.POST.get('instagram_url')
            business.facebook_url = request.POST.get('facebook_url')
            business.twitter_url = request.POST.get('twitter_url')

            if 'cover_image' in request.FILES:
                business.cover_image = request.FILES['cover_image']

            business.save()
            messages.success(request, "Business profile and social links updated successfully.")

        # --- PAYFAST & DEPOSIT SETTINGS ---
        elif action == "update_payfast":
            merchant_id = request.POST.get('payfast_merchant_id')
            merchant_key = request.POST.get('payfast_merchant_key')

            # Verify credentials before saving
            if not verify_payfast_credentials(merchant_id, merchant_key):
                messages.error(request, "PayFast credentials are invalid (format error).")
                return redirect('owner_dashboard', business_id=business.id)

            # Save credentials and deposit settings
            business.payfast_merchant_id = merchant_id
            business.payfast_merchant_key = merchant_key

            business.deposit_type = request.POST.get('deposit_type', 'fixed')

            if business.deposit_type == 'percentage':
                dep_percent = request.POST.get('deposit_percentage')
                try:
                    business.deposit_percentage = int(float(dep_percent)) if dep_percent else 0
                except ValueError:
                    business.deposit_percentage = 0
                business.deposit_amount = 0.00
            else:
                deposit_amt = request.POST.get('deposit_amount')
                try:
                    business.deposit_amount = float(deposit_amt) if deposit_amt else 0.00
                except ValueError:
                    business.deposit_amount = 0.00
                business.deposit_percentage = 0

            res_window = request.POST.get('reschedule_window_hours')
            business.reschedule_window_hours = int(res_window) if res_window else 24
            business.deposit_policy = request.POST.get('deposit_policy')

            business.save()
            messages.success(request, "Deposit settings and payment credentials updated.")
            return redirect('owner_dashboard', business_id=business.id)



        # --- OPERATING HOURS ---
        elif action == "update_hours":
            for field_name, day_type in [('mon_fri', 'mon_fri'), ('sat', 'sat'), ('sun', 'sun')]:
                open_t = request.POST.get(f'open_{field_name}')
                close_t = request.POST.get(f'close_{field_name}')
                if open_t and close_t:
                    OperatingHours.objects.update_or_create(
                        business=business,
                        day_type=day_type,
                        defaults={'open_time': open_t, 'close_time': close_t}
                    )
            messages.success(request, "Operating hours updated.")

        # --- BLOCKED DAYS ---
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

    # --- 5. FETCH DATA FOR UI ---
    today = timezone.now().date()
    # Access it directly via the new related_name
    booking_form = getattr(business, 'booking_form', None)

    base_appointments = Appointment.objects.filter(
        booking_form__business=business
    ).select_related('service', 'customer').order_by('appointment_start_time')

    calendar_events = [{
        'title': appt.customer.get_full_name() if appt.customer else f"{appt.guest_name} (Guest)",
        'start': f"{appt.appointment_date.isoformat()}T{appt.appointment_start_time.strftime('%H:%M:%S')}",
        'backgroundColor': '#6366f1' if appt.status == 'confirmed' else ('#ef4444' if appt.status == 'cancelled' else '#f59e0b'),
    } for appt in base_appointments]

    context = {
        'business': business,
        'booking_form': booking_form,
        'days_left': business.days_remaining,
        'pay_url': get_subscription_url(business, SUBSCRIPTION_PRICE),
        'today_appointments': base_appointments.filter(
            appointment_date=today
        ).exclude(status__in=['cancelled', 'declined', 'completed']).order_by('appointment_start_time'),
        'upcoming_appointments': base_appointments.filter(
            appointment_date__gte=today
        ).exclude(status__in=['completed', 'cancelled', 'declined']).order_by('appointment_date', 'appointment_start_time'),
        'past_appointments': base_appointments.filter(
            Q(appointment_date__lt=today) | Q(status__in=['completed', 'cancelled', 'declined'])
        ).order_by('-appointment_date', '-appointment_start_time'),
        'operating_hours': {oh.day_type: oh for oh in business.operating_hours.all()},
        'business_blocks': business.blocks.filter(block_date__gte=today),
        'services': business.services.all(),
        'staff_members': business.staff_members.all().select_related('user__profile'),
        'calendar_events': calendar_events,
        'is_admin': (is_owner or is_admin_staff),
        'deposit_required': business.deposit_required,
    }

    return render(request, 'bookingApp/owner_dashboard.html', context)



def book_appointment_public(request, token):
    # This finds the form that actually exists based on the secret token
    booking_form = get_object_or_404(BookingForm, embed_token=token)

    # Now it passes the REAL id (e.g., 14 or 15) to the booking logic
    return book_appointment(request, booking_form_id=booking_form.id)

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

from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages

@require_POST
def service_delete(request, business_id, service_id):
    # Match the parameter names from your URL path
    service = get_object_or_404(Service, id=service_id, business_id=business_id)
    service.delete()
    messages.success(request, "Service deleted successfully.")

    # Corrected redirect to match your URL name and param
    return redirect('owner_dashboard', business_id=business_id)

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
import logging
from datetime import datetime, date
from decimal import Decimal

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone

from .models import Business, BookingForm, Service, Staff, ClientProfile, Appointment
from .forms import AppointmentForm
from .utils import (
    get_available_times,
    calculate_deposit_amount,
    generate_appointment_payfast_url,
    send_deposit_request_email,
    send_push_notification,
    trigger_pending_reminders
)

logger = logging.getLogger(__name__)

@xframe_options_exempt
@ensure_csrf_cookie
def book_appointment(request, business_slug=None, booking_form_id=None):
    if business_slug:
        business = get_object_or_404(Business, slug=business_slug)
        booking_form = getattr(business, 'booking_form', None)
    elif booking_form_id:
        booking_form = get_object_or_404(BookingForm, id=booking_form_id)
        business = booking_form.business

    # Trigger background tasks (e.g., automated reminders)
    trigger_pending_reminders()

    services = Service.objects.filter(business=business)
    staff_members = Staff.objects.filter(business=business)
    is_embedded = request.GET.get('embed') == 'true'

    if request.method == 'POST':
        selected_date_str = request.POST.get('appointment_date')
        selected_service_id = request.POST.get('service')
        selected_staff_id = request.POST.get('staff')

        # Filter Service & Staff strictly by service qualification for form validation
        selected_service = services.filter(id=selected_service_id).first() if selected_service_id else None

        if selected_service:
            staff_members = staff_members.filter(services=selected_service)
        else:
            staff_members = staff_members.none()

        selected_date = None
        available_times = []

        # Re-calculate availability for validation context
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

        # Initialize Form with filtered querysets
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

            # --- PUSH NOTIFICATION LOGIC ---
            try:
                owner = business.owner
                player_id = getattr(owner.profile, "onesignal_player_id", None)

                if player_id:
                    msg = f"New booking from {appointment.guest_name} for {appointment.service.name}"
                    send_push_notification([player_id], msg)
                else:
                    logger.warning(f"No OneSignal player ID for owner {owner.id}")
            except Exception as e:
                logger.error(f"Failed to send owner notification: {e}")
            # --- END PUSH NOTIFICATION ---

            # Handle Redirection / Success
            if requires_payment:
                try:
                    pay_url = generate_appointment_payfast_url(request, appointment)

                    # Only send email if a deposit is actually required and amount > 0
                    # This uses the 'requires_payment' boolean defined in the exemption logic
                    send_deposit_request_email(appointment, pay_url)

                    # Return JavaScript Breakout for iFrames/Embedded forms
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
                except Exception as e:
                    logger.error(f"Payment Redirect Error: {e}")
                    messages.warning(request, "Payment redirect failed, but a link has been emailed to you.")
                    return render(request, 'bookingApp/booking_success_guest.html', {'appointment': appointment})

            else:
                # Case: Deposit Exempt OR Business doesn't require deposit
                # No email is sent here because requires_payment is False
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

        # Inside if request.method == "POST":

        # Add this block:
        elif 'confirm_appointment' in request.POST:
            appt_id = request.POST.get('appointment_id')
            Appointment.objects.filter(
                id=appt_id,
                staff=staff_profile,
                status='pending'
            ).update(status='confirmed')
            messages.success(request, "Appointment confirmed.")

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

    today = timezone.now().date()
# Generate next 7 days for the week picker
    week_dates = [today + timedelta(days=i) for i in range(7)]

    context = {
        'staff': staff_profile,
        'business': business,
        'todays_appointments': todays_appointments,
        'upcoming': upcoming,
        'week_dates': week_dates,
        'today': today,
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
    is_admin_staff = Staff.objects.filter(user=request.user, business=business, role='ADMIN').exists()
    is_owner = (business.owner == request.user or is_admin_staff)
    is_customer = (appointment.customer == request.user or appointment.guest_email == request.user.email)

    # 3. Handle Status Updates & Rescheduling (Existing POST Logic)
    # In views.py, inside appointment_detail(request, pk)
    if request.method == "POST":
        # If using fetch(url, {body: formData}), it's in request.POST
        action = request.POST.get('action')

        # If action is None, check if it was sent as a standalone 'status' key
        # (which your JS handles in window.handleStatusUpdate)
        new_status = request.POST.get('status')

        if new_status:
            valid_statuses = [choice[0] for choice in Appointment.STATUS_CHOICES]
            if new_status in valid_statuses:
                appointment.status = new_status
                appointment.save()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'success'})

            # LOGIC 2: Reschedule (Moved out of the status update IF)
            if action == 'reschedule_submit' and is_customer:
                form = RescheduleAppointmentForm(request.POST, instance=appointment)
                if form.is_valid():
                    appt = form.save(commit=False)
                    appt.status = 'reschedule_requested'
                    appt.save()
                    return JsonResponse({'status': 'success'})
                return JsonResponse({'status': 'error', 'errors': form.errors})

            return JsonResponse({'status': 'error', 'message': 'Invalid Action'}, status=400)

    # 4. Generate Link Sending Data (Exemption Logic Added Here)
    pay_url = None
    payment_whatsapp_url = None

    # Check if a ClientProfile exists for this email at this business and if they are exempt
    is_exempt = ClientProfile.objects.filter(
        business=business,
        email=appointment.guest_email
    ).filter(deposit_exempt=True).exists()

    # Logic: Show payment block only if business requires it, user isn't exempt,
    # it hasn't been paid, and it's a valid active appointment.
    show_payment_section = (
        business.deposit_required and
        not is_exempt and
        not appointment.deposit_paid and
        appointment.status not in ['cancelled', 'declined']
    )

    if show_payment_section:
        pay_url = generate_appointment_payfast_url(request, appointment)

        if appointment.formatted_whatsapp_number:
            message_text = (
                f"Hi {appointment.guest_name}, this is {business.name}. "
                f"To confirm your booking for {appointment.service.name}, "
                f"please complete the deposit of R{business.deposit_amount} here: {pay_url}"
            )
            params = {'text': message_text}
            payment_whatsapp_url = f"https://wa.me/{appointment.formatted_whatsapp_number}?{urlencode(params)}"

    gcal_url = get_owner_gcal_link(appointment)
    # 5. Render
    context = {
        'appointment': appointment,
        'is_owner': is_owner,
        'is_customer': is_customer,
        'reschedule_form': RescheduleAppointmentForm(instance=appointment),
        'pay_url': pay_url,
        'payment_whatsapp_url': payment_whatsapp_url,
        'gcal_url': gcal_url,
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

from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponse

def appointment_reschedule(request, token):
    # 1. Fetch the original appointment
    appointment = get_object_or_404(Appointment, reschedule_token=token)
    business = appointment.booking_form.business

    # 2. Calculate if it's within the restricted window
    appointment_datetime = timezone.make_aware(
        datetime.combine(appointment.appointment_date, appointment.appointment_start_time)
    )
    hours_window = business.reschedule_window_hours
    limit_time = timezone.now() + timedelta(hours=hours_window)
    is_too_late = appointment_datetime < limit_time

    if request.method == 'POST':
        # Bind the form to the appointment instance
        form = RescheduleAppointmentForm(request.POST, instance=appointment)
        late_confirmation_given = request.POST.get('confirm_deposit_loss') == 'on'

        if is_too_late and not late_confirmation_given:
            form.add_error(None, "You must confirm that you understand the deposit will be lost.")

        elif form.is_valid():
            new_date = form.cleaned_data.get('appointment_date')
            new_time = form.cleaned_data.get('appointment_start_time')

            # Standardize time format for comparison
            new_time_str = new_time.strftime('%H:%M') if hasattr(new_time, 'strftime') else new_time
            selected_staff = appointment.staff

            # Check availability
            available_slots = get_available_times(
                business=business,
                appointment_date=new_date,
                service_length=appointment.service.default_length_minutes,
                staff_id=selected_staff.id if selected_staff else None,
                service_obj=appointment.service
            )

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
                    # Calculate the new deposit amount based on the business settings
                    new_deposit = business.calculate_deposit(appointment.service.price)

                    # 1. Create a NEW Appointment object
                    new_appt = Appointment.objects.create(
                        booking_form=appointment.booking_form,
                        service=appointment.service,
                        customer=appointment.customer,
                        guest_name=appointment.guest_name,
                        guest_email=appointment.guest_email,
                        guest_phone=appointment.guest_phone,
                        appointment_date=new_date,
                        appointment_start_time=new_time,
                        staff=selected_staff,
                        status='pending',
                        deposit_paid=False,
                        amount_to_pay=new_deposit,  # <--- FIX: Pass the calculated deposit here
                        notes=f"Rescheduled from Appt #{appointment.id}. Previous deposit forfeited."
                    )

                    # 2. Revert the OLD appointment in memory and then cancel it
                    # This prevents the new time from being saved to the old record
                    appointment.refresh_from_db()
                    appointment.status = 'cancelled'
                    appointment.notes = (appointment.notes or "") + f"\n[SYSTEM]: Late reschedule. Deposit forfeited. Re-booked as Appt #{new_appt.id}."
                    appointment.save()

                    # 3. Handle Payment Redirect
                    if business.deposit_required:
                        try:
                            pay_url = generate_appointment_payfast_url(request, new_appt)
                            send_deposit_request_email(new_appt, pay_url)
                            return HttpResponse(f"""
                                <html><body>
                                    <p>Reschedule accepted. Redirecting to payment for new deposit...</p>
                                    <script>window.top.location.href = "{pay_url}";</script>
                                </body></html>
                            """)
                        except Exception as e:
                            return render(request, 'bookingApp/booking_success_guest.html', {'appointment': new_appt})

                    return render(request, 'bookingApp/reschedule_success.html', {'appointment': new_appt, 'is_too_late': True})

                # ====================================================
                # LOGIC BRANCH: EARLY RESCHEDULE (STANDARD)
                # ====================================================
                else:
                    # Update the existing appointment record
                    appt = form.save(commit=False)
                    appt.status = 'pending'
                    appt.save()

                    # Notification Logic
                    client_name = appt.customer.get_full_name() if appt.customer else appt.guest_name
                    customer_email = appt.guest_email or (appt.customer.email if appt.customer else None)
                    staff_recipient = appt.staff.user.email if (appt.staff and hasattr(appt.staff, 'user')) else business.owner.email

                    context = {
                        'appointment': appt,
                        'client_name': client_name,
                        'business': business,
                        'site_url': settings.SITE_URL,
                        'is_too_late': False
                    }

                    # Notify Staff
                    if staff_recipient:
                        html_staff = render_to_string('bookingApp/owner_reschedule_notification.html', context)
                        send_mail(f"Reschedule Request - {client_name}", strip_tags(html_staff), settings.DEFAULT_FROM_EMAIL, [staff_recipient], html_message=html_staff, fail_silently=True)

                    # Notify Customer
                    if customer_email:
                        html_cust = render_to_string('bookingApp/customer_status_update.html', context)
                        send_mail(f"Reschedule Confirmed: {business.name}", f"Hi {client_name}, your reschedule is confirmed.", settings.DEFAULT_FROM_EMAIL, [customer_email], html_message=html_cust, fail_silently=True)

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
    # Ensure the appointment belongs to the user
    appointment = get_object_or_404(Appointment, pk=pk, customer=request.user)

    if request.method == 'POST':
        appointment.status = 'cancelled'
        # Crucial: We do NOT change deposit_paid to False.
        # The business keeps the money.
        appointment.save()
        return redirect('my_appointments')

    return render(request, 'bookingApp/appointment_confirm_cancel.html', {'appointment': appointment})

# views.py
from django.utils import timezone
from datetime import datetime, timedelta

def appointment_cancel_guest(request, token):
    # Fetch by token instead of PK/User for guests
    appointment = get_object_or_404(Appointment, reschedule_token=token)
    business = appointment.booking_form.business

    # Logic to check if cancellation is within the non-refundable window
    # Combine date and time to get the full start datetime
    appt_start = datetime.combine(appointment.appointment_date, appointment.appointment_start_time)
    if timezone.is_aware(appt_start):
        now = timezone.now()
    else:
        now = datetime.now()

    # Determine if it's too late to keep the deposit
    is_late = now + timedelta(hours=business.reschedule_window_hours) > appt_start

    if request.method == 'POST':
        appointment.status = 'cancelled'
        appointment.save()
        # You could redirect to a "Booking Cancelled" success page
        return render(request, 'bookingApp/cancel_success.html', {'business': business})

    return render(request, 'bookingApp/appointment_confirm_cancel.html', {
        'appointment': appointment,
        'is_guest': True,
        'is_late': is_late,
        'business': business
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
            # Check if your owner_dashboard URL also uses a business_id.
            # If it doesn't, remove the business_id=... here as well.
            return redirect('staff_dashboard')

        # Create the staff profile with ADMIN privileges
        Staff.objects.create(
            business=business,
            user=request.user,
            name=request.user.get_full_name() or request.user.username,
            email=request.user.email,
            role='ADMIN'
        )

        if hasattr(request.user, 'profile'):
            request.user.profile.is_business_owner = True
            request.user.profile.save()

        messages.success(request, f"Access granted to {business.name}! Remember to select your Services and set your Hours so clients can book you!")

        # FIX: Removed business_id because the 'staff_dashboard' URL pattern does not accept arguments
        return redirect('staff_dashboard')

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

from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from urllib.parse import urlencode

from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.http import urlencode
from .models import Business, Staff, BookingForm
from .forms import ManualBookingForm
from .utils import (
    trigger_pending_reminders,
    generate_appointment_payfast_url,
    send_deposit_request_email
)

@login_required
def manual_booking(request, business_id):
    """
    Allows business owners or admin staff to create appointments manually.
    Now correctly references the OneToOne booking_form relationship.
    """
    business = get_object_or_404(Business, id=business_id)
    trigger_pending_reminders()

    # --- Permission Check ---
    is_admin_staff = Staff.objects.filter(user=request.user, business=business, role='ADMIN').exists()
    if business.owner != request.user and not is_admin_staff:
        messages.error(request, "Unauthorized access.")
        return redirect('home')

    if request.method == 'POST':
        form = ManualBookingForm(request.POST, business=business)
        if form.is_valid():
            appointment = form.save(commit=False)

            # --- UPDATED: Accessing OneToOneField via singular related_name ---
            target_form = getattr(business, 'booking_form', None)

            if not target_form:
                messages.error(request, "Please create a Booking Form first.")
                return redirect('owner_dashboard', business_id=business.id)

            appointment.booking_form = target_form

            # --- NEW LOGIC: Handle Deposit & Exemption ---
            guest_email = form.cleaned_data.get('guest_email')

            # Check if deposit is required globally AND if this specific client is NOT exempt
            deposit_needed = business.is_deposit_required_for_client(guest_email)

            if deposit_needed:
                appointment.status = 'pending'

                # Calculate deposit safely using Decimal
                if appointment.service and appointment.service.price is not None:
                    # Uses business logic to determine percentage or fixed amount
                    deposit_percent = business.deposit_percentage or 100
                    price = appointment.service.price
                    appointment.amount_to_pay = (price * (Decimal(deposit_percent) / Decimal('100'))).quantize(Decimal('0.01'))
                else:
                    appointment.amount_to_pay = Decimal('0.00')

                appointment.save()

                # Generate PayFast URL (using the business slug indirectly via utility)
                pay_url = generate_appointment_payfast_url(request, appointment)

                # Auto-send email ONLY if guest email exists
                email_sent = False
                if appointment.guest_email:
                    send_deposit_request_email(appointment, pay_url)
                    email_sent = True

                # Generate WhatsApp link for manual sharing
                whatsapp_url = None
                if appointment.formatted_whatsapp_number:
                    msg = f"Hi {appointment.guest_name}, please complete your deposit for {appointment.service.name} here: {pay_url}"
                    whatsapp_url = f"https://wa.me/{appointment.formatted_whatsapp_number}?{urlencode({'text': msg})}"

                # Render success / action screen
                return render(request, 'bookingApp/manual_booking_success.html', {
                    'appointment': appointment,
                    'pay_url': pay_url,
                    'whatsapp_url': whatsapp_url,
                    'email_sent': email_sent
                })

            else:
                # No deposit required OR client is exempt
                appointment.status = 'confirmed'
                appointment.amount_to_pay = Decimal('0.00')
                appointment.deposit_paid = True # Mark as paid since no payment is needed
                appointment.save()

                status_msg = f"Booking for {appointment.guest_name} confirmed!"
                if business.deposit_required: # Clarify bypass for exempt clients
                    status_msg += " (Client is deposit exempt)"

                messages.success(request, status_msg)
                return redirect('owner_dashboard', business_id=business.id)

    else:
        form = ManualBookingForm(business=business)

    return render(request, 'bookingApp/manual_booking.html', {
        'form': form,
        'business': business
    })
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


import json
from django.db.models import Sum, Avg, Count, Q
from django.db.models.functions import ExtractHour
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
import json
from django.db.models import Sum, Avg, Count, Q
from django.db.models.functions import ExtractHour
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from .models import Appointment, Review, Staff, Business

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

        # --- 2. Identity & Business Resolution ---
        is_owner = hasattr(user, 'business')
        is_staff = hasattr(user, 'staff_profile')
        business_obj = None

        if is_owner:
            business_obj = user.business
            context['staff_list_dropdown'] = business_obj.staff_members.all()
            appointments = Appointment.objects.filter(staff__business=business_obj)
            reviews = Review.objects.filter(business=business_obj)
            context['scope_name'] = business_obj.name

            if staff_id:
                appointments = appointments.filter(staff_id=staff_id)
                reviews = reviews.filter(appointment__staff_id=staff_id)
                try:
                    context['scope_name'] = Staff.objects.get(id=staff_id).name
                except Staff.DoesNotExist:
                    pass

        elif is_staff:
            staff_member = user.staff_profile
            business_obj = staff_member.business
            appointments = Appointment.objects.filter(staff=staff_member)
            reviews = Review.objects.filter(appointment__staff=staff_member)
            context['scope_name'] = staff_member.name
        else:
            return context

        # --- 3. Apply Date Filters ---
        start_date_only = start_date.date()
        appointments = appointments.filter(appointment_date__gte=start_date_only)
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
            staff_performance = business_obj.staff_members.annotate(
                booking_count=Count('appointments', filter=Q(appointments__appointment_date__gte=start_date_only)),
                revenue=Sum('appointments__service__price', filter=Q(
                    appointments__appointment_date__gte=start_date_only,
                    appointments__status='completed'
                ))
            ).order_by('-revenue')

        # --- 7. Metrics & Context (The "R0" Fix) ---
        # Instead of multiplying count by business.deposit_amount,
        # we sum the ACTUAL 'amount_to_pay' stored on cancelled appointments.
        no_show_profit = appointments.filter(
            status='cancelled',
            deposit_paid=True
        ).aggregate(total=Sum('amount_to_pay'))['total'] or 0

        context.update({
            'total_revenue': completed_apps.aggregate(Sum('service__price'))['service__price__sum'] or 0,
            'total_bookings': appointments.count(),
            'no_show_profit': no_show_profit, # Now summing actual captured cash
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
from datetime import date
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, Http404
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from datetime import date, timedelta, datetime
import calendar
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone

# Ensure you import your models
# from .models import Business, Appointment

@login_required
def master_appointments_view(request, business_id):
    # 1. Get business and check security
    business = get_object_or_404(Business, id=business_id)

    is_owner = (business.owner == request.user)
    staff_profile = getattr(request.user, 'staff_profile', None)
    is_staff = staff_profile is not None and staff_profile.business == business

    if not (is_owner or is_staff):
        raise Http404("You do not have permission to view this business.")

    # 🔒 2. Subscription Lock Logic
    if not business.subscription_end_date or business.subscription_end_date < timezone.now():
        return render(request, 'bookingApp/dashboard_locked.html', {
            'business': business,
            'is_staff': is_staff,
            'is_owner': is_owner,
        })

    # 3. Extract and Parse Parameters
    view_mode = request.GET.get('view_mode', 'my')
    scale = request.GET.get('scale', 'day') # 'day', 'week', 'month'
    q = request.GET.get('q')
    status = request.GET.get('status')
    staff_id = request.GET.get('staff')
    service_id = request.GET.get('service')

    # Parse the date string into a Date object for calculations
    raw_date = request.GET.get('date', date.today().isoformat())
    try:
        current_date_obj = datetime.strptime(raw_date, '%Y-%m-%d').date()
    except ValueError:
        current_date_obj = date.today()

    # 4. Determine Date Range based on Scale
    context_extras = {} # To store week_dates or calendar_grid

    if scale == 'week':
        # Find Monday of the current week
        start_of_week = current_date_obj - timedelta(days=current_date_obj.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        filter_start = start_of_week
        filter_end = end_of_week

        # Pass the list of 7 dates for the table headers
        context_extras['week_dates'] = [start_of_week + timedelta(days=i) for i in range(7)]

    elif scale == 'month':
        # Find 1st and Last day of month
        year, month = current_date_obj.year, current_date_obj.month
        num_days = calendar.monthrange(year, month)[1]

        start_of_month = date(year, month, 1)
        end_of_month = date(year, month, num_days)

        filter_start = start_of_month
        filter_end = end_of_month

        # Build Grid Logic:
        # We need to know which weekday the month starts on (0=Mon, 6=Sun)
        # to add "empty" slots at the beginning of the grid.
        start_weekday = start_of_month.weekday()

        calendar_days = []
        # Add padding for previous month days (empty dicts or None)
        for _ in range(start_weekday):
            calendar_days.append(None)

        # Add actual days
        for day in range(1, num_days + 1):
            calendar_days.append(date(year, month, day))

        context_extras['calendar_days'] = calendar_days

    else: # Default to 'day'
        filter_start = current_date_obj
        filter_end = current_date_obj

    # 5. Base Queryset - Filter by Date Range
    appointments_list = Appointment.objects.filter(
        booking_form__business=business,
        appointment_date__range=[filter_start, filter_end]
    ).select_related('service', 'staff', 'customer').order_by('appointment_start_time')

    # 6. Apply "Personal" vs "Team" Logic
    if view_mode == 'my':
        if is_staff:
            appointments_list = appointments_list.filter(staff=staff_profile)
        elif is_owner and not staff_id:
            pass # Owner sees all if no specific staff selected

    # 7. Apply Secondary Filters
    if q:
        appointments_list = appointments_list.filter(
            Q(customer__email__icontains=q) |
            Q(customer__first_name__icontains=q) |
            Q(guest_name__icontains=q) |
            Q(guest_email__icontains=q)
        )

    if status:
        appointments_list = appointments_list.filter(status=status)

    if staff_id:
        appointments_list = appointments_list.filter(staff_id=staff_id)

    if service_id:
        appointments_list = appointments_list.filter(service_id=service_id)

    # 8. Pagination logic
    # We DISABLE pagination for Week/Month views because the visual grid
    # requires all data to render correctly. We only paginate the list view (Day).
    if scale == 'day':
        paginator = Paginator(appointments_list, 50)
        page_number = request.GET.get('page')
        appointments_page = paginator.get_page(page_number)
    else:
        # Return all objects for matrix views
        appointments_page = appointments_list

    # 9. Prepare Context
    context = {
        'business': business,
        'appointments': appointments_page,
        'staff_members': business.staff_members.all(),
        'services': business.services.all(),
        'status_choices': Appointment.STATUS_CHOICES,
        'today_date': date.today().isoformat(),
        'current_date': raw_date, # The string value for the input
        'current_date_obj': current_date_obj, # The object for logic
        'view_mode': view_mode,
        'scale': scale,
        **context_extras # Merges week_dates or calendar_days into context
    }

    # 10. AJAX Response Handling
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('bookingApp/master_appointments.html', context, request=request)
        return JsonResponse({'html': html})

    return render(request, 'bookingApp/master_appointments.html', context)


import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import DemoLead
from .signals import demo_completed


@require_POST
def demo_booking_api(request):
    data = json.loads(request.body)

    email = data.get('email')
    send_email = data.get('send_email', True)

    if not email:
        return JsonResponse(
            {'status': 'error', 'message': 'Email address is required'},
            status=400
        )

    email_context = {
        'name': data.get('name'),
        'service': data.get('service'),
        'staff': data.get('staff'),
        'time': data.get('time'),
    }

    # 🔒 Always store lead
    DemoLead.objects.update_or_create(
        email=email,
        defaults=email_context
    )

    # ✉️ NON-NEGOTIABLE EMAIL
    if send_email:
        demo_completed.send(
            sender=DemoLead,
            email=email,
            context=email_context
        )

    return JsonResponse({
        'status': 'success',
        'message': 'Demo booked and email sent'
    })




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

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
@login_required # Use login_required instead of staff_member for testing
@require_POST
def update_appointment_status(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)

    # Security check: Ensure user belongs to this business
    business = appointment.booking_form.business
    if not (business.owner == request.user or hasattr(request.user, 'staff_profile')):
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    # Handle both FormData (standard) and JSON
    if request.content_type == 'application/json':
        data = json.loads(request.body)
        new_status = data.get('status')
    else:
        new_status = request.POST.get('status')

    valid_statuses = [choice[0] for choice in Appointment.STATUS_CHOICES]
    if new_status in valid_statuses:
        appointment.status = new_status
        appointment.save()
        return JsonResponse({'status': 'success', 'new_status': appointment.status})

    return JsonResponse({'status': 'error', 'message': f'Invalid status: {new_status}'}, status=400)

from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import ClientProfile

from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.db.models import Max, Q, F, Count, Sum
from django.db.models.functions import Coalesce
from .models import ClientProfile, Staff, Business

import urllib.parse
from decimal import Decimal
from django.db.models import Max, Q, Count, Sum, DecimalField, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.core.exceptions import ObjectDoesNotExist
from .models import ClientProfile, Staff, Appointment, Business

from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count, Sum, DecimalField, OuterRef, Subquery, F
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
# Import your models: ClientProfile, Appointment, Staff, etc.
from django.db.models import Subquery, OuterRef, Count, Sum, Q, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

class ClientListView(LoginRequiredMixin, ListView):
    model = ClientProfile
    template_name = 'bookingApp/client_list.html'
    context_object_name = 'clients'
    paginate_by = 25

    def get_queryset(self):
        user = self.request.user

        # 1. Identify Business
        try:
            business = user.business
        except AttributeError:
            staff_profile = getattr(user, 'staff_profile', None)
            if staff_profile:
                business = staff_profile.business
            else:
                return ClientProfile.objects.none()

        # 2. Base Relationship
        appointments_base = Appointment.objects.filter(
            Q(guest_email=OuterRef('email')) | Q(customer__email=OuterRef('email')),
            service__business=business
        )

        # 3. Subqueries

        # Last Appointment Date
        last_appt_subquery = appointments_base.filter(
            status='completed'
        ).order_by('-appointment_date').values('appointment_date')[:1]

        # Total Completed Bookings
        count_subquery = appointments_base.filter(
            status='completed'
        ).annotate(
            total_count=Count('id')
        ).values('total_count')[:1]

        # LTV Calculation: Sum of 'service__price' (Full Revenue)
        sum_subquery = appointments_base.filter(
            status='completed'
        ).annotate(
            total_revenue=Sum('service__price')
        ).values('total_revenue')[:1]

        # NEW: Total Deposits Calculation: Sum of 'amount_to_pay'
        deposit_sum_subquery = appointments_base.filter(
            status='completed',
            deposit_paid=True  # <--- Filter to only include successful transactions
        ).annotate(
            total_deposits=Sum('amount_to_pay')
        ).values('total_deposits')[:1]

        # 4. Base Queryset with Annotations
        queryset = ClientProfile.objects.filter(business=business).annotate(
            last_appointment_date=Subquery(last_appt_subquery),
            annotated_appointment_count=Coalesce(
                Subquery(count_subquery),
                0
            ),
            annotated_total_spent=Coalesce(
                Subquery(sum_subquery, output_field=DecimalField()),
                Decimal('0.00')
            ),
            # New annotation for deposits
            annotated_total_deposit=Coalesce(
                Subquery(deposit_sum_subquery, output_field=DecimalField()),
                Decimal('0.00')
            )
        )

        # 5. Filter: Search
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(phone__icontains=query) |
                Q(email__icontains=query)
            )

        # 6. Filter: Status (Overdue/New)
        status_filter = self.request.GET.get('status')
        today = timezone.now().date()
        if status_filter == 'overdue':
            thirty_days_ago = today - timedelta(days=30)
            queryset = queryset.filter(last_appointment_date__lte=thirty_days_ago)
        elif status_filter == 'new':
            thirty_days_ago = today - timedelta(days=30)
            queryset = queryset.filter(created_at__gte=thirty_days_ago)

        # 7. Filter: Deposit
        deposit_filter = self.request.GET.get('deposit')
        if deposit_filter == 'exempt':
            queryset = queryset.filter(deposit_exempt=True)
        elif deposit_filter == 'required':
            queryset = queryset.filter(deposit_exempt=False)

        # 8. Sorting
        sort_by = self.request.GET.get('sort', 'created_at')
        direction = self.request.GET.get('direction', 'desc')

        sort_map = {
            'name': 'name',
            'revenue': 'annotated_total_spent',
            'deposits': 'annotated_total_deposit', # Enabled sorting for new column
            'bookings': 'annotated_appointment_count',
            'last_visit': 'last_appointment_date',
            'created_at': 'created_at'
        }

        db_field = sort_map.get(sort_by, 'created_at')
        if direction == 'desc':
            db_field = f'-{db_field}'

        return queryset.order_by(db_field)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'current_q': self.request.GET.get('q', ''),
            'current_sort': self.request.GET.get('sort', 'created_at'),
            'current_direction': self.request.GET.get('direction', 'desc'),
            'current_status': self.request.GET.get('status', 'all'),
            'current_deposit': self.request.GET.get('deposit', 'all'),
        })
        return context

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import ClientProfile
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.urls import reverse

@login_required
@require_POST
def toggle_client_exemption(request, client_id):
    # Ensure ownership security
    client = get_object_or_404(ClientProfile, id=client_id, business__owner=request.user)

    # Toggle the state
    client.deposit_exempt = not client.deposit_exempt
    client.save()

    # Prepare logic for the updated HTML
    checked = "checked" if client.deposit_exempt else ""
    color_class = "text-emerald-600" if client.deposit_exempt else "text-red-500"
    label = "NO DEPOSIT" if client.deposit_exempt else "DEPOSIT REQUIRED"

    # Get the POST URL dynamically
    post_url = reverse('toggle_client_exemption', args=[client.id])

    # This response replaces the old form, re-arming HTMX for the next click
    return HttpResponse(f'''
        <form hx-post="{post_url}"
              hx-trigger="change from:find input"
              hx-target="this"
              hx-swap="outerHTML"
              hx-headers='{{"X-CSRFToken": "{get_token(request)}"}}'
              class="flex flex-col items-center flex-shrink-0">
            <label class="toggle-wrapper inline-block">
                <input type="checkbox" name="exempt" class="toggle-input" {checked}>
                <div class="toggle-track"><div class="toggle-thumb"></div></div>
            </label>
            <span class="text-[8px] font-black uppercase mt-1 tracking-widest {color_class}">
                {label}
            </span>
        </form>
    ''')



