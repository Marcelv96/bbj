from django.core.management.base import BaseCommand
from bookingApp.utils import trigger_pending_reminders
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Send appointment reminders (24h and 2h) and run auto-complete logic."

    def add_arguments(self, parser):
        parser.add_argument('--window', type=int, default=5, help='Window size in minutes (default 5)')

    def handle(self, *args, **options):
        window = options['window']
        logger.info("Running trigger_pending_reminders with window %s minutes", window)
        try:
            trigger_pending_reminders(window_minutes=window)
            logger.info("trigger_pending_reminders completed")
        except Exception as e:
            logger.exception("trigger_pending_reminders failed: %s", e)
            raise