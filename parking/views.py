import csv
from functools import wraps
from io import BytesIO
from decimal import Decimal
from pathlib import Path

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import qrcode

from .forms import HistoryFilterForm, ParkingSlotForm, QRScanForm, SettingsForm
from .models import ParkingSlot, Payment, SystemSetting, Vehicle


User = get_user_model()


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'admin':
            messages.error(request, 'Access denied.')
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return _wrapped


@login_required
@admin_required
def dashboard_view(request):
    total_slots = ParkingSlot.objects.count()
    available_slots = ParkingSlot.objects.filter(status='available').count()
    occupied_slots = ParkingSlot.objects.filter(status='occupied').count()
    active_vehicles = Vehicle.objects.filter(is_active=True).count()
    total_revenue = Payment.objects.aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')
    context = {
        'total_slots': total_slots,
        'available_slots': available_slots,
        'occupied_slots': occupied_slots,
        'active_vehicles': active_vehicles,
        'total_revenue': total_revenue,
    }
    return render(request, 'parking/dashboard.html', context)


@login_required
@admin_required
def slot_list_view(request):
    slots = ParkingSlot.objects.all().order_by('slot_number')
    category = request.GET.get('category', '')
    status = request.GET.get('status', '')
    if category:
        slots = slots.filter(category=category)
    if status:
        slots = slots.filter(status=status)
    context = {
        'slots': slots,
        'category': category,
        'status': status,
        'available_count': ParkingSlot.objects.filter(status='available').count(),
        'occupied_count': ParkingSlot.objects.filter(status='occupied').count(),
    }
    return render(request, 'parking/slot_list.html', context)


@login_required
@admin_required
def slot_create_view(request):
    if request.method == 'POST':
        form = ParkingSlotForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Slot added successfully.')
            return redirect('parking:slot_list')
    else:
        form = ParkingSlotForm()
    return render(request, 'parking/slot_form.html', {'form': form, 'title': 'Add Slot'})


@login_required
@admin_required
def slot_update_view(request, pk):
    slot = get_object_or_404(ParkingSlot, pk=pk)
    if request.method == 'POST':
        form = ParkingSlotForm(request.POST, instance=slot)
        if form.is_valid():
            form.save()
            messages.success(request, 'Slot updated successfully.')
            return redirect('parking:slot_list')
    else:
        form = ParkingSlotForm(instance=slot)
    return render(request, 'parking/slot_form.html', {'form': form, 'title': 'Update Slot'})


@login_required
@admin_required
def slot_delete_view(request, pk):
    slot = get_object_or_404(ParkingSlot, pk=pk)
    if request.method == 'POST':
        slot.delete()
        messages.success(request, 'Slot deleted successfully.')
        return redirect('parking:slot_list')
    return render(request, 'parking/slot_delete_confirm.html', {'slot': slot})


@login_required
@admin_required
def vehicle_entry_list_view(request):
    vehicles = Vehicle.objects.filter(is_active=True).order_by('-entry_time')
    return render(request, 'parking/vehicle_entry_list.html', {'vehicles': vehicles})


@login_required
@admin_required
def vehicle_exit_view(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, is_active=True)
    setting = SystemSetting.get_solo()

    vehicle.exit_time = timezone.now()
    vehicle.is_active = False
    minutes = vehicle.parked_minutes()

    if setting.price_unit == 'hour':
        units = Decimal(minutes) / Decimal('60')
    else:
        units = Decimal(minutes)

    total = units * setting.price_rate
    total = total.quantize(Decimal('0.01'))

    if vehicle.slot:
        vehicle.slot.status = 'available'
        vehicle.slot.save()

    vehicle.save()
    payment = Payment.objects.create(vehicle=vehicle, total_cost=total)

    messages.success(request, f'Vehicle exited. Bill generated: {total}')
    return render(request, 'parking/exit_success.html', {
        'vehicle': vehicle,
        'total': total
    })


