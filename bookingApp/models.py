from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from datetime import datetime, timedelta
from django.db.models import Avg
from django.db import models
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True, null=True)
    # Preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    onesignal_player_id = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


# models.py
from django.db import models
from django.conf import settings
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill
from django.utils.crypto import get_random_string
from django.db.models import Avg

import string
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from django.db.models import Avg
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill
from django.utils import timezone

import string
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from django.utils import timezone
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill
from django.db.models import Avg

class Business(models.Model):
    INDUSTRY_CHOICES = [
        ('salon', 'Salon'),
        ('clinic', 'Clinic'),
        ('barber', 'Barber'),
    ]

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='business'
    )
    cover_image = models.ImageField(
        upload_to='business_covers/',
        blank=True,
        null=True
    )

    cover_image_webp = ImageSpecField(
        source='cover_image',
        processors=[ResizeToFill(1600, 600)],
        format='WEBP',
        options={'quality': 80}
    )

    # --- Subscription & Referral Fields ---
    subscription_end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The date when the business's access expires."
    )
    referral_code = models.CharField(
        max_length=12,
        unique=True,
        null=True,
        blank=True,
        help_text="The code this business shares to get bonuses."
    )
    referred_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referrals_made',
        help_text="The business that referred this one."
    )

    # --- UPDATED Payment & Deposit Settings ---
    payfast_merchant_id = models.CharField(max_length=50, blank=True, null=True, help_text="Your PayFast Merchant ID")
    payfast_merchant_key = models.CharField(max_length=50, blank=True, null=True, help_text="Your PayFast Merchant Key")

    DEPOSIT_TYPE_CHOICES = [
        ('fixed', 'Fixed Amount (R)'),
        ('percentage', 'Percentage (%)'),
    ]

    deposit_type = models.CharField(
        max_length=10,
        choices=DEPOSIT_TYPE_CHOICES,
        default='fixed',
        help_text="Choose how the deposit is calculated."
    )

    deposit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Fixed amount (e.g. 50.00). Used if Deposit Type is 'Fixed'."
    )

    deposit_percentage = models.PositiveIntegerField(
        default=50,
        help_text="Percentage of service price (e.g. 50). Used if Deposit Type is 'Percentage'."
    )

    reschedule_window_hours = models.PositiveIntegerField(
        default=24,
        help_text="Hours before appointment when deposit becomes non-refundable."
    )

    deposit_policy = models.TextField(blank=True, null=True, help_text="Rules for deposits")

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    industry = models.CharField(max_length=20, choices=INDUSTRY_CHOICES, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    # --- Social Fields ---
    instagram_url = models.URLField(max_length=500, blank=True, null=True)
    facebook_url = models.URLField(max_length=500, blank=True, null=True)
    twitter_url = models.URLField(max_length=500, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    join_code = models.CharField(max_length=12, unique=True, null=True, blank=True)

    def save(self, *args, **kwargs):
        # 1. Handle Slug Generation
        if not self.slug:
            self.slug = slugify(self.name)

        # Ensure slug uniqueness
        original_slug = self.slug
        queryset = Business.objects.all()
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)

        counter = 1
        while queryset.filter(slug=self.slug).exists():
            self.slug = f"{original_slug}-{counter}"
            counter += 1

        # 2. Handle Random Join Code Generation (Staff)
        if not self.join_code:
            self.join_code = self.generate_unique_code('join_code')

        # 3. Handle Random Referral Code Generation (Sharing)
        if not self.referral_code:
            self.referral_code = self.generate_unique_code('referral_code')

        super().save(*args, **kwargs)

    # models.py inside the Business class

    def is_deposit_required_for_client(self, email):
        """
        Checks if a deposit is required, unless the client is marked as exempt.
        """
        # 1. Check if the business even requires deposits globally
        if not self.deposit_required:
            return False

        # 2. Check if this specific client is exempt
        from .models import ClientProfile
        client = ClientProfile.objects.filter(business=self, email=email).first()
        if client and client.deposit_exempt:
            return False

        return True

    def generate_unique_code(self, field_name):
        """Helper to ensure the random string isn't already in use for a specific field."""
        while True:
            code = get_random_string(8, allowed_chars=string.ascii_uppercase + string.digits)
            filter_kwargs = {field_name: code}
            if not Business.objects.filter(**filter_kwargs).exists():
                return code

    @property
    def deposit_required(self):
        has_creds = all([self.payfast_merchant_id, self.payfast_merchant_key])
        if not has_creds:
            return False

        if self.deposit_type == 'percentage':
            return self.deposit_percentage > 0
        else:
            return self.deposit_amount > 0

    @property
    def average_rating(self):
        avg = self.reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 0.0

    @property
    def review_count(self):
        return self.reviews.count()

    @property
    def is_active(self):
        if not self.subscription_end_date:
            return False
        return self.subscription_end_date > timezone.now()

    @property
    def days_remaining(self):
        if not self.subscription_end_date:
            return 0
        delta = self.subscription_end_date - timezone.now()
        return max(0, delta.days)

    def get_absolute_url(self):
        return f"/business/{self.id}/"

    def __str__(self):
        return self.name


# models.py

class Staff(models.Model):
    ROLE_CHOICES = [
        ('STAFF', 'Staff'),
        ('ADMIN', 'Admin/Co-Owner'),
    ]

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='staff_members')
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='staff_profile'
    )
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='STAFF') # New field
    email = models.EmailField(blank=True, null=True)
    services = models.ManyToManyField('Service', related_name='staff_members', blank=True)

    def __str__(self):
        return f"{self.name} ({self.role}) @ {self.business.name}"

