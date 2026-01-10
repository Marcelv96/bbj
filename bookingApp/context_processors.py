# bookingApp/context_processors.py
from .models import Appointment, Staff

def pending_appointments_count(request):
    if not request.user.is_authenticated:
        return {'pending_count': 0, 'pending_staff_count': 0}

    # Count as Owner
    biz_count = 0
    if hasattr(request.user, 'business'):
        biz_count = Appointment.objects.filter(booking_form__business=request.user.business, status='pending').count()

    # Count as Staff/Admin
    staff_count = 0
    if hasattr(request.user, 'staff_profile'):
        staff_count = Appointment.objects.filter(booking_form__business=request.user.staff_profile.business, status='pending').count()

    return {
        'pending_count': biz_count,
        'pending_staff_count': staff_count
    }