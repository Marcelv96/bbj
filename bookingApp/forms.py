from django import forms
from .models import Business, BookingForm, Appointment, Service, Staff

class BusinessForm(forms.ModelForm):
    class Meta:
        model = Business
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

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
from .models import Appointment, Service, Staff

from django import forms
from django.utils import timezone
from datetime import datetime
from .models import Appointment, Service, Staff

class AppointmentForm(forms.ModelForm):
    service = forms.ModelChoiceField(
        queryset=Service.objects.none(), 
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    staff = forms.ModelChoiceField(
        queryset=Staff.objects.none(), 
        required=False, 
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Appointment
        # 'length_minutes' is removed to enforce service-defined duration
        fields = ['service', 'staff', 'appointment_date', 'appointment_start_time', 'notes'] 
        widgets = {
            'appointment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'appointment_start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        services = kwargs.pop('services', None)
        staff = kwargs.pop('staff', None)
        super().__init__(*args, **kwargs)
        if services is not None:
            self.fields['service'].queryset = services
            # Display duration in dropdown for transparency
            self.fields['service'].label_from_instance = lambda obj: f"{obj.name} ({obj.default_length_minutes} min)"
        if staff is not None:
            self.fields['staff'].queryset = staff
            self.fields['staff'].empty_label = "No preference"
        self.fields['notes'].required = False

    def clean(self):
        cleaned_data = super().clean()
        appointment_date = cleaned_data.get('appointment_date')
        start_time = cleaned_data.get('appointment_start_time')

        if appointment_date and start_time:
            # Combine date and time to compare with current system time
            appointment_datetime = timezone.make_aware(
                datetime.combine(appointment_date, start_time)
            )
            
            # Validation to prevent booking in the past
            if appointment_datetime < timezone.now():
                raise forms.ValidationError("You cannot book an appointment in the past.")

        return cleaned_data

class RescheduleAppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['appointment_date', 'appointment_start_time', 'notes']
        widgets = {
            'appointment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'appointment_start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        

class AppointmentStatusForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['status']
        widgets = {'status': forms.Select(attrs={'class': 'form-select'})}