@login_required
@admin_required
def history_view(request):
    records = Vehicle.objects.filter(is_active=False).select_related('owner', 'slot').order_by('-exit_time')
    form = HistoryFilterForm(request.GET or None)
    if form.is_valid():
        date = form.cleaned_data.get('date')
        vehicle_number = form.cleaned_data.get('vehicle_number')
        if date:
            records = records.filter(exit_time__date=date)
        if vehicle_number:
            records = records.filter(vehicle_number__icontains=vehicle_number)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="parking_history.csv"'
        writer = csv.writer(response)
        writer.writerow(['Vehicle', 'Owner', 'Slot', 'Entry Time', 'Exit Time'])
        for r in records:
            writer.writerow([r.vehicle_number, r.owner.username, r.slot.slot_number if r.slot else '-', r.entry_time, r.exit_time])
        return response

    return render(request, 'parking/history.html', {'records': records, 'form': form})


@login_required
@admin_required
def settings_view(request):
    setting = SystemSetting.get_solo()
    if request.method == 'POST':
        form = SettingsForm(request.POST, instance=setting)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pricing settings updated.')
            return redirect('parking:settings')
    else:
        form = SettingsForm(instance=setting)

    users = User.objects.all().order_by('username')
    return render(request, 'parking/settings.html', {'form': form, 'users': users})


@login_required
@admin_required
def user_role_update_view(request, pk):
    user = get_object_or_404(User, pk=pk)
    role = request.POST.get('role')
    if role in ['admin', 'user']:
        user.role = role
        user.save(update_fields=['role'])
        messages.success(request, f'Role updated for {user.username}.')
    else:
        messages.error(request, 'Invalid role selected.')
    return redirect('parking:settings')


