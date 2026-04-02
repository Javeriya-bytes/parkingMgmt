from django.conf import settings
from django.db import models

from parking.models import ParkingSlot


class Booking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    slot = models.ForeignKey(ParkingSlot, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField()
    vehicle_number = models.CharField(max_length=20, default='UNKNOWN')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_checked_in = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date', '-start_time']

    def __str__(self):
        return f"{self.user.username} - {self.slot.slot_number}"
