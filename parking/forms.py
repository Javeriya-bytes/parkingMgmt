from django import forms

from .models import ParkingSlot, SystemSetting, Vehicle


class ParkingSlotForm(forms.ModelForm):
    class Meta:
        model = ParkingSlot
        fields = ['slot_number', 'category', 'slot_type', 'status']


class VehicleExitForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = []


class SettingsForm(forms.ModelForm):
    class Meta:
        model = SystemSetting
        fields = ['price_unit', 'price_rate']


class HistoryFilterForm(forms.Form):
    date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    vehicle_number = forms.CharField(required=False)


class QRScanForm(forms.Form):
    qr_data = forms.CharField(
        label='QR Data',
        help_text='Enter vehicle number from QR (example: 22K989)',
        widget=forms.TextInput(attrs={'placeholder': 'Enter vehicle number (e.g. 22K989)'}),
    )
