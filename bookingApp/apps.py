# bookingApp/apps.py
from django.apps import AppConfig

class BookingAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bookingApp'

    def ready(self):
        import bookingApp.signals  # import your signal handlers here