class StaffOperatingHours(models.Model):
    DAY_TYPE_CHOICES = [
        ('mon_fri', 'Monday to Friday'),
        ('sat', 'Saturday'),
        ('sun', 'Sunday'),
    ]
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='work_hours')
    day_type = models.CharField(max_length=10, choices=DAY_TYPE_CHOICES)
    open_time = models.TimeField()
    close_time = models.TimeField()

    class Meta:
        unique_together = ('staff', 'day_type')


# Services offered by a business
class Service(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    default_length_minutes = models.PositiveIntegerField(default=30)
    price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)  # optional

    buffer_minutes = models.PositiveIntegerField(default=15, help_text="Buffer time after appointment")

    capacity = models.PositiveIntegerField(
        default=1, null=True, blank=True,
        help_text="Maximum number of attendees allowed for this service session."
    )

    # Optional: Calculate total time occupied
    @property
    def total_occupied_minutes(self):
        return self.duration_minutes + self.buffer_minutes

    def __str__(self):
        return f"{self.name} ({self.business.name})"


# Booking form configuration per business
class BookingForm(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='booking_forms')
    name = models.CharField(max_length=255, default="Main Booking Form")
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    embed_token = models.CharField(max_length=32, unique=True, editable=False)

    def save(self, *args, **kwargs):
        # Generate a unique embed token
        if not self.embed_token:
            token = get_random_string(length=32)
            while BookingForm.objects.filter(embed_token=token).exists():
                token = get_random_string(length=32)
            self.embed_token = token
        super().save(*args, **kwargs)

    def get_embed_js_snippet(self):
        return f'<script src="https://example.com/embed/{self.embed_token}/book.js"></script>'

    def __str__(self):
        return f"{self.name} ({self.business.name})"


import uuid
import re
from datetime import datetime, timedelta
from django.db import models
from django.conf import settings
from django.utils.http import urlencode

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('declined', 'Declined'),
        ('rescheduled', 'Rescheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    booking_form = models.ForeignKey('BookingForm', on_delete=models.CASCADE, related_name='appointments', null=True, blank=True)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='appointments', null=True, blank=True)

    deposit_paid = models.BooleanField(default=False)
    amount_to_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payfast_reference = models.CharField(max_length=100, blank=True, null=True)

    reminder_24h_sent = models.BooleanField(default=False)
    reminder_2h_sent = models.BooleanField(default=False)

    # Guest details for manual bookings
    guest_name = models.CharField(max_length=255, blank=True, null=True)
    guest_phone = models.CharField(max_length=20, blank=True, null=True)
    guest_email = models.EmailField(blank=True, null=True)
    attendees = models.PositiveIntegerField(default=1, blank=True, null=True)

    service = models.ForeignKey('Service', on_delete=models.SET_NULL, null=True)
    staff = models.ForeignKey('Staff', on_delete=models.CASCADE, related_name='appointments', null=True, blank=True)
    length_minutes = models.PositiveIntegerField(editable=False)

    appointment_date = models.DateField()
    appointment_start_time = models.TimeField()
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    reschedule_token = models.CharField(
        max_length=100,
        unique=True,
        default=uuid.uuid4,
        editable=False
    )

    class Meta:
        ordering = ['-appointment_date', '-appointment_start_time']

    # --- WhatsApp Logic ---
    @property
    def formatted_whatsapp_number(self):
        """Returns a clean digits-only number starting with 27"""
        # 1. Fallback chain: Check Customer User profile, then Guest field
        raw_phone = None
        if self.customer and hasattr(self.customer, 'phone'):
            raw_phone = self.customer.phone

        if not raw_phone:
            raw_phone = self.guest_phone

        if not raw_phone:
            return None

        # 2. Clean all non-numeric characters (removes +, spaces, dashes)
        clean_number = re.sub(r'\D', '', str(raw_phone))

        # 3. Handle SA Local format (082...) -> (2782...)
        if clean_number.startswith('0'):
            clean_number = f"27{clean_number[1:]}"

        return clean_number

    @property
    def whatsapp_link(self):
        """Returns the full wa.me URL with an optional pre-filled message"""
        number = self.formatted_whatsapp_number
        if not number:
            return None

        # Optional: Add a pre-filled message
        name = self.guest_name or (self.customer.get_full_name() if self.customer else "Customer")
        message = f"Hi {name}, regarding your appointment on {self.appointment_date}:"
        params = urlencode({'text': message})

        return f"https://wa.me/{number}?{params}"

    # --- Existing Logic ---
    @property
    def end_time(self):
        start_dt = datetime.combine(self.appointment_date, self.appointment_start_time)
        return (start_dt + timedelta(minutes=self.length_minutes)).time()

    def save(self, *args, **kwargs):
        if not self.reschedule_token:
            self.reschedule_token = str(uuid.uuid4())

        if self.service:
            self.length_minutes = self.service.default_length_minutes
        else:
            self.length_minutes = 30

        super().save(*args, **kwargs)

    def __str__(self):
        display_name = "Guest"
        if self.customer:
            display_name = self.customer.username
        elif self.guest_name:
            display_name = self.guest_name

        service_name = self.service.name if self.service else 'No Service'
        return f"{display_name} - {service_name} ({self.appointment_date})"
# models.py

class OperatingHours(models.Model):
    DAY_TYPE_CHOICES = [
        ('mon_fri', 'Monday to Friday'),
        ('sat', 'Saturday'),
        ('sun', 'Sunday'),
    ]

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='operating_hours')
    day_type = models.CharField(max_length=10, choices=DAY_TYPE_CHOICES)
    open_time = models.TimeField()
    close_time = models.TimeField()

    class Meta:
        unique_together = ('business', 'day_type')

