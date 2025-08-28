
from django.db import models
import uuid
from django.utils import timezone
from django.contrib.auth.models import AbstractUser, PermissionsMixin

# Create your models here.
class Role(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    HR    = "HR",    "HR"
    HOD   = "HOD",   "Head-of-Dept"
    LM    = "LM",    "Line Manager"
    EMP   = "EMP",   "Employee"

class Gender(models.TextChoices):
    MALE   = "MALE",   "Male"
    FEMALE = "FEMALE", "Female"
    OTHER  = "OTHER",  "Other"

class User(AbstractUser):
    user_id    = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name       = models.CharField(max_length=120)
    email      = models.EmailField(unique=True)
    phone      = models.CharField(max_length=30, blank=True)
    country_code = models.CharField(max_length=8, blank=True, default="")
    gender     = models.CharField(max_length=6, choices=Gender.choices,default=Gender.MALE,null=True,blank=True)
    avatar     = models.URLField(blank=True)
    role       = models.CharField(max_length=8, choices=Role.choices)
    position      = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)  


    def __str__(self):
        return self.get_full_name() or self.username


''' class User(models.Model):
    user_id    = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name       = models.CharField(max_length=120)
    email      = models.EmailField(unique=True)
    phone      = models.CharField(max_length=30, blank=True)
    avatar     = models.URLField(blank=True)
    role       = models.CharField(max_length=8, choices=Role.choices)
    title      = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)    '''
