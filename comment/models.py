from django.db import models
from django_softdelete.models import SoftDeleteModel
from user.models import User
from company.models import Company


class Comment(SoftDeleteModel, models.Model):
    user = models.ForeignKey(User,on_delete=models.SET_NULL, null=True, blank=True, related_name="usercomment")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    company = models.ForeignKey(Company, related_name='comments', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'comment'

    def __str__(self):
        return f"Comment by {self.user.full_name} on {self.created_at}"
