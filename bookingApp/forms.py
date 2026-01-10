from django import forms
from .models import Business, BookingForm, Appointment, Service, Staff

from django import forms
from .models import Business

from django.contrib.auth.decorators import login_required
from django import forms
from .models import Business, OperatingHours

from django import forms
from .models import Business
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
# In forms.py
from allauth.account.forms import ResetPasswordForm

from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import get_user_model

from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import get_user_model

class FlexiblePasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        """Finds the user even if they have a Google-linked account."""
        active_users = get_user_model()._default_manager.filter(
            email__iexact=email, is_active=True
        )
        return active_users


class StaffServicesForm(forms.ModelForm):
    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False
    )

    class Meta:
        model = Staff
        fields = ['services']

    def __init__(self, *args, **kwargs):
        business = kwargs.pop('business', None)
        super().__init__(*args, **kwargs)
        if business:
            # Only show services belonging to this specific business
            self.fields['services'].queryset = Service.objects.filter(business=business)

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class BusinessForm(forms.ModelForm):
    mon_fri_open = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        label="Monday to Friday Open Time"
    )
    mon_fri_close = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        label="Monday to Friday Close Time"
    )

    sat_open = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        label="Saturday Open Time"
    )
    sat_close = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        label="Saturday Close Time"
    )

    sun_open = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        label="Sunday Open Time"
    )
    sun_close = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        label="Sunday Close Time"
    )

    class Meta:
        model = Business
        fields = [
            'name',
            'cover_image',
            'industry',
            'address',
            'contact_number',
            'description',
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Business name'
            }),
            'cover_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'industry': forms.Select(attrs={
                'class': 'form-select'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Physical address'
            }),
            'contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contact number'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell customers about your business'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            oh = {oh.day_type: oh for oh in self.instance.operating_hours.all()}

            if 'mon_fri' in oh:
                self.fields['mon_fri_open'].initial = oh['mon_fri'].open_time
                self.fields['mon_fri_close'].initial = oh['mon_fri'].close_time
            if 'sat' in oh:
                self.fields['sat_open'].initial = oh['sat'].open_time
                self.fields['sat_close'].initial = oh['sat'].close_time
            if 'sun' in oh:
                self.fields['sun_open'].initial = oh['sun'].open_time
                self.fields['sun_close'].initial = oh['sun'].close_time

    def save(self, commit=True):
        # Only save the Business instance here, no OperatingHours logic
        business = super().save(commit=commit)
        return business





class BookingFormForm(forms.ModelForm):
    class Meta:
        model = BookingForm
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'description', 'default_length_minutes', 'price']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'default_length_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = ['name', 'email']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

from django import forms
from django.forms import inlineformset_factory
from .models import Business, Staff, Service, BookingForm, OperatingHours

from django import forms
from django.forms import inlineformset_factory
from .models import Business, Staff, Service

# forms.py
from django import forms
from .models import Business

