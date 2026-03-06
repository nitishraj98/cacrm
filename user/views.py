from rest_framework import viewsets,status,generics,filters
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .models import *
from .serializers import *
from .permissions import *
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken,AccessToken
from django.shortcuts import get_object_or_404
from user.decorators import *
from django_filters.rest_framework import DjangoFilterBackend
from django.db import IntegrityError,transaction
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
import django_filters
from rest_framework.pagination import PageNumberPagination


class CARegistrationViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(role='CA', deleted_at__isnull=True)
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        # Set role to 'CA'
        request.data['role'] = 'CA'
        
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except ValidationError as e:
            error_message = "Invalid data"
            if isinstance(e.detail, dict) and any(e.detail.values()):
                error_message = list(e.detail.values())[0][0]
            return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    
class CustomLoginView(TokenObtainPairView):

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({"error": "Email and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)  
        except User.DoesNotExist:
            return Response({"error": "Invalid email"}, status=status.HTTP_400_BAD_REQUEST)
        except User.MultipleObjectsReturned:
            return Response({"error": "Multiple users found with this email"}, status=status.HTTP_400_BAD_REQUEST)

        if user.check_password(password):
           
            
            response = super().post(request, *args, **kwargs)
            
            response.data['role'] = user.role
            response.data['name'] = user.full_name
            response.data['email'] = user.email
            response.data['phone_number'] = user.phone_number
            response.data['message'] = 'Login successful'
            return response
        else:
            return Response({"error": "Invalid password"}, status=status.HTTP_400_BAD_REQUEST)
        

class LogoutAPIView(APIView):

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get('refresh')
        access_token = request.data.get('access')

        if not refresh_token:
            return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            # Blacklist the access token
            if access_token:
                access_token_obj = AccessToken(access_token)
                BlacklistedToken.objects.create(token=str(access_token_obj))
                
            return Response({"message": "Logged out successfully"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GrantPermissionView(APIView):
    permission_classes = [IsTokenValid]

    def post(self, request):
        if request.user.role != 'CA':
            return Response({"error": "Only CA can grant permissions."}, status=status.HTTP_403_FORBIDDEN)

        granted_to_id = request.data.get('granted_to_id')
        permission_types = request.data.get('permission_types')

        if not granted_to_id or not permission_types:
            return Response({"error": "User ID and permission types are required."}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(permission_types, list):
            return Response({"error": "Permission types should be a list."}, status=status.HTTP_400_BAD_REQUEST)

        granted_to = get_object_or_404(User, id=granted_to_id)
        if granted_to.role != 'AM':
            return Response({"error": "Can only grant permissions to Account Managers."}, status=status.HTTP_400_BAD_REQUEST)

        already_granted_permissions = []
        newly_granted_permissions = []

        for permission_type in permission_types:
            if Permission.objects.filter(created_by=request.user, granted_to=granted_to, permission_type=permission_type).exists():
                already_granted_permissions.append(permission_type)
            else:
                # Create the permission if it doesn't exist
                Permission.objects.create(created_by=request.user, granted_to=granted_to, permission_type=permission_type)
                newly_granted_permissions.append(permission_type)

        if already_granted_permissions:
            return Response({
                "message": f"{already_granted_permissions} already exits and granted this permission {newly_granted_permissions}.",
                "already_granted_permissions": already_granted_permissions,
                "newly_granted_permissions": newly_granted_permissions
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Permissions granted successfully.",
            "newly_granted_permissions": newly_granted_permissions
        }, status=status.HTTP_201_CREATED)
 
    def get(self, request):
        granted_to_id = request.query_params.get('granted_to_id')

        if granted_to_id:
            user = get_object_or_404(User, id=granted_to_id)
            permissions = Permission.objects.filter(granted_to=user)
        else:
            if request.user.role == 'CA':
                permissions = Permission.objects.filter(created_by=request.user)
            else:
                permissions = Permission.objects.filter(granted_to=request.user)

        permission_type = request.query_params.get('permission_type')
        if permission_type:
            permissions = permissions.filter(permission_type=permission_type)

        serializer = PermissionSerializer(permissions, many=True) 
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)


    


class RemovePermissionView(APIView):
    permission_classes = [IsTokenValid]

    def delete(self, request):
        if request.user.role != 'CA':
            return Response({"error": "Only CA can remove permissions."}, status=status.HTTP_403_FORBIDDEN)

        granted_to_id = request.data.get('granted_to_id')
        permission_types = request.data.get('permission_types')

        if not granted_to_id or not permission_types:
            return Response({"error": "User ID and permission types are required."}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(permission_types, list):
            return Response({"error": "Permission types should be a list."}, status=status.HTTP_400_BAD_REQUEST)

        granted_to = get_object_or_404(User, id=granted_to_id)
        not_found_permissions = []
        removed_permissions = []

        for permission_type in permission_types:
            try:
                permission = Permission.objects.get(created_by=request.user, granted_to=granted_to, permission_type=permission_type)
                permission.delete()
                removed_permissions.append(permission_type)
            except Permission.DoesNotExist:
                not_found_permissions.append(permission_type)

        if not_found_permissions:
            return Response({
                "message":f"{not_found_permissions} permissions were not found and removed this{removed_permissions}.",
                "not_found_permissions": not_found_permissions,
                "removed_permissions": removed_permissions
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Permissions removed successfully.",
            "removed_permissions": removed_permissions
        }, status=status.HTTP_204_NO_CONTENT)


    

class ChangePasswordView(APIView):
    permission_classes = [IsTokenValid]

    def post(self, request):
        current_user = request.user
        data = request.data

        if not current_user.check_password(data.get('old_password')):
            return Response({'error': 'Old password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)

        if not data.get('new_password'):
            return Response({'error': 'New password is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if data.get('new_password')!= data.get('confirm_password'):
            return Response({"error":"New password and confirm password doesn't match!!"})

        current_user.set_password(data.get('new_password'))
        current_user.save()
        return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)

class UserFilterSet(django_filters.FilterSet):
    full_name = django_filters.CharFilter(lookup_expr='icontains')
    email = django_filters.CharFilter(lookup_expr='icontains')     
    role = django_filters.CharFilter(lookup_expr='icontains') 
    uid = django_filters.CharFilter(lookup_expr='icontains')         

    class Meta:
        model = User
        fields = ['full_name', 'email', 'role','uid']

class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsTokenValid]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_class = UserFilterSet
    search_fields = ['email','full_name','role','uid']
    ordering_fields = ['created_at', 'updated_at', 'first_name']
    ordering = ['-created_at']
    def get_queryset(self):
        user = self.request.user
        show_deleted = self.request.query_params.get('show_deleted', 'false').lower() == 'true'

        if user.role == 'CA':
            if show_deleted:
                # Return only deleted users
                return User.objects.filter(is_active=False)
            else:
                # Return all users (including deleted ones)
                return User.objects.filter(is_active=True)

        elif user.role == 'AM':
            if show_deleted:
                # Return only deleted clients assigned to the AM
                return User.objects.filter(role='CLNT', assigned_to=user, is_active=False)
            else:
                # Return all clients assigned to the AM (including deleted ones)
                return User.objects.filter(role='CLNT', assigned_to=user,is_active=True)

        elif user.role == 'CLNT':
            # Clients should not see any users
            return User.objects.none()

        return User.objects.none() 
    
    def list(self, request, *args, **kwargs):
        if any(request.query_params.get(param) for param in self.filterset_class.get_filters()):
            self.pagination_class = None
        else:
            self.pagination_class = PageNumberPagination
        
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @role_based_permission('create_user')
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                self.perform_create(serializer)
                headers = self.get_success_headers(serializer.data)
                response_data = {
                    'message': 'User created successfully.',
                    'data': serializer.data
                }
                return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

        except ValidationError as e:
            return Response({'error': e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except APIException as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    # @role_based_permission('update_user')
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            response_data = {
                'message': 'User updated successfully.',
                'data': serializer.data
            }
            return Response(response_data)
        except ValidationError as e:
            return Response({'error': e.detail}, status=status.HTTP_400_BAD_REQUEST)

    @role_based_permission('delete_user')
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            instance.is_active = False
            instance.save()  # Save the instance with is_active set to False
            return Response({'message': 'User deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['patch'], detail=False)
    @role_based_permission('update_user')
    def bulk_update(self, request, *args, **kwargs):
        data = request.data
        updated_count = 0
        errors = []

        for item in data:
            user_id = item.get('id')
            user_data = item.get('data')
            try:
                user = User.objects.filter(id=user_id, is_active=True).first()
                
                if user is None:
                    raise User.DoesNotExist

                serializer = self.get_serializer(user, data=user_data, partial=True)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                updated_count += 1
            except User.DoesNotExist:
                errors.append(f"User with ID {user_id} does not exist.")
            except ValidationError as e:
                errors.append(f"Validation error for user ID {user_id}: {e.detail}")

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': f'{updated_count} users updated successfully.'}, status=status.HTTP_200_OK)

    @action(methods=['delete'], detail=False)
    @role_based_permission('delete_user')
    def bulk_delete(self, request, *args, **kwargs):
        data = request.data
        deleted_count = 0
        errors = []

        for user_id in data:
            try:
                user = User.objects.filter(id=user_id, is_active=True).first()
                
                if user is None:
                    raise User.DoesNotExist

                user.is_active = False  
                user.save()
                deleted_count += 1
            except User.DoesNotExist:
                errors.append(f"User with ID {user_id} does not exist.")
            except Exception as e:
                errors.append(f"Error deleting user with ID {user_id}: {str(e)}")

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': f'{deleted_count} users deleted successfully.'}, status=status.HTTP_200_OK)
        
    @action(methods=['post'], detail=True)
    @role_based_permission('restore_user')
    def restore(self, request, *args, **kwargs):
        user_id = self.kwargs.get('pk')
        try:
            user = User.objects.filter(id=user_id).first()
            if user is None:
                raise APIException('User not found.')

            # Restore the soft-deleted user
            user.is_active = True  # Set is_active to True for restoration
            user.save()

            response_data = {
                'message': 'User restored successfully.',
                'data': UserSerializer(user).data
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except APIException as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class AssignClientView(generics.GenericAPIView):
    serializer_class = AssignClientSerializer
    permission_classes = [IsTokenValid]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            client_id = serializer.validated_data['client_id']
            account_manager_id = serializer.validated_data['account_manager_id']

            try:
                client = User.objects.get(id=client_id.id, role='CLNT')
            except User.DoesNotExist:
                return Response({
                    'error': 'Client not found or is not a client role.'
                }, status=status.HTTP_404_NOT_FOUND)

            try:
                account_manager = User.objects.get(id=account_manager_id.id, role='AM')
            except User.DoesNotExist:
                return Response({
                    'error': 'Account Manager not found or is not an Account Manager role.'
                }, status=status.HTTP_404_NOT_FOUND)

            if request.user.role != 'CA':
                return Response({
                    'error': 'Only CAs can assign clients to Account Managers.',
                }, status=status.HTTP_403_FORBIDDEN)

            client.assigned_to = account_manager
            client.save()

            return Response({
                'message': f'Client {client.full_name} successfully assigned to Account Manager {account_manager.full_name}.'
            }, status=status.HTTP_200_OK)

        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, account_manager_id=None):
        try:
            # Ensure the account manager exists
            account_manager = User.objects.get(id=account_manager_id, role='AM')
        except User.DoesNotExist:
            return Response({
                'error': 'Account Manager not found or is not an Account Manager role.'
            }, status=status.HTTP_404_NOT_FOUND)

        # Get all clients assigned to this account manager
        clients = User.objects.filter(assigned_to=account_manager)
        
        # Debugging information
        print(f"Account Manager: {account_manager.full_name}, Clients Assigned: {[client.full_name for client in clients]}")

        # Serialize the data
        data = {
            'id': account_manager.id,
            'username': account_manager.full_name,
            'clients': ClientSerializer(clients, many=True).data
        }

        return Response(data, status=status.HTTP_200_OK)

    

class RemoveAccountManagerView(generics.GenericAPIView):
    serializer_class = RemoveAccountManagerSerializer
    permission_classes = [IsTokenValid]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            client_id = serializer.validated_data['client_id']
            account_manager_id = serializer.validated_data['account_manager_id']

            # Ensure the current user has permission to remove clients
            if request.user.role != 'CA':
                return Response({
                    'error': 'Only CAs can remove clients from Account Managers.',
                }, status=status.HTTP_403_FORBIDDEN)

            try:
                client = User.objects.get(id=client_id, role='CLNT')
                account_manager = User.objects.get(id=account_manager_id, role='AM')

                # Check if the client is assigned to the account manager
                if client.assigned_to != account_manager:
                    return Response({
                        'error': 'Client is not assigned to the specified Account Manager.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Remove the assignment
                client.assigned_to = None
                client.save()

                return Response({
                    'message': f'Client {client.full_name} successfully removed from Account Manager {account_manager.full_name}.'
                }, status=status.HTTP_200_OK)

            except User.DoesNotExist:
                return Response({
                    'error': 'Client or Account Manager not found.'
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)



