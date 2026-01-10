from datetime import datetime, timedelta
from .models import OperatingHours, StaffOperatingHours, Appointment, Staff, StaffBlock

from .models import OperatingHours, StaffOperatingHours, Appointment, Staff, StaffBlock, BusinessBlock

# utils.py
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
from .models import OperatingHours, StaffOperatingHours, Appointment, Staff, StaffBlock, BusinessBlock

# Correct logging setup

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
from .models import BusinessBlock, Staff, StaffOperatingHours, Appointment, StaffBlock

logger = logging.getLogger(__name__)

def get_available_times(business, appointment_date, service_length, staff_id=None, service_obj=None):
    """
    Evaluates availability with Smart Group Booking logic.
    - Blocks if staff is on a different service.
    - Allows overlap if it's the same service and capacity isn't reached.
    """

    # 0. CHECK BUSINESS-WIDE BLOCKED DAYS
    if BusinessBlock.objects.filter(business=business, block_date=appointment_date).exists():
        return []

    weekday = appointment_date.weekday()
    day_key = 'mon_fri' if weekday <= 4 else ('sat' if weekday == 5 else 'sun')

    staff = None
    oh = None

    # 1. ATTEMPT STAFF LOOKUP
    clean_staff_id = str(staff_id).strip() if staff_id else ""
    if clean_staff_id and clean_staff_id not in ["", "None", "null", "undefined"]:
        staff = Staff.objects.filter(id=clean_staff_id).first()
        if staff:
            oh = StaffOperatingHours.objects.filter(staff=staff, day_type=day_key).first()

    # 2. FALLBACK TO BUSINESS
    if not oh:
        oh = business.operating_hours.filter(day_type=day_key).first()

    if not oh:
        return []

    # 3. GENERATE POTENTIAL SLOTS
    slot_interval = timedelta(minutes=30)
    service_duration = timedelta(minutes=service_length)
    potential_slots = []

    current_time = timezone.make_aware(
        datetime.combine(appointment_date, oh.open_time),
        timezone.get_current_timezone()
    )
    end_time = timezone.make_aware(
        datetime.combine(appointment_date, oh.close_time),
        timezone.get_current_timezone()
    )

    # Today Buffer
    now = timezone.now()
    if appointment_date == now.date():
        start_threshold = now + timedelta(minutes=30)
        if current_time < start_threshold:
            current_time = start_threshold
            minute_remainder = current_time.minute % 30
            if minute_remainder > 0:
                current_time += timedelta(minutes=(30 - minute_remainder))
                current_time = current_time.replace(second=0, microsecond=0)

    while current_time + service_duration <= end_time:
        potential_slots.append(current_time.time())
        current_time += slot_interval

    # 4. FILTER CONFLICTS
    expiry_limit = timezone.now() - timedelta(hours=2)
    query_filter = Q(appointment_date=appointment_date)

    if staff:
        query_filter &= Q(staff=staff)
    else:
        query_filter &= Q(booking_form__business=business)

    existing_appointments = Appointment.objects.filter(query_filter).filter(
        Q(status__in=['confirmed', 'reschedule_requested']) |
        Q(status='pending', created_at__gt=expiry_limit)
    ).select_related('service')

    staff_blocks = StaffBlock.objects.filter(staff=staff, block_date=appointment_date) if staff else []

    available_slots = []
    max_capacity = service_obj.capacity if service_obj else 1

    for slot_time in potential_slots:
        slot_start = datetime.combine(appointment_date, slot_time)
        slot_end = slot_start + service_duration

        is_blocked = False
        current_attendees = 0

        # A. Check against Appointment overlaps
        for appt in existing_appointments:
            appt_start = datetime.combine(appt.appointment_date, appt.appointment_start_time)
            appt_end = appt_start + timedelta(minutes=appt.service.default_length_minutes)

            # If times overlap
            if slot_start < appt_end and slot_end > appt_start:
                if service_obj and appt.service_id == service_obj.id:
                    # Same session: Add to attendee count
                    current_attendees += appt.attendees
                else:
                    # Different session: Hard block staff
                    is_blocked = True
                    break

        if is_blocked:
            continue

        # If capacity for the same session is already met, hide slot
        if current_attendees >= max_capacity:
            continue

        # B. Check against Staff Blocks
        for block in staff_blocks:
            b_start = datetime.combine(appointment_date, block.start_time)
            b_end = datetime.combine(appointment_date, block.end_time)
            if slot_start < b_end and slot_end > b_start:
                is_blocked = True
                break

        if not is_blocked:
            available_slots.append(slot_time)

    return available_slots
# utils.py
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

from django.utils import timezone
from datetime import datetime, timedelta
from .models import Appointment
import logging

logger = logging.getLogger(__name__)

