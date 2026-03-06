from rest_framework import serializers
from document.models import Document


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'company', 'file', 'uploaded_at', 'category']
        read_only_fields = ['uploaded_at']