@login_required
@admin_required
def user_delete_view(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('parking:settings')
    user.delete()
    messages.success(request, 'User deleted successfully.')
    return redirect('parking:settings')


@login_required
def slot_status_api(request):
    slots = list(ParkingSlot.objects.values('slot_number', 'status', 'category', 'slot_type'))
    counts = {
        'available': ParkingSlot.objects.filter(status='available').count(),
        'occupied': ParkingSlot.objects.filter(status='occupied').count(),
    }
    return JsonResponse({'slots': slots, 'counts': counts})


@login_required
def generate_receipt(request, vehicle_id):
    vehicle = get_object_or_404(
        Vehicle.objects.select_related('slot', 'payment', 'owner'),
        pk=vehicle_id,
    )
    payment = vehicle.payment
    qr_text = vehicle.vehicle_number

    media_dir = Path(settings.BASE_DIR) / 'media'
    media_dir.mkdir(parents=True, exist_ok=True)
    qr_path = media_dir / f'qr_{vehicle.id}.png'
    qr_img = qrcode.make(qr_text)
    qr_img.save(qr_path)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.setTitle('Parking Receipt')

    pdf.setFont('Helvetica-Bold', 16)
    pdf.drawString(50, 800, 'Smart Parking - Receipt')
    pdf.setFont('Helvetica', 11)
    pdf.drawString(50, 770, f'Vehicle Number: {vehicle.vehicle_number}')
    pdf.drawString(50, 750, f'Slot Number: {vehicle.slot.slot_number if vehicle.slot else "-"}')
    pdf.drawString(50, 730, f'Entry Time: {vehicle.entry_time}')
    pdf.drawString(50, 710, f'Exit Time: {vehicle.exit_time}')
    pdf.drawString(50, 690, f'Total Amount: Rs. {payment.total_cost if payment else "-"}')
    pdf.drawString(50, 670, f'QR Data: {qr_text}')

    pdf.drawImage(ImageReader(str(qr_path)), 400, 620, width=150, height=150)
    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{vehicle.vehicle_number}.pdf"'
    return response


@login_required
def qr_scanner_view(request):
    result = None
    scan_details = None
    qr_image_url = None
    form = QRScanForm(request.POST or None)
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if request.method == 'POST' and form.is_valid():
        qr_data = form.cleaned_data['qr_data'].strip()
        if not qr_data:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Enter vehicle number.'}, status=400)
            messages.error(request, 'Enter vehicle number.')
        else:
            try:
                vehicle = Vehicle.objects.select_related('slot', 'owner').get(vehicle_number__iexact=qr_data)
                result = vehicle
                setting = SystemSetting.get_solo()
                end_time = vehicle.exit_time or timezone.now()
                duration_seconds = max((end_time - vehicle.entry_time).total_seconds(), 60)
                duration_minutes = Decimal(str(duration_seconds)) / Decimal('60')
                duration_hours = Decimal(str(duration_seconds)) / Decimal('3600')

                if setting.price_unit == 'minute':
                    amount = duration_minutes * setting.price_rate
                else:
                    amount = duration_hours * setting.price_rate
                amount = amount.quantize(Decimal('0.01'))
                duration_text = f"{int(duration_minutes)} minutes ({duration_hours.quantize(Decimal('0.01'))} hours)"

                # Generate and save QR code image
                media_dir = Path(settings.BASE_DIR) / 'media'
                media_dir.mkdir(parents=True, exist_ok=True)
                qr_filename = f'qr_{vehicle.id}.png'
                qr_path = media_dir / qr_filename
                qr_img = qrcode.make(vehicle.vehicle_number)
                qr_img.save(qr_path)
                qr_image_url = f'/media/{qr_filename}'

                scan_details = {
                    'owner_email': vehicle.owner.email,
                    'duration': duration_text,
                    'amount': str(amount),
                }

                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'vehicle_id': vehicle.id,
                        'vehicle_number': vehicle.vehicle_number,
                        'owner': vehicle.owner.username,
                        'owner_email': vehicle.owner.email,
                        'slot': vehicle.slot.slot_number if vehicle.slot else '-',
                        'entry_time': str(vehicle.entry_time),
                        'exit_time': str(vehicle.exit_time) if vehicle.exit_time else 'Still Active',
                        'duration': duration_text,
                        'amount': str(amount),
                        'qr_image_url': qr_image_url,
                        'pdf_url': f'/parking/scanner-receipt/{vehicle.id}/',
                        'receipt_url': f'/parking/receipt/{vehicle.id}/' if vehicle.exit_time else '',
                    })
            except Vehicle.DoesNotExist:
                if is_ajax:
                    return JsonResponse({'success': False, 'error': 'Vehicle not found.'}, status=404)
                messages.error(request, 'Vehicle not found.')

    elif request.method == 'POST' and is_ajax:
        return JsonResponse({'success': False, 'error': 'Enter vehicle number.'}, status=400)

    return render(
        request,
        'parking/qr_scanner.html',
        {
            'form': form,
            'result': result,
            'scan_details': scan_details,
            'qr_image_url': qr_image_url,
        },
    )
