from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Appointment
from datetime import datetime, timedelta
import urllib.parse
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Business, Staff

import logging
import urllib.parse
from datetime import datetime, timedelta

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

from .models import Appointment

logger = logging.getLogger(__name__)
import logging
import urllib.parse
from datetime import datetime, timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Appointment

logger = logging.getLogger(__name__)

# --- 1. OWNER NOTIFICATIONS ---



# --- 2. CUSTOMER NOTIFICATIONS ---

import logging
import urllib.parse
from datetime import datetime, timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Appointment

logger = logging.getLogger(__name__)

import logging
import urllib.parse
from datetime import datetime, timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Appointment

logger = logging.getLogger(__name__)
import logging
import urllib.parse
from datetime import datetime, timedelta
import hashlib
import urllib.parse
import logging
from datetime import datetime, timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Appointment, Business, Staff

import hashlib
import urllib.parse
import logging
from datetime import datetime, timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from .models import Appointment
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Business, Staff, StaffBlock, StaffOperatingHours, BookingForm

from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Business, Staff, StaffBlock, StaffOperatingHours, BookingForm
from allauth.socialaccount.signals import social_account_added
from django.dispatch import receiver

@receiver(social_account_added)
def ensure_password_not_removed(request, sociallogin, **kwargs):
    user = sociallogin.user
    if not user.has_usable_password():
        # DO NOTHING — but block accidental removal
        user.set_unusable_password()
        user.save()


def notify_owner(staff_instance, subject_line, message_body):
    """
    Helper function to send email to the business owner.
    Prevents notification if the staff member IS the business owner.
    """
    business = staff_instance.business
    owner = business.owner

    # Guard: Don't notify if the owner is making changes to their own profile
    if staff_instance.user == owner:
        return

    send_mail(
        subject=subject_line,
        message=message_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[owner.email],
        fail_silently=True,
    )

# --- 1. SIGNAL: Staff Adds a Block Day ---
@receiver(post_save, sender=StaffBlock)
def signal_staff_block_created(sender, instance, created, **kwargs):
    if created:
        subject = f"Staff Schedule Block: {instance.staff.name}"
        body = (
            f"Staff member {instance.staff.name} has added a block:\n\n"
            f"Date: {instance.block_date}\n"
            f"Time: {instance.start_time} - {instance.end_time}\n"
            f"Reason: {instance.reason or 'Personal'}\n\n"
            f"Review this in your dashboard."
        )
        notify_owner(instance.staff, subject, body)

# --- 2. SIGNAL: Staff Changes Operating Hours ---
@receiver(post_save, sender=StaffOperatingHours)
def signal_staff_hours_updated(sender, instance, created, **kwargs):
    action = "set" if created else "updated"
    subject = f"Staff Hours Updated: {instance.staff.name}"
    body = (
        f"Staff member {instance.staff.name} has {action} hours for "
        f"{instance.get_day_type_display()}:\n\n"
        f"New Hours: {instance.open_time} - {instance.close_time}"
    )
    notify_owner(instance.staff, subject, body)

