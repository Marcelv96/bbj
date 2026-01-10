from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Profile, Business, Service, Staff, BookingForm, Appointment, ClientProfile
from django.contrib import admin
from .models import SavedBusiness, Review
# admin.py
from django.contrib import admin
from .models import DemoLead

admin.site.register(ClientProfile)

@admin.register(DemoLead)
class DemoLeadAdmin(admin.ModelAdmin):
    list_display = ('email', 'service', 'staff', 'created_at')
    search_fields = ('email', 'name')
    list_filter = ('created_at',)


@admin.register(SavedBusiness)
class SavedBusinessAdmin(admin.ModelAdmin):
    list_display = ('user', 'business', 'created_at')
    list_filter = ('created_at', 'business')
    search_fields = ('user__username', 'business__name')
    readonly_fields = ('created_at',)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('business', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at', 'business')
    search_fields = ('user__username', 'business__name', 'comment')
    # This allows you to edit the rating and comment directly in the list view
    list_editable = ('rating',)
    readonly_fields = ('created_at', 'updated_at')

    # Organizes the detail view in the admin
    fieldsets = (
        (None, {
            'fields': ('business', 'user')
        }),
        ('Content', {
            'fields': ('rating', 'comment')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

# Inline admin descriptor for Profile model linked to User
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'profile'


# Extend User admin to include Profile inline
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)


# Unregister the default User admin and register the new one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# admin.py
from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    # ERROR CAUSE: 'is_business_owner' is missing from the Profile model
    # list_display = ['user', 'is_business_owner', 'phone_number']

    # FIXED: Use existing fields from your Profile model
    list_display = ['user', 'phone_number', 'email_notifications']
    search_fields = ['user__username', 'phone_number']


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'slug', 'created_at', 'payfast_merchant_id', 'payfast_merchant_key')
    list_filter = ('created_at',)
    search_fields = ('name', 'owner__username')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'business', 'default_length_minutes', 'price')
    list_filter = ('business',)
    search_fields = ('name', 'business__name')


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('name', 'business', 'email')
    list_filter = ('business',)
    search_fields = ('name', 'business__name')


@admin.register(BookingForm)
class BookingFormAdmin(admin.ModelAdmin):
    list_display = ('name', 'business', 'embed_token', 'created_at')
    list_filter = ('created_at', 'business')
    search_fields = ('name', 'business__name', 'embed_token')


from django.contrib import admin
from .models import Appointment

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    # Changed 'confirmed' to 'status'
    list_display = ('id', 'customer', 'booking_form', 'service', 'staff', 'appointment_date', 'appointment_start_time', 'status')
    # Filter by the new status choices
    list_filter = ('status', 'appointment_date', 'booking_form')
    search_fields = ('customer__username', 'booking_form__business__name', 'service__name')
    date_hierarchy = 'appointment_date'

    # Optional: Make it easy to change status directly from the list view
    list_editable = ('status',)