@login_required
def scanner_receipt_pdf(request, vehicle_id):
    vehicle = get_object_or_404(
        Vehicle.objects.select_related('slot', 'owner'),
        pk=vehicle_id
    )
    setting = SystemSetting.get_solo()

    end_time = vehicle.exit_time or timezone.now()
    duration_seconds = max((end_time - vehicle.entry_time).total_seconds(), 60)
    duration_minutes = Decimal(str(duration_seconds)) / Decimal('60')
    duration_hours = Decimal(str(duration_seconds)) / Decimal('3600')

    if setting.price_unit == 'minute':
        amount = duration_minutes * setting.price_rate
    else:
        amount = duration_hours * setting.price_rate
    amount = amount.quantize(Decimal('0.01'))
    duration_text = f"{int(duration_minutes)} min ({duration_hours.quantize(Decimal('0.01'))} hrs)"

    media_dir = Path(settings.BASE_DIR) / 'media'
    media_dir.mkdir(parents=True, exist_ok=True)
    qr_path = media_dir / f'qr_{vehicle.id}.png'
    qr_img = qrcode.make(vehicle.vehicle_number)
    qr_img.save(qr_path)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setFillColorRGB(0.08, 0.35, 0.55)
    pdf.rect(0, height - 80, width, 80, fill=1, stroke=0)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont('Helvetica-Bold', 20)
    pdf.drawString(40, height - 45, 'Smart Parking')
    pdf.setFont('Helvetica', 11)
    pdf.drawString(40, height - 65, 'Parking Receipt / Payment Summary')

    box_left  = 40
    box_right = width - 40
    line_h    = 28
    y         = height - 110

    def draw_row(y, label, value, shade=False):
        if shade:
            pdf.setFillColorRGB(0.94, 0.96, 0.98)
            pdf.rect(box_left, y - 6, box_right - box_left, line_h, fill=1, stroke=0)
        pdf.setFillColorRGB(0.3, 0.3, 0.3)
        pdf.setFont('Helvetica-Bold', 10)
        pdf.drawString(box_left + 10, y + 7, label)
        pdf.setFillColorRGB(0.05, 0.05, 0.05)
        pdf.setFont('Helvetica', 10)
        pdf.drawString(box_left + 180, y + 7, str(value))

    rows = [
        ('Vehicle Number', vehicle.vehicle_number),
        ('Owner',          vehicle.owner.username),
        ('Email',          vehicle.owner.email),
        ('Slot',           vehicle.slot.slot_number if vehicle.slot else '-'),
        ('Entry Time',     vehicle.entry_time.strftime('%d %b %Y  %H:%M:%S')),
        ('Exit Time',      vehicle.exit_time.strftime('%d %b %Y  %H:%M:%S') if vehicle.exit_time else 'Still Active'),
        ('Duration',       duration_text),
        ('Rate',           f"Rs. {setting.price_rate} / {setting.price_unit}"),
        ('Status',         'Exited' if vehicle.exit_time else 'Active'),
    ]

    for i, (label, value) in enumerate(rows):
        draw_row(y, label, value, shade=(i % 2 == 0))
        y -= line_h

    y -= 10
    pdf.setFillColorRGB(0.08, 0.35, 0.55)
    pdf.rect(box_left, y - 6, box_right - box_left, 36, fill=1, stroke=0)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont('Helvetica-Bold', 13)
    pdf.drawString(box_left + 10, y + 10, 'Total Amount')
    pdf.drawRightString(box_right - 10, y + 10, f'Rs. {amount}')

    qr_size = 130
    qr_x = (width - qr_size) / 2
    qr_y = y - qr_size - 35
    pdf.setFillColorRGB(0.05, 0.05, 0.05)
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawCentredString(width / 2, y - 20, 'Scan QR to Verify Vehicle')
    pdf.drawImage(ImageReader(str(qr_path)), qr_x, qr_y, width=qr_size, height=qr_size, preserveAspectRatio=True)
    pdf.setFont('Helvetica', 9)
    pdf.setFillColorRGB(0.4, 0.4, 0.4)
    pdf.drawCentredString(width / 2, qr_y - 15, vehicle.vehicle_number)

    pdf.setFillColorRGB(0.08, 0.35, 0.55)
    pdf.rect(0, 0, width, 35, fill=1, stroke=0)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont('Helvetica', 9)
    pdf.drawCentredString(width / 2, 12, f'Generated on {timezone.now().strftime("%d %b %Y  %H:%M")}  |  Smart Parking System')

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{vehicle.vehicle_number}.pdf"'
    return response

