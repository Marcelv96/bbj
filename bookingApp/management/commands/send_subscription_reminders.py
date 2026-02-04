import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

# Import your Business model
from bookingApp.models import Business 

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sends subscription expiration reminders: 2 days prior and on the day of expiration.'

    def handle(self, *args, **options):
        # 1. Setup Dates
        now = timezone.now()
        today = now.date()
        date_in_2_days = today + timedelta(days=2)

        self.stdout.write(f"Running subscription checks for {today}...")

        # ==========================================
        # SCENARIO A: 2 Days Before Expiration
        # ==========================================
        # Finds businesses where the end date is exactly 2 days from now
        businesses_2_days = Business.objects.filter(
            subscription_end_date__date=date_in_2_days,
            owner__email__isnull=False
        ).select_related('owner')

        count_2_days = 0
        for biz in businesses_2_days:
            if self.send_reminder_email(biz, days_left=2):
                count_2_days += 1

        if count_2_days > 0:
            self.stdout.write(self.style.SUCCESS(f"Sent '2 Days Left' reminders to {count_2_days} businesses."))
        else:
            self.stdout.write("No businesses found expiring in 2 days.")

        # ==========================================
        # SCENARIO B: Morning of Expiration (Today)
        # ==========================================
        # Finds businesses where the end date is today
        businesses_expiring_today = Business.objects.filter(
            subscription_end_date__date=today,
            owner__email__isnull=False
        ).select_related('owner')

        count_today = 0
        for biz in businesses_expiring_today:
            if self.send_reminder_email(biz, days_left=0):
                count_today += 1

        if count_today > 0:
            self.stdout.write(self.style.SUCCESS(f"Sent 'Expiring Today' reminders to {count_today} businesses."))
        else:
            self.stdout.write("No businesses found expiring today.")

    def send_reminder_email(self, business, days_left):
        """
        Renders the HTML template and sends the multi-part email.
        """
        try:
            # Construct renewal URL (make sure SITE_URL is in your settings.py)
            site_url = getattr(settings, 'SITE_URL', 'https://getmebooked.co.za')
            renew_url = f"{site_url}/business/{business.id}/owner/dashboard/"
            
            context = {
                'owner_name': business.owner.first_name or business.owner.username,
                'business_name': business.name,
                'renew_url': renew_url,
            }

            # Determine Template and Subject
            if days_left == 0:
                subject = f"⚠️ ACTION REQUIRED: {business.name} Expires Today"
                template_name = 'bookingApp/subscription_expired_today.html'
            else:
                subject = f"Reminder: {business.name} Subscription Reminder"
                template_name = 'bookingApp/subscription_reminder_2_days.html'

            # Render HTML and create plain-text fallback
            html_content = render_to_string(template_name, context)
            text_content = strip_tags(html_content)

            # Build the email
            msg = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [business.owner.email]
            )
            msg.attach_alternative(html_content, "text/html")
            
            # Send
            msg.send(fail_silently=False)
            return True

        except Exception as e:
            logger.error(f"Error sending email to {business.name}: {e}")
            self.stdout.write(self.style.ERROR(f"Failed to send to {business.name}: {e}"))
            return False