class BusinessBlock(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='blocks')
    block_date = models.DateField()
    reason = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ('business', 'block_date')
        ordering = ['block_date']

    def __str__(self):
        return f"{self.business.name} closed on {self.block_date}"

# Add to models.py

class SavedBusiness(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_businesses')
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'business') # Prevents double liking

class Review(models.Model):
    RATING_CHOICES = [(i, f"{i} Stars") for i in range(1, 6)]

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='reviews')
    # Made null=True and SET_NULL so reviews persist even if a user is deleted,
    # and to allow guest reviews where no user account exists.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # New fields for the guest system
    guest_name = models.CharField(max_length=255, blank=True, null=True)
    appointment = models.OneToOneField(
        'Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='review'
    )

    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, default=5)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # We use the appointment OneToOneField to enforce one review per booking
        ordering = ['-created_at']

    def __str__(self):
        reviewer = self.user.username if self.user else self.guest_name
        return f"{reviewer} - {self.business.name} ({self.rating})"


from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Business, BookingForm # Ensure BookingForm is imported

@receiver(post_save, sender=Business)
def create_business_booking_form(sender, instance, created, **kwargs):
    """
    Automatically creates a default BookingForm whenever a new Business is created.
    """
    if created:
        # We only set the business; name and embed_token have defaults/auto-logic
        BookingForm.objects.create(
            business=instance,
            name=f"Booking Form - {instance.name}"
        )

class StaffBlock(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='blocks')
    block_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.CharField(max_length=255, blank=True)

    def __str__(self):
        # Use 'self.staff' to access the field on the model instance
        # Also, ensure you use the correct field for the name (e.g., self.staff.user.username)
        return f"Block for {self.staff} on {self.block_date}"

# models.py
from django.db import models

class DemoLead(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, blank=True)
    service = models.CharField(max_length=255, blank=True)
    staff = models.CharField(max_length=255, blank=True)
    time = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

from django.db import models
from django.conf import settings
from django.db.models import Sum, Count, Q
from django.db.models.signals import post_save
from django.dispatch import receiver

class ClientProfile(models.Model):
    business = models.ForeignKey('Business', on_delete=models.CASCADE, related_name='clients')
    name = models.CharField(max_length=255)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deposit_exempt = models.BooleanField(
        default=False,
        help_text="If checked, this client can book without paying a deposit."
    )

    class Meta:
        unique_together = ('business', 'email')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.business.name}"

    def get_appointments(self):
        """Standardizes finding all appointments for this client email at this business."""
        from .models import Appointment
        return Appointment.objects.filter(
            Q(guest_email=self.email) | Q(customer__email=self.email),
            service__business=self.business
        )

    @property
    def appointment_count(self):
        return self.get_appointments().count()

    @property
    def total_spent(self):
        return self.get_appointments().aggregate(total=Sum('amount_to_pay'))['total'] or 0.00

    @property
    def last_service(self):
        apt = self.get_appointments().order_by('-appointment_date', '-appointment_start_time').first()
        return apt.service.name if apt and apt.service else "N/A"

    @property
    def most_selected_service(self):
        service_counts = self.get_appointments().values('service__name').annotate(
            count=Count('service')
        ).order_by('-count').first()
        return service_counts['service__name'] if service_counts else "N/A"

# Signal to automatically build the client list
@receiver(post_save, sender='bookingApp.Appointment') # Use string name if Appointment is defined later
def sync_client_profile(sender, instance, created, **kwargs):
    if created and instance.service:
        business = instance.service.business
        email = instance.guest_email or (instance.customer.email if instance.customer else None)

        if email:
            from .models import ClientProfile
            ClientProfile.objects.get_or_create(
                business=business,
                email=email,
                defaults={
                    'name': instance.guest_name or (instance.customer.get_full_name() if instance.customer else instance.customer.username if instance.customer else "Guest"),
                    'phone': instance.guest_phone or (getattr(instance.customer.profile, 'phone_number', '') if instance.customer else ''),
                    'user': instance.customer
                }
            )