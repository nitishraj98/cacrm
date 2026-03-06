from django.db import models
from user.models import User
from django_softdelete.models import SoftDeleteModel
from django_softdelete.managers import SoftDeleteManager
from django.db.models import Q
import uuid


class Company(SoftDeleteModel, models.Model):
    name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, null=True, blank=True)
    gst_number = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    pincode = models.IntegerField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='companies')
    client = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="clients")
    account_manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_companies")
    cid = models.CharField(max_length=20, unique=True, editable=False)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    all_objects = SoftDeleteManager()

    class Meta:
        db_table = 'company'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'registration_number', 'gst_number'],
                condition=Q(deleted_at__isnull=True),
                name='unique_company_not_deleted'
            )
        ]

    def save(self, *args, **kwargs):
        if not self.cid:
            self.cid = self.generate_company_uid()
        super().save(*args, **kwargs)

    def generate_company_uid(self):
        abbrev_name = ''.join([word[0] for word in self.name.split() if word]).upper()
        while True:
            uid = f"{abbrev_name}{uuid.uuid4().hex[:6]}"  # Abbreviation + Short UUID
            if not Company.objects.filter(cid=uid).exists():
                return uid


    def __str__(self):
        return self.name