def trigger_pending_reminders():
    """Checks for reminders and Auto-Completes past appointments."""
    now = timezone.now()

    # 1. Fetch 24-Hour Reminders
    reminders_24h = Appointment.objects.filter(
        status='confirmed',
        reminder_24h_sent=False,
        appointment_date=(now + timedelta(hours=24)).date(),
        appointment_start_time__lte=(now + timedelta(hours=24)).time()
    )

    # 2. Fetch 2-Hour Reminders
    reminders_2h = Appointment.objects.filter(
        status='confirmed',
        reminder_2h_sent=False,
        appointment_date=(now + timedelta(hours=2)).date(),
        appointment_start_time__lte=(now + timedelta(hours=2)).time()
    )

    # 3. AUTO-COMPLETE LOGIC (2 Hours After Booking Time)
    # We look for confirmed appointments that have ended at least 2 hours ago.
    past_limit = now - timedelta(minutes=10)
    potential_completions = Appointment.objects.filter(status='confirmed')

    for appt in potential_completions:
        # Create a timezone-aware datetime for the start time
        start_dt = timezone.make_aware(datetime.combine(appt.appointment_date, appt.appointment_start_time))
        # End time = Start time + duration of the service
        end_dt = start_dt + timedelta(minutes=appt.service.default_length_minutes)

        # If the appointment ended more than 2 hours ago, mark as complete
        if end_dt < past_limit:
            appt.status = 'completed'
            # save() triggers the 'notify_workflow' signal which sends the Review Email
            appt.save(update_fields=['status'])
            logger.info(f"Auto-completed Appointment {appt.id}")

    # Process reminder emails
    from .utils import send_reminder_batch # Assuming this helper exists
    send_reminder_batch(reminders_24h, "24 hours", "24h")
    send_reminder_batch(reminders_2h, "2 hours", "2h")

def send_reminder_batch(queryset, timeframe_label, field_prefix):
    for appt in queryset:
        # 1. Determine recipient email safely
        recipient = None

        # Check 'customer' field (since 'user' doesn't exist)
        customer = getattr(appt, 'customer', None)
        if customer and hasattr(customer, 'email') and customer.email:
            recipient = customer.email

        # Fallback to guest_email
        if not recipient:
            recipient = getattr(appt, 'guest_email', None)

        if not recipient:
            continue

        # 2. Safety check for business
        # Using .first() because booking_form might be a related manager
        business = None
        if appt.booking_form:
            business = appt.booking_form.business

        if not business:
            continue

        context = {
            'appointment': appt,
            'business': business,
            'timeframe': timeframe_label,
            'site_url': settings.SITE_URL,
        }

        try:
            html_message = render_to_string('bookingApp/email_reminder.html', context)

            send_mail(
                subject=f"Reminder: Appointment in {timeframe_label}",
                message=f"Your appointment at {business.name} is soon.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                html_message=html_message,
                fail_silently=True
            )

            # 3. Mark as sent using update_fields to avoid re-triggering signals
            if field_prefix == "24h":
                appt.reminder_24h_sent = True
                appt.save(update_fields=['reminder_24h_sent'])
            else:
                appt.reminder_2h_sent = True
                appt.save(update_fields=['reminder_2h_sent'])

        except Exception as e:
            print(f"Reminder Error for Appt {appt.id}: {e}")
            continue

def send_owner_paid_notification(appointment):
    business = appointment.booking_form.business
    context = {
        'appointment': appointment,
        'business': business,
        'owner': business.owner,
        'customer_name': appointment.guest_name,
        'site_url': settings.SITE_URL,
    }
    html_message = render_to_string('bookingApp/owner_notification_paid.html', context)
    send_mail(
        f"✅ NEW PAID BOOKING: {appointment.service.name}",
        f"Payment received from {appointment.guest_name}",
        settings.DEFAULT_FROM_EMAIL,
        [business.owner.email],
        html_message=html_message
    )

# utils.py or inside views.py
import hashlib
from urllib.parse import urlencode
from django.conf import settings

def generate_payfast_url(business, amount):
    # Use a list of tuples to maintain order for signature
    params = [
        ('merchant_id', '33083387'), # Your platform ID
        ('merchant_key', 'su9wfcs6tngdj'),
        ('return_url', 'https://www.getmebooked.co.za/help/',),
        ('cancel_url', 'https://www.getmebooked.co.za/business/onboarding/'),
        ('notify_url', 'https://www.getmebooked.co.za/payfast/itn/'),
        ('m_payment_id', f"SUB-{business.id}-{int(timezone.now().timestamp())}"),
        ('amount', f"{amount:.2f}"),
        ('item_name', f"Platform Activation: {business.name}"),
        ('custom_int1', str(business.id)),
    ]

    # Generate Signature
    pf_common = ""
    for key, value in params:
        if value:
            pf_common += f"{key}={urllib.parse.quote_plus(str(value).strip())}&"

    pf_string = pf_common + f"passphrase={urllib.parse.quote_plus('VanWyknBake420')}"
    signature = hashlib.md5(pf_string.encode()).hexdigest()

    # Build final URL
    payload = dict(params)
    payload['signature'] = signature

    base_url = "https://www.payfast.co.za/eng/process"
    return f"{base_url}?{urllib.parse.urlencode(payload)}" # Removed the '}'

