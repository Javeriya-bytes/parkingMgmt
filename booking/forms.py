from django import forms


class BookingForm(forms.Form):
    vehicle_number = forms.CharField(max_length=20)
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    start_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    duration_minutes = forms.IntegerField(min_value=30, max_value=720)
    category = forms.ChoiceField(choices=[('', 'Any'), ('car', 'Car'), ('bike', 'Bike'), ('ev', 'EV')], required=False)