@login_required
def scanner_receipt_pdf(request, vehicle_id):
    vehicle = get_object_or_404(
        Vehicle.objects.select_related('slot', 'owner'),
        pk=vehicle_id
    )
    setting = SystemSetting.get_solo()

    end_time = vehicle.exit_time or timezone.now()
    duration_seconds = max((end_time - vehicle.entry_time).total_seconds(), 60)
    duration_minutes = Decimal(str(duration_seconds)) / Decimal('60')
    duration_hours = Decimal(str(duration_seconds)) / Decimal('3600')

    if setting.price_unit == 'minute':
        amount = duration_minutes * setting.price_rate
    else:
        amount = duration_hours * setting.price_rate
    amount = amount.quantize(Decimal('0.01'))
    duration_text = f"{int(duration_minutes)} min ({duration_hours.quantize(Decimal('0.01'))} hrs)"

    media_dir = Path(settings.BASE_DIR) / 'media'
    media_dir.mkdir(parents=True, exist_ok=True)
    qr_path = media_dir / f'qr_{vehicle.id}.png'
    qr_img = qrcode.make(vehicle.vehicle_number)
    qr_img.save(qr_path)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Blue header
    pdf.setFillColorRGB(0.08, 0.35, 0.55)
    pdf.rect(0, height - 80, width, 80, fill=1, stroke=0)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont('Helvetica-Bold', 20)
    pdf.drawString(40, height - 45, 'Smart Parking')
    pdf.setFont('Helvetica', 11)
    pdf.drawString(40, height - 65, 'Parking Receipt / Payment Summary')

    # Detail rows
    box_left  = 40
    box_right = width - 40
    line_h    = 28
    y         = height - 110

    def draw_row(y, label, value, shade=False):
        if shade:
            pdf.setFillColorRGB(0.94, 0.96, 0.98)
            pdf.rect(box_left, y - 6, box_right - box_left, line_h, fill=1, stroke=0)
        pdf.setFillColorRGB(0.3, 0.3, 0.3)
        pdf.setFont('Helvetica-Bold', 10)
        pdf.drawString(box_left + 10, y + 7, label)
        pdf.setFillColorRGB(0.05, 0.05, 0.05)
        pdf.setFont('Helvetica', 10)
        pdf.drawString(box_left + 180, y + 7, str(value))

    rows = [
        ('Vehicle Number', vehicle.vehicle_number),
        ('Owner',          vehicle.owner.username),
        ('Email',          vehicle.owner.email),
        ('Slot',           vehicle.slot.slot_number if vehicle.slot else '-'),
        ('Entry Time',     vehicle.entry_time.strftime('%d %b %Y  %H:%M:%S')),
        ('Exit Time',      vehicle.exit_time.strftime('%d %b %Y  %H:%M:%S') if vehicle.exit_time else 'Still Active'),
        ('Duration',       duration_text),
        ('Rate',           f"Rs. {setting.price_rate} / {setting.price_unit}"),
        ('Status',         'Exited' if vehicle.exit_time else 'Active'),
    ]

    for i, (label, value) in enumerate(rows):
        draw_row(y, label, value, shade=(i % 2 == 0))
        y -= line_h

    # Total amount bar
    y -= 10
    pdf.setFillColorRGB(0.08, 0.35, 0.55)
    pdf.rect(box_left, y - 6, box_right - box_left, 36, fill=1, stroke=0)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont('Helvetica-Bold', 13)
    pdf.drawString(box_left + 10, y + 10, 'Total Amount')
    pdf.drawRightString(box_right - 10, y + 10, f'Rs. {amount}')

    # QR code
    qr_size = 130
    qr_x = (width - qr_size) / 2
    qr_y = y - qr_size - 35
    pdf.setFillColorRGB(0.05, 0.05, 0.05)
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawCentredString(width / 2, y - 20, 'Scan QR to Verify Vehicle')
    pdf.drawImage(ImageReader(str(qr_path)), qr_x, qr_y, width=qr_size, height=qr_size, preserveAspectRatio=True)
    pdf.setFont('Helvetica', 9)
    pdf.setFillColorRGB(0.4, 0.4, 0.4)
    pdf.drawCentredString(width / 2, qr_y - 15, vehicle.vehicle_number)

    # Footer
    pdf.setFillColorRGB(0.08, 0.35, 0.55)
    pdf.rect(0, 0, width, 35, fill=1, stroke=0)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont('Helvetica', 9)
    pdf.drawCentredString(width / 2, 12, f'Generated on {timezone.now().strftime("%d %b %Y  %H:%M")}  |  Smart Parking System')

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{vehicle.vehicle_number}.pdf"'
    return response
