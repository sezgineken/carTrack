from django import forms
from django.utils import timezone
from .models import VehicleReservation, VehicleUsage


class VehicleReservationForm(forms.ModelForm):
    """Form for creating vehicle reservation"""
    start_time = forms.DateTimeField(
        required=True,
        label='Başlangıç Zamanı',
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local',
            'required': True
        })
    )
    end_time = forms.DateTimeField(
        required=True,
        label='Bitiş Zamanı',
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local',
            'required': True
        })
    )
    purpose = forms.CharField(
        required=False,
        label='Amaç',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    
    class Meta:
        model = VehicleReservation
        fields = ['start_time', 'end_time', 'purpose']
    
    def __init__(self, *args, **kwargs):
        self.vehicle = kwargs.pop('vehicle', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time:
            if end_time <= start_time:
                raise forms.ValidationError('Bitiş zamanı başlangıç zamanından sonra olmalıdır.')
            
            if start_time <= timezone.now():
                raise forms.ValidationError('Rezervasyon başlangıç zamanı gelecekte olmalıdır.')
        
        return cleaned_data
    
    def save(self, commit=True):
        reservation = super().save(commit=False)
        reservation.vehicle = self.vehicle
        # Always use the user from __init__, never from form data
        if self.user:
            reservation.user = self.user
        if commit:
            reservation.save()
        return reservation


class VehicleUsageCompleteForm(forms.ModelForm):
    """Form for completing a vehicle usage after reservation end."""

    class Meta:
        model = VehicleUsage
        fields = ['dropoff_kilometer', 'destination', 'purpose']
        labels = {
            'dropoff_kilometer': 'Kilometre',
            'destination': 'Gidilen Yerler',
            'purpose': 'Amaç',
        }
        widgets = {
            'dropoff_kilometer': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'required': True}),
            'destination': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'required': True}),
            'purpose': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'required': True}),

        }

    def __init__(self, *args, **kwargs):
        self.usage = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        self.fields['destination'].required = True
        self.fields['purpose'].required = True

    def clean_dropoff_kilometer(self):
        dropoff_km = self.cleaned_data.get('dropoff_kilometer')
        if dropoff_km is None:
            return dropoff_km

        pickup_km = self.usage.pickup_kilometer if self.usage else 0
        if dropoff_km < pickup_km:
            raise forms.ValidationError(
                f'Kilometre değeri {pickup_km} değerinden küçük olamaz.'
            )
        return dropoff_km


class VehicleReservationExtendForm(forms.Form):
    """Form for extending reservation end time only."""

    new_end_time = forms.DateTimeField(
        required=True,
        label='Yeni Bitiş Zamanı',
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local',
            'required': True
        })
    )

    def __init__(self, *args, **kwargs):
        self.base_end_time = kwargs.pop('base_end_time')
        super().__init__(*args, **kwargs)

    def clean_new_end_time(self):
        new_end_time = self.cleaned_data.get('new_end_time')
        if new_end_time is None:
            return new_end_time
        if new_end_time <= self.base_end_time:
            raise forms.ValidationError('Yeni bitiş zamanı mevcut bitiş zamanından sonra olmalıdır.')
        return new_end_time

