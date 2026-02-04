from datetime import datetime, timedelta
from .models import OperatingHours, StaffOperatingHours, Appointment, Staff, StaffBlock

# Correct logging setup

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
from .models import (
    OperatingHours,
    StaffOperatingHours,
    Appointment,
    Staff,
    StaffBlock,
    BusinessBlock
)

logger = logging.getLogger(__name__)

def get_available_times(business, appointment_date, service_length, staff_id=None, service_obj=None):
    """
    Evaluates availability with Smart Group Booking logic and Business Buffer.
    - Blocks if staff is on a different service.
    - Allows overlap if it's the same service and capacity isn't reached.
    - Dynamically generates slots based on buffer time to avoid "dead time".
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
    # Get buffer from business (e.g., 15)
    buffer_minutes = getattr(business, 'buffer_time', 0)
    buffer_delta = timedelta(minutes=buffer_minutes)

    # FIX: Set the search interval to 15 minutes or the buffer time.
    # This ensures a 10:45 slot can actually be found.
    search_interval = min(15, buffer_minutes) if buffer_minutes > 0 else 15
    slot_interval = timedelta(minutes=search_interval)

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

    # --- TODAY BUFFER ---
    now = timezone.now().astimezone(timezone.get_current_timezone())
    if appointment_date == now.date():
        # Buffer for 'today' still starts from next full hour for professional look
        next_hour_start = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        if next_hour_start > current_time:
            current_time = next_hour_start

    # Loop to find all possible start times
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
        Q(status__in=['confirmed', 'reschedule_requested', 'rescheduled']) |
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

        # A. Check against Appointment overlaps + Buffer
        for appt in existing_appointments:
            appt_start = datetime.combine(appt.appointment_date, appt.appointment_start_time)
            appt_end = appt_start + timedelta(minutes=appt.service.default_length_minutes)

            # Define the blocked range for an existing appointment:
            # It blocks from (Start - Buffer) to (End + Buffer)
            blocked_start = appt_start - buffer_delta
            blocked_end = appt_end + buffer_delta

            if slot_start < blocked_end and slot_end > blocked_start:
                # Group Booking Logic:
                # If it's the EXACT same session (same service & same start time), ignore buffer
                if service_obj and appt.service_id == service_obj.id and appt_start == slot_start:
                    current_attendees += appt.attendees
                else:
                    # It's either a different service or it's overlapping the buffer zone
                    is_blocked = True
                    break

        if is_blocked:
            continue

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

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.db.models import Q
from .models import Appointment

logger = logging.getLogger(__name__)

def trigger_pending_reminders():
    """
    Checks for confirmed appointments that need 24h or 2h reminders
    and haven't received them yet.
    """
    now = timezone.now()

    # 1. Define Thresholds
    # We want to find appointments that start roughly within the lookahead window
    threshold_24h = now + timedelta(hours=24)
    threshold_2h = now + timedelta(hours=2)

    # ---------------------------------------------------------
    # LOGIC: 24 HOUR REMINDERS
    # Condition:
    # 1. Confirmed
    # 2. 24h Reminder NOT sent
    # 3. Appt is in the future (greater than now)
    # 4. Appt is LESS than 24 hours away (lte threshold_24h)
    # 5. (Optional Safety) Don't send 24h reminder if it's already less than 2h away (avoid double email spam)
    # ---------------------------------------------------------

    # We need to filter in Python for precise datetime combination or use complex DB annotations.
    # To keep it efficient/readable, we filter loosely in DB and precisely in Python.

    # Grab candidates for the next 25 hours to be safe
    candidates = Appointment.objects.filter(
        status='confirmed',
        appointment_date__gte=now.date(),
        appointment_date__lte=(now + timedelta(days=2)).date()
    ).select_related('booking_form__business')

    reminders_24h = []
    reminders_2h = []

    for appt in candidates:
        # Combine Date and Time to make it aware
        try:
            naive_start = datetime.combine(appt.appointment_date, appt.appointment_start_time)
            # Ensure we use the server's configured timezone
            start_dt = timezone.make_aware(naive_start, timezone.get_current_timezone())
        except Exception as e:
            logger.error(f"Timezone error for appt {appt.id}: {e}")
            continue

        time_until_appt = start_dt - now

        # --- Check 24 Hour Reminder ---
        # If it is less than 24h away, but more than 2h away, and we haven't sent it yet.
        if (timedelta(hours=2) < time_until_appt <= timedelta(hours=24)) and not appt.reminder_24h_sent:
            reminders_24h.append(appt)

        # --- Check 2 Hour Reminder ---
        # If it is less than 2h away (but still in future), and we haven't sent it yet.
        if (timedelta(minutes=0) < time_until_appt <= timedelta(hours=2)) and not appt.reminder_2h_sent:
            reminders_2h.append(appt)

    # Send the batches
    if reminders_24h:
        logger.info(f"Sending 24h reminders to {len(reminders_24h)} recipients.")
        send_reminder_batch(reminders_24h, "24 hours", "reminder_24h_sent")

    if reminders_2h:
        logger.info(f"Sending 2h reminders to {len(reminders_2h)} recipients.")
        send_reminder_batch(reminders_2h, "2 hours", "reminder_2h_sent")

    # --- Auto-Complete Logic (Preserved) ---
    process_auto_completions(now)

def process_auto_completions(now):
    # Moved to separate function for cleanliness
    potential_completions = Appointment.objects.filter(status='confirmed', appointment_date__lte=now.date())
    for appt in potential_completions:
        try:
            naive_start = datetime.combine(appt.appointment_date, appt.appointment_start_time)
            start_dt = timezone.make_aware(naive_start, timezone.get_current_timezone())
            completion_threshold = start_dt + timedelta(hours=2)

            if now >= completion_threshold:
                appt.status = 'completed'
                appt.save(update_fields=['status'])
                logger.info(f"Auto-completed Appointment {appt.id}")
        except Exception:
            logger.exception(f"Error auto-completing appointment {appt.id}")

# send_reminder_batch remains exactly as you wrote it

def send_reminder_batch(appointments, timeframe_label, sent_field_name):
    """
    appointments: list of Appointment instances
    timeframe_label: string for subject/body ("24 hours", "2 hours")
    sent_field_name: model field to mark True ('reminder_24h_sent' or 'reminder_2h_sent')
    """
    for appt in appointments:
        try:
            # Safety checks
            recipient = None
            customer = getattr(appt, 'customer', None)
            if customer and getattr(customer, 'email', None):
                recipient = customer.email
            elif appt.guest_email:
                recipient = appt.guest_email

            if not recipient:
                logger.info("Skipping reminder for appt %s: no recipient", appt.id)
                continue

            business = getattr(appt.booking_form, 'business', None)
            if not business:
                logger.warning("Skipping reminder for appt %s: no business", appt.id)
                continue

            context = {
                'appointment': appt,
                'business': business,
                'timeframe': timeframe_label,
                'site_url': settings.SITE_URL,
            }
            html_message = render_to_string('bookingApp/email_reminder.html', context)
            plain_message = f"Your appointment at {business.name} is coming up in {timeframe_label}."

            # Send email
            send_mail(
                subject=f"Reminder: Appointment in {timeframe_label}",
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                html_message=html_message,
                fail_silently=False  # consider True in production if you prefer to only log
            )

            # Mark it as sent in an atomic manner
            setattr(appt, sent_field_name, True)
            appt.save(update_fields=[sent_field_name])

            logger.info("Sent %s reminder for appt %s to %s", timeframe_label, appt.id, recipient)

        except Exception:
            logger.exception("Failed to send reminder for appt %s", appt.id)

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
# Change this line:
def generate_payfast_url(business, amount=None):  # Add =None here
    amount = business.subscription_price          # This pulls R199 or R349 automatically

    params = [
        ('merchant_id', settings.PAYFAST_MERCHANT_ID),
        ('merchant_key', settings.PAYFAST_MERCHANT_KEY),
        ('return_url', 'https://www.getmebooked.co.za/help/'),
        ('cancel_url', 'https://www.getmebooked.co.za/business/onboarding/'),
        ('notify_url', 'https://www.getmebooked.co.za/payfast/itn/'),
        ('m_payment_id', f"SUB-{business.id}-{int(timezone.now().timestamp())}"),
        ('amount', f"{amount:.2f}"),
        ('item_name', f"Platform Activation: {business.name}"),
        ('custom_int1', str(business.id)),
    ]

    pf_string = ""
    for key, value in params:
        if value:
            pf_string += f"{key}={urllib.parse.quote_plus(str(value).strip())}&"

    pf_string = pf_string.rstrip("&")

    passphrase = (settings.PAYFAST_PASSPHRASE or "").strip()
    if passphrase:
        pf_string += f"&passphrase={urllib.parse.quote_plus(passphrase)}"

    signature = hashlib.md5(pf_string.encode()).hexdigest()

    final_params = params + [('signature', signature)]
    return "https://www.payfast.co.za/eng/process?" + urllib.parse.urlencode(final_params)

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
import hashlib
import urllib.parse
from django.utils import timezone


def generate_appointment_payfast_url(request, appointment):
    business = appointment.booking_form.business

    merchant_id = str(business.payfast_merchant_id).strip()
    merchant_key = str(business.payfast_merchant_key).strip()
    passphrase = (business.payfast_passphrase or "").strip()

    params = [
        ("merchant_id", merchant_id),
        ("merchant_key", merchant_key),
        ("return_url", request.build_absolute_uri(
            f"/booking/success/{appointment.id}/"
        )),
        ("cancel_url", request.build_absolute_uri("/")),
        ("notify_url", "https://www.getmebooked.co.za/payfast/itn/"),
        ("name_first", appointment.guest_name.split()[0] if appointment.guest_name else "Guest"),
        ("email_address", appointment.guest_email or ""),
        ("m_payment_id", f"APP-{appointment.id}-{int(timezone.now().timestamp())}"),
        ("amount", f"{appointment.amount_to_pay:.2f}"),
        ("item_name", f"Deposit: {appointment.service.name}"),
        ("custom_int1", str(appointment.id)),
    ]

    # Remove empty values
    params = [(k, v) for k, v in params if str(v).strip()]

    pf_string = ""
    for key, value in params:
        pf_string += f"{key}={urllib.parse.quote_plus(str(value))}&"

    pf_string = pf_string.rstrip("&")

    if passphrase:
        pf_string += f"&passphrase={urllib.parse.quote_plus(passphrase)}"

    signature = hashlib.md5(pf_string.encode()).hexdigest()

    params.append(("signature", signature))

    return "https://www.payfast.co.za/eng/process?" + urllib.parse.urlencode(params)


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

    limit = timezone.now() - timedelta(minutes=10)

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

import requests
import logging
import logging
import requests

logger = logging.getLogger(__name__)

def send_push_notification(player_ids, message):
    if not player_ids:
        return

    payload = {
        "app_id": "755c884c-75a6-4624-b4fe-5089ee21abac",
        "include_player_ids": player_ids,
        "headings": {"en": "New Booking"},
        "contents": {"en": message}
    }

    headers = {
        "Authorization": "Basic nlqzt6d5ceouuuoptflbqxc2o",
        "Content-Type": "application/json"
    }


    response = requests.post(
        "https://onesignal.com/api/v1/notifications",
        json=payload,
        headers=headers,
        timeout=10
    )

    logger.info(f"OneSignal response: {response.text}")



from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.timezone import localtime
from datetime import timedelta
from django.conf import settings
from .models import Business
import logging

logger = logging.getLogger(__name__)

def send_subscription_expiry_reminders():
    """
    Checks for businesses expiring in exactly 1 or 2 days and sends reminders.
    Designed to be run once daily via PythonAnywhere Scheduled Tasks.
    """
    # Use localtime to ensure we match the business owner's day
    today = localtime(timezone.now()).date()

    reminders = [
        {'days': 2, 'target_date': today + timedelta(days=2)},
        {'days': 1, 'target_date': today + timedelta(days=1)},
    ]

    for reminder in reminders:
        # Filter for the date part of the DateTimeField
        expiring_businesses = Business.objects.filter(
            subscription_end_date__date=reminder['target_date']
        )

        logger.info(f"Checking for {reminder['days']} day reminders. Found: {expiring_businesses.count()}")

        for business in expiring_businesses:
            subject = f"⚠️ Reminder: Your {business.name} subscription expires in {reminder['days']} day(s)"

            context = {
                'business': business,
                'days_left': reminder['days'],
            }

            html_content = render_to_string('emails/subscription_expiry.html', context)
            # Fallback text for email clients that don't support HTML
            text_content = f"Hi {business.owner.first_name}, your subscription for {business.name} expires in {reminder['days']} days. Renew here: https://www.getmebooked.co.za/business/{business.id}/owner/dashboard/"

            try:
                msg = EmailMultiAlternatives(
                    subject,
                    text_content,
                    settings.DEFAULT_FROM_EMAIL,
                    [business.owner.email]
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send(fail_silently=False) # Keep False while testing to see errors in task logs
                logger.info(f"✅ Expiry reminder sent to {business.owner.email} for {business.name}")
            except Exception as e:
                logger.error(f"❌ Failed to send expiry reminder to {business.owner.email}: {str(e)}")