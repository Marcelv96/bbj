from django.shortcuts import redirect
from django.urls import reverse

class StaffActiveMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        # URLs that are ALWAYS allowed (Notice page and Profile page)
        allowed_urls = [
            reverse('staff_deactivated'),
            reverse('profile'),
            reverse('user_guide'),
            reverse('logout'), # Always allow logout
        ]

        if hasattr(request.user, 'staff_profile'):
            staff = request.user.staff_profile

            # If they are inactive and NOT trying to access an allowed page
            if not staff.is_active and request.path not in allowed_urls:
                return redirect('staff_deactivated')

        return self.get_response(request)

from .models import VisitorLog

from .models import VisitorLog

class VisitorTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # STRICT CHECK: Only log if the path is exactly '/'
        # This ignores /admin/, /api/, and business-specific slugs
        if request.path == "/" and request.method == "GET":

            # Ensure session exists to track the user across the site later
            if not request.session.session_key:
                request.session.create()

            VisitorLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                path=request.path,
                referer=request.META.get('HTTP_REFERER')
            )

        return self.get_response(request)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')


from django.utils import timezone
from datetime import timedelta
from .models import Business

