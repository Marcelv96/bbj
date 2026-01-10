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
        if created and instance.status == 'pending':
            if not business.deposit_required:
                context = {
                    'appointment': instance,
                    'business': business,
                    'owner': owner,
                    'customer_name': customer_name,
                    'site_url': settings.SITE_URL, # Ensure this is passed
                }
                html_owner = render_to_string('bookingApp/owner_notification.html', context)
                send_mail(
                    subject=f"New Request: {instance.service.name} - {customer_name}",
                    message=f"New booking request from {customer_name}.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[owner.email],
                    html_message=html_owner,
                    fail_silently=True
                )
            else:
                logger.info(f"Appt {instance.id} created. Skipping owner notification (Awaiting Deposit).")

        # --- SECTION 2: STATUS UPDATES ---
        if instance.status == 'cancelled':
            # Notify Owner
            context_owner = {
                'appointment': instance,
                'customer_name': customer_name,
                'site_url': settings.SITE_URL
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
                send_mail("Booking Update: Cancelled", "", settings.DEFAULT_FROM_EMAIL, [recipient], html_message=html_declined, fail_silently=True)

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

                pf_common = ""
                for k, v in pf_params:
                    pf_common += f"{k}={urllib.parse.quote_plus(str(v).strip())}&"

                pf_string = pf_common + "passphrase=VanWyknBake420"
                sig = hashlib.md5(pf_string.encode()).hexdigest()

                final_params = dict(pf_params)
                final_params['signature'] = sig
                payfast_url = "https://www.payfast.co.za/eng/process?" + urllib.parse.urlencode(final_params)

            # --- KEY FIX HERE ---
            context = {
                'appointment': instance,
                'business': business,
                'gcal_link': gcal_link,
                'payfast_url': payfast_url,
                'site_url': settings.SITE_URL, # <--- This fixes the reschedule button
            }

            html_cust = render_to_string('bookingApp/customer_status_update.html', context)
            send_mail(f"Confirmed: {instance.service.name}", "", settings.DEFAULT_FROM_EMAIL, [recipient], html_message=html_cust, fail_silently=True)

        # --- SECTION 3: THANK YOU & REVIEW REQUEST ---
        elif instance.status == 'completed' and recipient:
            review_url = f"{settings.SITE_URL}/review/{instance.id}/"
            context = {
                'customer_name': customer_name,
                'business_name': business.name,
                'review_url': review_url,
                'site_url': settings.SITE_URL,
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

def get_owner_gcal_link(instance):
    """
    Safely generates a GCal link for the owner,
    handling both Registered Customers and Guests.
    """
    business = instance.booking_form.business

    # --- FIX START ---
    # Check if registered customer exists, otherwise use guest name
    if instance.customer:
        customer_id = instance.customer.username
    else:
        customer_id = f"{instance.guest_name} (Guest)"
    # --- FIX END ---

    start_dt = datetime.combine(instance.appointment_date, instance.appointment_start_time)
    end_dt = start_dt + timedelta(minutes=instance.service.default_length_minutes)
    fmt = "%Y%m%dT%H%M%SZ"

    gcal_params = {
        'action': 'TEMPLATE',
        'text': f"CONFIRMED: {instance.service.name} - {customer_id}",
        'dates': f"{start_dt.strftime(fmt)}/{end_dt.strftime(fmt)}",
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


from django.dispatch import receiver, Signal
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

# Set up logging to see errors in your console/logs
logger = logging.getLogger(__name__)

demo_completed = Signal()

@receiver(demo_completed)
def send_demo_confirmation(sender, email, context=None, **kwargs):
    if not email:
        return

    final_context = {
        'name': 'Valued Client',
        'service': 'Gents Fade & Beard Trim',
        'staff': 'Sarah',
        'time': 'Tomorrow @ 10:30 AM'
    }

    if context:
        clean_context = {k: v for k, v in context.items() if v}
        final_context.update(clean_context)

    subject = f"✨ Appointment Confirmed: {final_context['service']}"
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'webmaster@localhost')

    try:
        html_content = render_to_string('bookingApp/demo_confirmation.html', final_context)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=f"Your booking for {final_context['service']} is confirmed!",
            from_email=from_email,
            to=[email.strip()] # Strip whitespace from email
        )
        msg.attach_alternative(html_content, "text/html")

        # fail_silently=False helps us see errors during development
        msg.send(fail_silently=False)
        print(f"✅ Email successfully sent to {email}")

    except Exception as e:
        logger.error(f"❌ Failed to send demo email to {email}: {str(e)}")
        # If this is for a demo/portfolio, we don't want to crash the whole view

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Appointment
from .utils import send_push_notification

@receiver(post_save, sender=Appointment)
def notify_new_appointment(sender, instance, created, **kwargs):
    if created:
        # Notify staff assigned to appointment
        staff_user = instance.staff.user if instance.staff else None
        if staff_user and hasattr(staff_user, 'profile') and staff_user.profile.onesignal_player_id:
            send_push_notification(
                [staff_user.profile.onesignal_player_id],
                f"New booking: {instance.service.name if instance.service else 'Service'} on {instance.appointment_date}"
            )

        # Optionally notify business owner
        owner = instance.booking_form.business.owner
        if owner and hasattr(owner, 'profile') and owner.profile.onesignal_player_id:
            send_push_notification(
                [owner.profile.onesignal_player_id],
                f"New booking for your business: {instance.service.name if instance.service else 'Service'} on {instance.appointment_date}"
            )
