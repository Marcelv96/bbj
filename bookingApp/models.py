from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from django.urls import reverse
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils.crypto import get_random_string

# CRITICAL IMPORTS FOR TIME CALCULATION
from datetime import datetime, timedelta
from django.utils import timezone

# Profile model to extend User with business owner flag and extra info
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    is_business_owner = models.BooleanField(default=False)
    # Other profile fields if needed, e.g. phone, avatar

    def __str__(self):
        return f"{self.user.username} Profile"


# Business / Salon owned by a user (business owner)
from django.db import models
from django.conf import settings
from django.utils.text import slugify

class Business(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='businesses')
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, help_text="Used for mini subdomain")
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            num = 1
            while Business.objects.filter(slug=slug).exists():
                slug = f"{base_slug}{num}"
                num += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_subdomain_url(self):
        return f"https://{self.slug}.example.com"

    def __str__(self):
        return self.name


# Staff members of a business
class Staff(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='staff_members')
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    # Add phone or other info as needed

    def __str__(self):
        return f"{self.name} ({self.business.name})"


# Services offered by the business
class Service(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    default_length_minutes = models.PositiveIntegerField(default=30)
    price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)  # optional

    def __str__(self):
        return f"{self.name} ({self.business.name})"


# Booking form per business - this could represent a customizable form
class BookingForm(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='booking_forms')
    name = models.CharField(max_length=255, default="Main Booking Form")
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Unique token for embedding JavaScript snippet on external sites
    embed_token = models.CharField(max_length=32, unique=True, editable=False)

    def save(self, *args, **kwargs):
        if not self.embed_token:
            # Generate a unique token for embedding JS snippet
            token = get_random_string(length=32)
            while BookingForm.objects.filter(embed_token=token).exists():
                token = get_random_string(length=32)
            self.embed_token = token
        super().save(*args, **kwargs)

    def get_embed_js_snippet(self):
        # Returns JavaScript snippet string that the business owner can embed on their own website
        return f'<script src="https://example.com/embed/{self.embed_token}.js"></script>'

    def __str__(self):
        return f"{self.name} ({self.business.name})"


from django.conf import settings
from django.db import models
from django.utils.crypto import get_random_string

# ... (Profile, Business, Staff, Service, BookingForm models remain as previously defined)

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('declined', 'Declined'),
        ('reschedule_requested', 'Reschedule Requested'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    booking_form = models.ForeignKey(BookingForm, on_delete=models.CASCADE, related_name='appointments')
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='appointments')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True)
    staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True)
    
    # editable=False ensures this doesn't appear in user-facing forms
    length_minutes = models.PositiveIntegerField(editable=False) 
    
    appointment_date = models.DateField()
    appointment_start_time = models.TimeField()
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-appointment_date', '-appointment_start_time']

    def save(self, *args, **kwargs):
        # Enforce business-defined service duration
        if self.service:
            self.length_minutes = self.service.default_length_minutes
        super().save(*args, **kwargs)

    @property
    def end_time(self):
        """Helper to show end time in dashboards and receipts"""
        start_dt = datetime.combine(self.appointment_date, self.appointment_start_time)
        return (start_dt + timedelta(minutes=self.length_minutes)).time()

    def __str__(self):
        return f"{self.customer.username} - {self.service.name if self.service else 'Service'}"