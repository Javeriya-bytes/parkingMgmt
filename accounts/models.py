from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ADMIN = 'admin'
    USER = 'user'
    ROLE_CHOICES = [
        (ADMIN, 'Admin'),
        (USER, 'User'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=USER)

    @property
    def is_role_admin(self):
        return self.role == self.ADMIN
