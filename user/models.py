from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django_softdelete.models import SoftDeleteModel
from django_softdelete.managers import SoftDeleteManager
from django.db.models import Q
import uuid

class BlacklistedToken(models.Model):
    token = models.CharField(max_length=255, unique=True)
    blacklisted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'blacklisted_token'

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(SoftDeleteModel, AbstractUser):
    username = None  
    middle_name = models.CharField(max_length=30, null=True, blank=True)  
    uid = models.CharField(max_length=50, unique=True, editable=False)  
    ROLE_CHOICES = [
        ('CA', 'CA'),
        ('AM', 'Account Manager'),
        ('CLNT', 'Client'),
    ]
    role = models.CharField(max_length=15, choices=ROLE_CHOICES)
    email = models.EmailField(('email address'), unique=True) 
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    full_name = models.CharField(max_length=255, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    pincode = models.IntegerField(null=True, blank=True)
    assigned_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_clients')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()
    all_objects = SoftDeleteManager()

    USERNAME_FIELD = 'email'  
    REQUIRED_FIELDS = []  

    class Meta:
        db_table = 'user'

    def save(self, *args, **kwargs):
        # Automatically set full_name by combining first_name, middle_name, and last_name
        full_name_parts = [self.first_name, self.middle_name, self.last_name]
        self.full_name = ' '.join(part for part in full_name_parts if part).strip()
        

        if not self.uid:
            self.uid = self.generate_uid(self.first_name)
        

        super().save(*args, **kwargs)


    def generate_uid(self, first_name):
        return f"{first_name.lower()}{uuid.uuid4().hex[:8]}"


class Permission(models.Model):
    PERMISSION_CHOICES = [
        ('create_user', 'Create User'),
        ('update_user', 'Update User'),
        ('delete_user', 'Delete User'),
        ('restore_user', 'Restore User'),
        ('create_company', 'Create Company'),
        ('update_company', 'Update Company'),
        ('delete_company', 'Delete Company'),
        ('restore_company', 'Restore Company'),
        ('create_document', 'Create Document'),
        ('update_document', 'Update Document'),
        ('delete_document', 'Delete Document'),
        ('restore_document', 'Restore Document'),
        ('create_comment', 'Create Comment'),
        ('update_comment', 'Update Comment'),
        ('delete_comment', 'Delete Comment'),
        ('restore_comment', 'Restore Comment'),
        # Add new permission types here
    ]

    created_by = models.ForeignKey(User, related_name='created_permissions', on_delete=models.SET_NULL, null=True)
    granted_to = models.ForeignKey(User, related_name='granted_permissions', on_delete=models.SET_NULL, null=True)
    permission_type = models.CharField(max_length=50, choices=PERMISSION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'permission'
        unique_together = ('created_by', 'granted_to', 'permission_type')