class BusinessOnboardingForm(forms.ModelForm):
    # Referral Field
    referral_code_input = forms.CharField(
        required=False,
        label="Referral Code",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter code for 30 days bonus'})
    )

    # Operating Hours Fields
    mon_fri_open = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}))
    mon_fri_close = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}))
    sat_open = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}))
    sat_close = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}))
    sun_open = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}))
    sun_close = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}))

    # Social Links Fields
    instagram_url = forms.URLField(required=False, widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://instagram.com/yourpage'}))
    facebook_url = forms.URLField(required=False, widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://facebook.com/yourpage'}))
    twitter_url = forms.URLField(required=False, widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://twitter.com/yourpage'}))

    class Meta:
        model = Business
        fields = [
            'name', 'industry', 'address', 'contact_number', 'description',
            'cover_image', 'instagram_url', 'facebook_url', 'twitter_url'
        ]
        widgets = {
            field: forms.TextInput(attrs={'class': 'form-control'}) for field in ['name', 'address', 'contact_number']
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].widget = forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        self.fields['industry'].widget.attrs.update({'class': 'form-select'})
# --- FORMSETS (Required for your View imports) ---

StaffFormSet = inlineformset_factory(
    Business, Staff,
    fields=['name', 'email'],
    extra=1,
    can_delete=True,
    widgets={
        'name': forms.TextInput(attrs={'class': 'form-control'}),
        'email': forms.EmailInput(attrs={'class': 'form-control'})
    }
)

ServiceFormSet = inlineformset_factory(
    Business, Service,
    fields=['name', 'price', 'default_length_minutes'],
    extra=1,
    can_delete=True,
    widgets={
        'name': forms.TextInput(attrs={'class': 'form-control'}),
        'price': forms.NumberInput(attrs={'class': 'form-control'}),
        'default_length_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
    }
)

from django import forms
from .models import Appointment, Service, Staff

from django import forms
from django.utils import timezone
from datetime import datetime
from .models import Appointment, Service, Staff

from django import forms
from .models import Appointment, Service, Staff
from django.utils import timezone
from datetime import datetime
from django import forms
from datetime import datetime
from django.utils import timezone
from .models import Appointment, Service, Staff  # Adjust import paths as needed

from django import forms
from django.utils import timezone
from datetime import datetime
from .models import Appointment, Service, Staff

class AppointmentForm(forms.ModelForm):
    service = forms.ModelChoiceField(
        queryset=Service.objects.none(),
        widget=forms.Select(attrs={'class': 'input-modern w-full h-12 px-4', 'id': 'svc-select'})
    )
    staff = forms.ModelChoiceField(
        queryset=Staff.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'input-modern w-full h-12 px-4', 'id': 'staff-select'})
    )
    appointment_start_time = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'id': 'final-time-input'})
    )

    class Meta:
        model = Appointment
        fields = [
            'guest_name', 'guest_phone', 'guest_email',
            'service', 'staff', 'appointment_date',
            'appointment_start_time', 'notes'
        ]
        widgets = {
            'appointment_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'input-modern w-full h-12 px-4',
                'id': 'date-input',
                'onchange': 'fetchSlots()'
            }),
            'guest_name': forms.TextInput(attrs={'class': 'input-modern w-full h-12 px-4'}),
            'guest_email': forms.EmailInput(attrs={'class': 'input-modern w-full h-12 px-4'}),
            'guest_phone': forms.TextInput(attrs={'class': 'input-modern w-full h-12 px-4'}),
            'notes': forms.Textarea(attrs={'class': 'input-modern w-full p-4', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        # Pop custom arguments passed from the view
        services = kwargs.pop('services', None)
        staff = kwargs.pop('staff', None)
        available_times = kwargs.pop('available_times', [])

        super().__init__(*args, **kwargs)

        # 1. Populate Services
        if services is not None:
            self.fields['service'].queryset = services
            self.fields['service'].label_from_instance = lambda obj: f"{obj.name} ({obj.default_length_minutes} min)"

        # 2. Populate Staff
        if staff is not None:
            self.fields['staff'].queryset = staff
            self.fields['staff'].empty_label = "Any Available Specialist"

        # 3. Handle Dynamic Time Choices
        # If we are receiving a POST, we need to inject the submitted time into 'choices'
        # so that Django's validation doesn't reject it as an "Invalid Choice".
        if 'appointment_start_time' in self.data:
            submitted_time = self.data.get('appointment_start_time')
            self.fields['appointment_start_time'].choices = [(submitted_time, submitted_time)]
        else:
            choices = [(t.strftime('%H:%M'), t.strftime('%I:%M %p')) for t in available_times]
            self.fields['appointment_start_time'].choices = [('', 'Select Time')] + choices

        self.fields['notes'].required = False

    def clean_appointment_start_time(self):
        """Convert the string time from the select/hidden input into a Python time object."""
        time_str = self.cleaned_data.get('appointment_start_time')
        if not time_str:
            raise forms.ValidationError("Please select a time slot.")
        try:
            return datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            # Handle cases like "14:00:00" if your JS format varies
            try:
                return datetime.strptime(time_str, '%H:%M:%S').time()
            except ValueError:
                raise forms.ValidationError("Invalid time format.")

    def clean(self):
        cleaned_data = super().clean()
        appointment_date = cleaned_data.get('appointment_date')
        start_time = cleaned_data.get('appointment_start_time')

        if appointment_date and start_time:
            # Combine Date and Time into a single datetime object
            appointment_datetime = datetime.combine(appointment_date, start_time)

            # Make it timezone aware (matching your project settings)
            appointment_datetime = timezone.make_aware(appointment_datetime)

            if appointment_datetime < timezone.now():
                self.add_error('appointment_start_time', "You cannot book an appointment in the past.")

        return cleaned_data


# In bookingApp/forms.py
class RescheduleAppointmentForm(forms.ModelForm):
    # Change ChoiceField to CharField to allow dynamic JS values
    appointment_start_time = forms.CharField(
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_appointment_start_time'})
    )

    class Meta:
        model = Appointment
        fields = ['appointment_date', 'appointment_start_time', 'notes']
        widgets = {
            'appointment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'id_appointment_date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # We no longer need to manually set choices here,
        # but we can set the initial value if needed.
        if self.instance and self.instance.pk:
            self.initial['appointment_start_time'] = self.instance.appointment_start_time.strftime('%H:%M')

class AppointmentStatusForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['status']
        widgets = {'status': forms.Select(attrs={'class': 'form-select'})}


# forms.py
class JoinStaffForm(forms.Form):
    company_code = forms.CharField(max_length=12, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Company Code'}))

# views.py
@login_required
def join_staff(request):
    if request.method == 'POST':
        form = JoinStaffForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['company_code']
            business = Business.objects.filter(join_code=code).first()

            if business:
                # Create the staff link
                Staff.objects.get_or_create(
                    business=business,
                    user=request.user,
                    defaults={'name': request.user.get_full_name() or request.user.username, 'email': request.user.email}
                )
                messages.success(request, f"You have joined {business.name} as a staff member!")
                return redirect('staff_dashboard') # Create this or redirect to home
            else:
                messages.error(request, "Invalid company code.")
    else:
        form = JoinStaffForm()
    return render(request, 'bookingApp/join_staff.html', {'form': form})

# forms.py

from django import forms
from .models import Appointment, Staff, Service

class ManualBookingForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = [
            'guest_name', 'guest_email', 'guest_phone',
            'staff', 'service', 'appointment_date',
            'appointment_start_time', 'notes'
        ]
        widgets = {
            'guest_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Client Name'}),
            'guest_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'guest_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),

            # These three trigger the availability check
            'staff': forms.Select(attrs={'class': 'form-select dynamic-field'}),
            'service': forms.Select(attrs={'class': 'form-select dynamic-field'}),
            'appointment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control dynamic-field'}),

            # Changed to Select to accommodate dynamic slots
            'appointment_start_time': forms.Select(attrs={'class': 'form-select', 'id': 'slot-container'}),

            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes...'}),
        }

    def __init__(self, *args, **kwargs):
        business = kwargs.pop('business', None)
        super().__init__(*args, **kwargs)

        # Initialize time field as empty until JS populates it
        self.fields['appointment_start_time'].choices = [('', 'Select date, staff & service first')]

        if business:
            # Only show services and staff belonging to this business
            self.fields['service'].queryset = Service.objects.filter(business=business)
            self.fields['staff'].queryset = Staff.objects.filter(business=business)
