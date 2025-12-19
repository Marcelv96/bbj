from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Appointment
from datetime import datetime, timedelta
import urllib.parse

@receiver(post_save, sender=Appointment)
def notify_owner_new_booking(sender, instance, created, **kwargs):
    """Sends an email to the owner when a NEW appointment is created."""
    if created:
        business = instance.booking_form.business
        subject = f"New Appointment Request: {instance.service.name}"
        
        context = {
            'appointment': instance,
            'owner': business.owner,
            'site_url': settings.SITE_URL,
        }
        
        html_message = render_to_string('bookingApp/owner_notification.html', context)
        
        try:
            send_mail(
                subject,
                f"New booking from {instance.customer.username}",
                settings.DEFAULT_FROM_EMAIL,
                [business.owner.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            print(f"SMTP Error notifying owner: {e}")

@receiver(post_save, sender=Appointment)
def notify_customer_on_status_change(sender, instance, created, **kwargs):
    """Sends a detailed confirmation email to the customer when confirmed or declined."""
    if not created and instance.status in ['confirmed', 'declined']:
        business = instance.booking_form.business
        subject = f"Update on your Appointment: {instance.status.title()}"
        
        gcal_link = None
        if instance.status == 'confirmed':
            # Calculate times for the calendar event
            start_dt = datetime.combine(instance.appointment_date, instance.appointment_start_time)
            duration = getattr(instance, 'length_minutes', instance.service.default_length_minutes)
            end_dt = start_dt + timedelta(minutes=duration)
            
            # Google Calendar time format: YYYYMMDDTHHMMSSZ
            fmt = "%Y%m%dT%H%M%SZ"
            dates = f"{start_dt.strftime(fmt)}/{end_dt.strftime(fmt)}"
            
            # Detailed Description for the Customer's Calendar entry
            description = (
                f"✅ APPOINTMENT CONFIRMED\n\n"
                f"Service: {instance.service.name}\n"
                f"Staff: {instance.staff.name if instance.staff else 'Any Professional'}\n"
                f"Location: {business.name}\n\n"
                f"Notes: {instance.notes if instance.notes else 'None'}\n\n"
                
            )
            
            params = {
                'action': 'TEMPLATE',
                'text': f"{instance.service.name} @ {business.name}",
                'dates': dates,
                'details': description,
                'location': business.name,
                'trp': 'false',
            }
            gcal_link = "https://www.google.com/calendar/render?" + urllib.parse.urlencode(params)

        context = {
            'appointment': instance,
            'business': business,
            'status': instance.status,
            'site_url': settings.SITE_URL,
            'gcal_link': gcal_link,
        }
        
        html_message = render_to_string('bookingApp/customer_status_update.html', context)
        
        try:
            send_mail(
                subject,
                f"Your appointment is {instance.status}.",
                settings.DEFAULT_FROM_EMAIL,
                [instance.customer.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            print(f"SMTP Error: {e}")

def get_owner_gcal_link(instance):
    """Generates the high-detail Google Calendar link for the Business Owner."""
    business = instance.booking_form.business
    start_dt = datetime.combine(instance.appointment_date, instance.appointment_start_time)
    duration = getattr(instance, 'length_minutes', instance.service.default_length_minutes)
    end_dt = start_dt + timedelta(minutes=duration)
    
    fmt = "%Y%m%dT%H%M%SZ"
    dates = f"{start_dt.strftime(fmt)}/{end_dt.strftime(fmt)}"
    
    # This block ensures the owner sees Service, Time, Staff, and Notes
    details = (
        f"📌 SERVICE: {instance.service.name}\n"
        f"⏰ DURATION: {duration} min\n"
        f"👤 CUSTOMER: {instance.customer.username}\n"
        f"👔 STAFF: {instance.staff.name if instance.staff else 'Not Assigned'}\n"
        f"--------------------------\n"
        f"📝 NOTES: {instance.notes if instance.notes else 'No notes'}"
    )
    
    params = {
        'action': 'TEMPLATE',
        'text': f"CONFIRMED: {instance.customer.username} - {instance.service.name}",
        'dates': dates,
        'details': details,
        'location': business.name,
    }
    return "https://www.google.com/calendar/render?" + urllib.parse.urlencode(params)