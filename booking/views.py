from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from parking.models import ParkingSlot, Vehicle

from .forms import BookingForm
from .models import Booking


@login_required
def user_home_view(request):
    active_vehicle = Vehicle.objects.filter(owner=request.user, is_active=True).first()
    total_bookings = Booking.objects.filter(user=request.user).count()
    active_bookings = Booking.objects.filter(user=request.user, is_active=True).count()
    return render(
        request,
        'booking/user_home.html',
        {
            'active_vehicle': active_vehicle,
            'total_bookings': total_bookings,
            'active_bookings': active_bookings,
        },
    )


@login_required
def my_bookings_view(request):
    bookings = Booking.objects.filter(user=request.user).select_related('slot')
    return render(request, 'booking/my_bookings.html', {'bookings': bookings})


@login_required
def create_booking_view(request):
    if request.user.role != 'user':
        messages.error(request, 'Only users can create bookings.')
        return render(request, 'booking/booking_form.html', {'form': BookingForm()})

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            date = form.cleaned_data['date']
            start_time = form.cleaned_data['start_time']
            duration_minutes = form.cleaned_data['duration_minutes']
            category = form.cleaned_data['category']
            vehicle_number = form.cleaned_data['vehicle_number'].upper().strip()

            slots = ParkingSlot.objects.filter(status='available')
            if category:
                slots = slots.filter(category=category)

            booking_start = datetime.combine(date, start_time)
            booking_end = booking_start + timedelta(minutes=duration_minutes)

            selected_slot = None
            for slot in slots.order_by('slot_number'):
                conflict = False
                existing_bookings = Booking.objects.filter(slot=slot, date=date, is_active=True)
                for existing in existing_bookings:
                    existing_start = datetime.combine(existing.date, existing.start_time)
                    existing_end = existing_start + timedelta(minutes=existing.duration_minutes)
                    if booking_start < existing_end and booking_end > existing_start:
                        conflict = True
                        break
                if not conflict:
                    selected_slot = slot
                    break

            if not selected_slot:
                messages.error(request, 'No available slot for selected time.')
            else:
                booking = Booking.objects.create(
                    user=request.user,
                    slot=selected_slot,
                    date=date,
                    start_time=start_time,
                    duration_minutes=duration_minutes,
                    vehicle_number=vehicle_number,
                )
                messages.success(request, f'Booking confirmed! Slot {selected_slot.slot_number} allocated.')
                return redirect('booking:user_home')
    else:
        form = BookingForm()

    return render(request, 'booking/booking_form.html', {'form': form})


@login_required
def checkin_booking_view(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user, is_active=True)
    if booking.is_checked_in:
        messages.info(request, 'This booking is already checked in.')
        return redirect('booking:user_home')

    if Vehicle.objects.filter(vehicle_number=booking.vehicle_number, is_active=True).exists():
        messages.error(request, 'This vehicle already has an active parking entry.')
        return redirect('booking:user_home')

    if booking.slot.status != 'available':
        messages.error(request, 'The assigned slot is currently not available.')
        return redirect('booking:user_home')

    booking.is_checked_in = True
    booking.save(update_fields=['is_checked_in'])
    booking.slot.status = 'occupied'
    booking.slot.save(update_fields=['status'])
    Vehicle.objects.create(owner=request.user, vehicle_number=booking.vehicle_number, slot=booking.slot)
    messages.success(request, f'Checked in successfully to slot {booking.slot.slot_number}.')
    return redirect('booking:user_home')
