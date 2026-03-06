from django.db import models
from django_softdelete.models import SoftDeleteModel
from company.models import Company


class Document(SoftDeleteModel, models.Model):
    CATEGORY_CHOICES = [
        ('GST', 'GST Documents'),
        ('IT', 'IT Documents'),
        ('TDS', 'TDS Documents'),
        # Add more categories as needed
    ]
    
    company = models.ForeignKey(Company, related_name='documents', on_delete=models.CASCADE)
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, null=True)

    class Meta:
        db_table = 'document'