import hashlib
import urllib.parse
from django.core.mail import send_mail
from django.conf import settings

import hashlib
import urllib.parse
from django.conf import settings

def calculate_deposit_amount(business, service_price):
    """Calculates the required deposit based on business settings."""
    if not business.deposit_required:
        return 0.00

    if business.deposit_type == 'percentage':
        if not service_price:
            return 0.00
        # Calculate percentage: (Price * % / 100)
        amount = (service_price * business.deposit_percentage) / 100
        return round(amount, 2)
    else:
        # Fixed amount
        return business.deposit_amount

import hashlib
import urllib.parse
from django.utils import timezone

def generate_appointment_payfast_url(request, appointment):
    """
    Generates the secure PayFast URL for a LIVE appointment deposit.
    Includes timestamp to allow retries/cancellations without 'Duplicate Transaction' errors.
    """
    business = appointment.booking_form.business

    # 1. Credentials
    m_id = str(business.payfast_merchant_id or "").strip()
    m_key = str(business.payfast_merchant_key or "").strip()
    passphrase = "VanWyknBake420"

    amount_val = appointment.amount_to_pay

    # 2. Parameters
    payfast_params = [
        ('merchant_id', m_id),
        ('merchant_key', m_key),
        ('return_url', request.build_absolute_uri(f'/booking/success/{appointment.id}/')),
        ('cancel_url', request.build_absolute_uri('/')),
        ('notify_url', 'https://www.getmebooked.co.za/payfast/itn/'),
        ('name_first', str(appointment.guest_name).split()[0] if appointment.guest_name else "Guest"),
        ('email_address', str(appointment.guest_email or "")),
        # CRITICAL FIX: Added timestamp to make every attempt unique
        ('m_payment_id', f"APP-{appointment.id}-{int(timezone.now().timestamp())}"),
        ('amount', f"{amount_val:.2f}"),
        ('item_name', f"Deposit: {appointment.service.name}"),
        ('custom_int1', str(appointment.id)),
    ]

    # 3. Signature Generation (With Empty Value Cleaning)
    # We filter out empty values BEFORE generating the signature string
    clean_params = [(k, v) for k, v in payfast_params if v.strip()]

    pf_common = ""
    for key, value in clean_params:
        pf_common += f"{key}={urllib.parse.quote_plus(str(value).strip())}&"

    pf_string = pf_common.rstrip('&')
    if passphrase:
        pf_string += f"&passphrase={urllib.parse.quote_plus(passphrase.strip())}"

    signature = hashlib.md5(pf_string.encode()).hexdigest()

    # 4. Build Final Params
    final_params = dict(clean_params)
    final_params['signature'] = signature

    return f"https://www.payfast.co.za/eng/process?{urllib.parse.urlencode(final_params)}"

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

# utils.py
from django.template.loader import render_to_string
from django.core.mail import EmailMessage

def send_deposit_request_email(appointment, pay_url):
    subject = f"Complete your booking at {appointment.booking_form.business.name}"

    # Ensure the appointment object is passed into context
    context = {
        'appointment': appointment,
        'payfast_url': pay_url,
        'business': appointment.booking_form.business,
    }

    html_content = render_to_string('bookingApp/email_deposit_request.html', context)

    email = EmailMessage(
        subject,
        html_content,
        to=[appointment.guest_email],
    )
    email.content_subtype = "html"
    email.send()

# utils.py
from django.utils import timezone
from datetime import timedelta
from .models import Appointment

# utils.py

def cleanup_expired_appointments(business):
    # Only run cleanup if the business actually requires deposits
    if not business.deposit_required:
        return

    limit = timezone.now() - timedelta(hours=2)

    expired = Appointment.objects.filter(
        booking_form__business=business,
        status='pending',
        created_at__lt=limit,
        deposit_paid=False  # They haven't paid
    )

    for appt in expired:
        appt.status = 'cancelled'
        appt.save()


import requests

ONESIGNAL_APP_ID = "755c884c-75a6-4624-b4fe-5089ee21abac"
ONESIGNAL_REST_API_KEY = "os_v2_app_ovoiqtdvuzdcjnh6kce64inlvsnlqzt6d5ceouuuoptflbqxc2okb2xt2ym3zyzkwlsiqws7rcdoyh5izolrlzr3pg55zddxaaek6vy"

def send_push_notification(player_ids, message):
    """
    Send push notifications to a list of OneSignal player_ids
    """
    if not player_ids:
        return {"error": "No player IDs provided"}

    url = "https://onesignal.com/api/v1/notifications"
    payload = {
        "app_id": ONESIGNAL_APP_ID,
        "include_external_user_ids": player_ids,  # List of player IDs
        "contents": {"en": message}
    }
    headers = {
        "Authorization": f"Basic {ONESIGNAL_REST_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()
