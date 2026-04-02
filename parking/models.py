from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class ParkingSlot(models.Model):
    CATEGORY_CHOICES = [('car', 'Car'), ('bike', 'Bike'), ('ev', 'EV')]
    TYPE_CHOICES = [('vip', 'VIP'), ('normal', 'Normal')]
    STATUS_CHOICES = [('available', 'Available'), ('occupied', 'Occupied')]

    slot_number = models.CharField(max_length=20, unique=True)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    slot_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='normal')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='available')

    def __str__(self):
        return self.slot_number


class Vehicle(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    vehicle_number = models.CharField(max_length=20, unique=True)
    slot = models.ForeignKey(ParkingSlot, on_delete=models.SET_NULL, null=True, blank=True)
    entry_time = models.DateTimeField(default=timezone.now)
    exit_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def parked_minutes(self):
        end_time = self.exit_time or timezone.now()
        minutes = int((end_time - self.entry_time).total_seconds() // 60)
        return max(minutes, 1)


class SystemSetting(models.Model):
    PRICE_UNIT_CHOICES = [('hour', 'Per Hour'), ('minute', 'Per Minute')]

    price_unit = models.CharField(max_length=10, choices=PRICE_UNIT_CHOICES, default='hour')
    price_rate = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('50.00'))

    @classmethod
    def get_solo(cls):
        setting, _ = cls.objects.get_or_create(pk=1)
        return setting


class Payment(models.Model):
    vehicle = models.OneToOneField(Vehicle, on_delete=models.CASCADE)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    paid_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vehicle.vehicle_number} - {self.total_cost}"
