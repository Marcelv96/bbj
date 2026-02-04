from django import template

register = template.Library()

@register.filter
def render_email_placeholders(text, appointment):
    """
    Replaces {{ variable }} placeholders in database text with actual appointment data.
    Usage: {{ business.custom_message|render_email_placeholders:appointment }}
    """
    if not text or not appointment:
        return ""

    # Define the allowed variables map
    # We use .get() or strict attributes based on your model
    guest_name = getattr(appointment, 'guest_name', 'Guest')
    
    # Handle cases where appointment might be a dict or object
    business_name = appointment.service.business.name if hasattr(appointment, 'service') else "Us"
    service_name = appointment.service.name if hasattr(appointment, 'service') else "Service"
    
    # Format dates nicely
    date_str = appointment.appointment_date.strftime('%A, %d %B') # e.g., Monday, 25 January
    time_str = appointment.appointment_start_time.strftime('%H:%M') # e.g., 14:30

    replacements = {
        "{{ guest_name }}": guest_name,
        "{{ business_name }}": business_name,
        "{{ service_name }}": service_name,
        "{{ date }}": date_str,
        "{{ time }}": time_str,
    }

    # Perform the replacement
    output = text
    for placeholder, value in replacements.items():
        output = output.replace(placeholder, str(value))

    return output