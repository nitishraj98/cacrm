from rest_framework import serializers
from .models import *
from document.models import Document
from django.db.models import Q
from comment.models import Comment


class CompanySerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    account_manager_name = serializers.SerializerMethodField()
    class Meta:
        model = Company
        fields = '__all__'
        extra_fields = ['client_name','account_manager_name']
        # Avoid DRF's UniqueConstraint validator blowing up on partial updates
        # when condition fields (e.g., deleted_at) are not in the payload.
        validators = []
    
    def get_client_name(self, obj):
        return obj.client.full_name if obj.client else ""
    
    def get_account_manager_name(self, obj):
        return obj.account_manager.full_name if obj.account_manager else ""
    
    def validate(self, data):
        # For partial updates, fall back to instance values so we don't validate
        # against None when fields are omitted.
        name = data.get('name', self.instance.name if self.instance else None)
        gst_number = data.get('gst_number', self.instance.gst_number if self.instance else None)
        registration_number = data.get('registration_number', self.instance.registration_number if self.instance else None)

        # Prepare the query for individual field checks
        name_query = Q(name=name)
        gst_query = Q(gst_number=gst_number)
        registration_query = Q(registration_number=registration_number)

        # Exclude the current instance from the queries if updating
        if self.instance:
            name_query &= ~Q(id=self.instance.id)
            gst_query &= ~Q(id=self.instance.id)
            registration_query &= ~Q(id=self.instance.id)

        # Check for conflicts with other active (non-soft-deleted) companies
        if Company.objects.filter(name_query, deleted_at__isnull=True).exists():
            raise serializers.ValidationError({"name": "A company with this name already exists."})

        if Company.objects.filter(gst_query, deleted_at__isnull=True).exists():
            raise serializers.ValidationError({"gst_number": "A company with this GST number already exists."})

        if Company.objects.filter(registration_query, deleted_at__isnull=True).exists():
            raise serializers.ValidationError({"registration_number": "A company with this registration number already exists."})

        # Check for the exact match of all three fields
        exact_match_query = Q(name=name, gst_number=gst_number, registration_number=registration_number)
        if self.instance:
            exact_match_query &= ~Q(id=self.instance.id)
        
        if Company.objects.filter(exact_match_query, deleted_at__isnull=True).exists():
            raise serializers.ValidationError("A company with this name, GST number, and registration number already exists.")
        
        return data
    


class AssignCompaniesSerializer(serializers.Serializer):
    account_manager_id = serializers.IntegerField(write_only=True, help_text="ID of the Account Manager to whom the companies will be assigned.")
    company_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        write_only=True,
        help_text="List of company IDs to assign to the Account Manager."
    )

    def validate_account_manager_id(self, value):
        try:
            account_manager = User.objects.get(id=value, role='AM')
        except User.DoesNotExist:
            raise serializers.ValidationError("Account Manager ID is invalid or the user is not an Account Manager.")
        return value

    def validate_company_ids(self, value):
        companies = Company.objects.filter(id__in=value)
        if companies.count() != len(value):
            raise serializers.ValidationError("One or more company IDs are invalid.")
        return value
    


class RemoveCompaniesFromAMSerializer(serializers.Serializer):
    account_manager_id = serializers.IntegerField(write_only=True, help_text="ID of the Account Manager from whom the companies will be removed.")
    company_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        write_only=True,
        help_text="List of company IDs to remove from the Account Manager."
    )

    def validate_account_manager_id(self, value):
        try:
            account_manager = User.objects.get(id=value, role='AM')
        except User.DoesNotExist:
            raise serializers.ValidationError("Account Manager ID is invalid or the user is not an Account Manager.")
        return value

    def validate_company_ids(self, value):
        companies = Company.objects.filter(id__in=value)
        if companies.count() != len(value):
            raise serializers.ValidationError("One or more company IDs are invalid.")
        return value
    

class RemoveCompaniesSerializer(serializers.Serializer):
    client_id = serializers.IntegerField(write_only=True, help_text="ID of the client from whom the companies will be removed.")
    company_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        write_only=True,
        help_text="List of company IDs to remove from the client."
    )

    def validate_client_id(self, value):
        try:
            client = User.objects.get(id=value, role='CLNT')
        except User.DoesNotExist:
            raise serializers.ValidationError("Client ID is invalid or the user is not a client.")
        return value

    def validate_company_ids(self, value):
        companies = Company.objects.filter(id__in=value)
        if companies.count() != len(value):
            raise serializers.ValidationError("One or more company IDs are invalid.")
        return value


class CompanyDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id','company', 'file', 'uploaded_at', 'category']


class CompanyCommentSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['user', 'content', 'company', 'created_at', 'updated_at', 'username']

    def get_username(self, obj):
        return obj.user.full_name if obj.user else ""


class ClientCompanySerializer(serializers.ModelSerializer):
    documents = CompanyDocumentSerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            'id', 'name', 'registration_number', 'gst_number', 'address', 'city', 
            'state', 'country', 'pincode', 'phone_number', 'email', 'website',
            'created_by', 'client', 'account_manager', 'created_at', 'updated_at', 
            'documents', 'comments'
        ]

    def get_comments(self, obj):
        comments = obj.comments.order_by('created_at') 
        return CompanyCommentSerializer(comments, many=True).data


class ClientCompanylistSerializer(serializers.ModelSerializer):
    class Meta:
        model=Company
        fields=['id','name']