# --- 3. SIGNAL: Staff Changes Services (Includes List) ---
@receiver(m2m_changed, sender=Staff.services.through)
def signal_staff_services_updated(sender, instance, action, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        # Get list of all services now offered
        services_list = "\n".join([f"- {s.name}" for s in instance.services.all()])

        subject = f"Staff Services Updated: {instance.name}"
        body = (
            f"Staff member {instance.name} has updated their services.\n\n"
            f"They now offer:\n"
            f"{services_list if services_list else '- No services selected'}\n\n"
            f"Business: {instance.business.name}"
        )
        notify_owner(instance, subject, body)

# --- 4. SIGNAL: Auto-create Booking Form ---
@receiver(post_save, sender=Business)
def create_business_booking_form(sender, instance, created, **kwargs):
    if created:
        BookingForm.objects.create(
            business=instance,
            name=f"Booking Form - {instance.name}"
        )

logger = logging.getLogger(__name__)

import logging
import hashlib
import urllib.parse
from datetime import datetime, timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from .models import Appointment

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Appointment)
def notify_workflow(sender, instance, created, **kwargs):
    try:
        if not instance.booking_form or not instance.service:
            return

        business = instance.booking_form.business
        owner = business.owner

        # Determine Recipient Safely
        recipient = instance.guest_email or (instance.customer.email if instance.customer else None)
        customer_name = instance.guest_name or (instance.customer.get_full_name() if instance.customer else "Valued Customer")

        # --- SECTION 1: OWNER NOTIFICATIONS (New Bookings) ---
        # Triggered for EVERY new appointment creation
        if created and instance.status == 'pending':
            context = {
                'appointment': instance,
                'business': business,
                'owner': owner,
                'customer_name': customer_name,
                'site_url': settings.SITE_URL,
            }
            # Note: Using your requested template name 'owner_notify.html'
            html_owner = render_to_string('bookingApp/owner_notification.html', context)

            send_mail(
                subject=f"New Request: {instance.service.name} - {customer_name}",
                message=f"New booking request from {customer_name}.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[owner.email],
                html_message=html_owner,
                fail_silently=True
            )

            if business.deposit_required:
                logger.info(f"Appt {instance.id}: Owner notified. Customer must still pay deposit.")

        # --- SECTION 2: STATUS UPDATES ---
        if instance.status == 'cancelled':
            # Notify Owner
            context_owner = {
                'appointment': instance,
                'customer_name': customer_name,
                'site_url': settings.SITE_URL,
                'business': business
            }
            html_cancel_owner = render_to_string('bookingApp/owner_cancelled.html', context_owner)
            send_mail(f"🚨 Cancelled: {customer_name}", "", settings.DEFAULT_FROM_EMAIL, [owner.email], html_message=html_cancel_owner, fail_silently=True)

            # Notify Customer
            if recipient:
                context_cust = {
                    'appointment': instance,
                    'business': business,
                    'site_url': settings.SITE_URL
                }
                html_declined = render_to_string('bookingApp/email_appointment_cancelled.html', context_cust)
                send_mail(
                    subject="Booking Update: Cancelled",
                    message=f"Your appointment at {business.name} has been cancelled.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient],
                    html_message=html_declined,
                    fail_silently=True
                )

        elif instance.status == 'confirmed' and recipient:
            # 1. GCal Link Generation
            start_dt = datetime.combine(instance.appointment_date, instance.appointment_start_time)
            end_dt = start_dt + timedelta(minutes=instance.service.default_length_minutes)
            fmt = "%Y%m%dT%H%M%S"

            gcal_params = {
                'action': 'TEMPLATE',
                'text': f"{instance.service.name} @ {business.name}",
                'dates': f"{start_dt.strftime(fmt)}/{end_dt.strftime(fmt)}",
                'location': business.name,
            }
            gcal_link = "https://www.google.com/calendar/render?" + urllib.parse.urlencode(gcal_params)

            # 2. Secure PayFast Link
            payfast_url = None
            m_id = str(business.payfast_merchant_id or "").strip()
            if m_id.isdigit() and business.deposit_amount > 0 and not instance.deposit_paid:
                pf_params = [
                    ('merchant_id', m_id),
                    ('merchant_key', str(business.payfast_merchant_key).strip()),
                    ('return_url', f"{settings.SITE_URL}/booking/success/{instance.id}/"),
                    ('cancel_url', f"{settings.SITE_URL}/"),
                    ('notify_url', "https://www.getmebooked.co.za/payfast/itn/"),
                    ('name_first', customer_name.split()[0]),
                    ('email_address', recipient),
                    ('m_payment_id', f"APP-{instance.id}"),
                    ('amount', f"{business.deposit_amount:.2f}"),
                    ('item_name', f"Deposit {instance.service.name}"),
                ]

                pf_common = "".join([f"{k}={urllib.parse.quote_plus(str(v).strip())}&" for k, v in pf_params])
                pf_string = pf_common + "passphrase=VanWyknBake420"
                sig = hashlib.md5(pf_string.encode()).hexdigest()

                final_params = dict(pf_params)
                final_params['signature'] = sig
                payfast_url = "https://www.payfast.co.za/eng/process?" + urllib.parse.urlencode(final_params)

            context = {
                'appointment': instance,
                'business': business,
                'gcal_link': gcal_link,
                'payfast_url': payfast_url,
                'site_url': settings.SITE_URL,
            }

            html_cust = render_to_string('bookingApp/customer_status_update.html', context)
            send_mail(f"Confirmed: {instance.service.name}", "", settings.DEFAULT_FROM_EMAIL, [recipient], html_message=html_cust, fail_silently=True)

        # --- SECTION 3: THANK YOU & REVIEW REQUEST ---
        elif instance.status == 'completed' and recipient:
            review_url = f"{settings.SITE_URL}/review/{instance.id}/"
            booking_form_id = instance.booking_form.id if instance.booking_form else None
            context = {
                'customer_name': customer_name,
                'business_name': business.name,
                'review_url': review_url,
                'site_url': settings.SITE_URL,
                'booking_form_id': booking_form_id,
            }
            html_thank_you = render_to_string('bookingApp/email_thank_you_review.html', context)

            send_mail(
                subject=f"How was your appointment at {business.name}?",
                message=f"Thank you for your visit! Please leave us a review: {review_url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                html_message=html_thank_you,
                fail_silently=True
            )

    except Exception as e:
        logger.error(f"Signal Error for Appt {instance.id}: {str(e)}", exc_info=True)
# Keep your create_owner_as_staff and get_owner_gcal_link functions as they were

from datetime import datetime, timedelta, timezone as dt_timezone # Add this
from django.utils import timezone
import urllib.parse

