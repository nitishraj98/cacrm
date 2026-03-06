from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, Permission
from django.db.models import Q
from rest_framework.exceptions import ValidationError

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        return token
    

class UserSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['id', 'uid', 'full_name','first_name','middle_name','last_name', 'email', 'password', 'role', 'phone_number','country','state','city','address','pincode','date_of_birth','assigned_to','assigned_to_name','created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True}
        }


    def get_assigned_to_name(self, obj):
        return obj.assigned_to.full_name if obj.assigned_to else ""
    
    def validate_phone_number(self, value):
        # Check if phone_number already exists for another active user
        if User.objects.filter(phone_number=value, is_active=True).exclude(id=self.instance.id if self.instance else None).exists():
            raise ValidationError('A user with this phone number already exists.')
        return value

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = self.Meta.model(**validated_data)
        if password:
            user.set_password(password)
        user.save()  
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

    

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'created_by', 'granted_to', 'permission_type', 'created_at']


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'full_name', 'email']


class AccountManagerClientsSerializer(serializers.ModelSerializer):
    clients = ClientSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'clients']


class AssignClientSerializer(serializers.Serializer):
    client_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role='CLNT'))
    account_manager_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role='AM'))


class RemoveAccountManagerSerializer(serializers.Serializer):
    client_id = serializers.IntegerField()
    account_manager_id = serializers.IntegerField()