def get_owner_gcal_link(instance):
    business = instance.booking_form.business

    if instance.customer:
        customer_id = instance.customer.username
    else:
        customer_id = f"{instance.guest_name} (Guest)"

    naive_start = datetime.combine(instance.appointment_date, instance.appointment_start_time)

    # Make it aware using the project's local timezone (SAST)
    start_local = timezone.make_aware(naive_start)
    end_local = start_local + timedelta(minutes=instance.service.default_length_minutes)

    fmt = "%Y%m%dT%H%M%SZ"

    # Use dt_timezone.utc from the standard library
    start_utc = start_local.astimezone(dt_timezone.utc).strftime(fmt)
    end_utc = end_local.astimezone(dt_timezone.utc).strftime(fmt)

    gcal_params = {
        'action': 'TEMPLATE',
        'text': f"CONFIRMED: {instance.service.name} - {customer_id}",
        'dates': f"{start_utc}/{end_utc}",
        'details': (
            f"Service: {instance.service.name}\n"
            f"Customer: {customer_id}\n"
            f"Phone: {instance.guest_phone}\n"
            f"Email: {instance.guest_email}"
        ),
        'location': business.name,
    }
    return "https://www.google.com/calendar/render?" + urllib.parse.urlencode(gcal_params)



@receiver(post_save, sender=Business)
def create_owner_as_staff(sender, instance, created, **kwargs):
    """
    Automatically adds the business owner as the first staff member.
    """
    if created:
        Staff.objects.get_or_create(
            business=instance,
            user=instance.owner,
            defaults={
                "name": instance.owner.get_full_name() or instance.owner.username,
                "role": "ADMIN",
                "email": instance.owner.email,
            }
        )

from allauth.account.signals import user_signed_up
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

@receiver(user_signed_up)
def notify_admin_allauth_signup(request, user, **kwargs):
    """
    Triggers when a user signs up via standard form OR social (Google).
    """
    # Check if a social account was used
    social_login = kwargs.get('sociallogin')
    provider = "Standard Form"
    if social_login:
        provider = social_login.account.provider.capitalize() # e.g., 'Google'

    subject = f"🚀 New Signup ({provider}): {user.username}"
    message = (
        f"A new user has registered on GetMeBooked!\n\n"
        f"Username: {user.username}\n"
        f"Email: {user.email}\n"
        f"Method: {provider}\n"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=['getmebookedinfo@gmail.com'],
        fail_silently=False  # Keep False while testing to catch errors
    )


from django.dispatch import Signal, receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# 🔔 Explicit signal
demo_completed = Signal()  # no providing_args in modern Django


@receiver(demo_completed)
def send_demo_confirmation(sender, *, email, context=None, **kwargs):
    """
    HARD-FAIL email sender.
    If this errors → request crashes.
    """

    if not email:
        raise ValueError("Email is required for demo confirmation")

    final_context = {
        'name': 'Valued Client',
        'service': 'Gents Fade & Beard Trim',
        'staff': 'Sarah',
        'time': 'Tomorrow @ 10:30 AM',
    }

    if context:
        final_context.update({k: v for k, v in context.items() if v})

    subject = f"✨ Appointment Confirmed: {final_context['service']}"
    from_email = settings.DEFAULT_FROM_EMAIL

    # 🔥 TEMPLATE MUST EXIST HERE:
    # bookingApp/templates/bookingApp/demo_confirmation.html
    html_content = render_to_string(
        'bookingApp/demo_confirmation.html',
        final_context
    )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=f"Your booking for {final_context['service']} is confirmed.",
        from_email=from_email,
        to=[email.strip()],
    )
    msg.attach_alternative(html_content, "text/html")

    # 🚨 HARD FAIL — NO SILENT MODE
    msg.send(fail_silently=False)

    logger.info(f"✅ Demo email sent to {email}")

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Appointment
from .utils import send_push_notification
@receiver(post_save, sender=Appointment)
def notify_new_appointment(sender, instance, created, **kwargs):
    if not created:
        return

    # 1. Safely identify the service name for the message
    service_name = instance.service.name if instance.service else "Service"

    # 2. Notify staff assigned to appointment
    if instance.staff and instance.staff.user:
        staff_user = instance.staff.user
        player_id = getattr(getattr(staff_user, 'profile', None), 'onesignal_player_id', None)

        if player_id:
            send_push_notification(
                [player_id],
                f"New booking: {service_name} on {instance.appointment_date}"
            )

    # 3. Notify business owner (Safely check booking_form)
    if instance.booking_form and instance.booking_form.business:
        owner = instance.booking_form.business.owner
        if owner:
            owner_player_id = getattr(getattr(owner, 'profile', None), 'onesignal_player_id', None)

            if owner_player_id:
                send_push_notification(
                    [owner_player_id],
                    f"New booking for your business: {service_name} on {instance.appointment_date}"
                )

