from rest_framework import viewsets,status,generics,filters
from rest_framework.response import Response
from .models import *
from .serializers import *
from user.permissions import *
from user.decorators import *
from django_filters.rest_framework import DjangoFilterBackend
from django.db import IntegrityError,transaction
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
import django_filters

class CompanyFilterSet(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains') 
    registration_number = django_filters.CharFilter(lookup_expr='icontains')    
    gst_number = django_filters.CharFilter(lookup_expr='icontains') 
    cid = django_filters.CharFilter(lookup_expr='icontains')        

    class Meta:
        model = Company
        fields = ['name', 'registration_number', 'gst_number','cid']
 

class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer
    permission_classes = [IsTokenValid]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_class = CompanyFilterSet
    search_fields = ['name', 'registration_number', 'gst_number','cid']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        show_deleted = self.request.query_params.get('show_deleted', 'false').lower() == 'true'

        if user.role == 'CA':
            if show_deleted:
                # Show only deleted companies
                return Company.objects.filter(deleted_at__isnull=False)
            else:
                # Show only non-deleted companies
                return Company.objects.filter(deleted_at__isnull=True)

        elif user.role == 'AM':
            if show_deleted:
                # Show only deleted companies assigned to the AM
                return Company.objects.filter(deleted_at__isnull=False, account_manager=user)
            else:
                # Show only non-deleted companies assigned to the AM
                return Company.objects.filter(deleted_at__isnull=True, account_manager=user)

        elif user.role == 'CLNT':
            if show_deleted:
                # Show only deleted companies assigned to the client
                return Company.objects.filter(deleted_at__isnull=False, client=user)
            else:
                # Show only non-deleted companies assigned to the client
                return Company.objects.filter(deleted_at__isnull=True, client=user)

        return Company.objects.none()


    @role_based_permission('create_company')
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                self.perform_create(serializer)
                headers = self.get_success_headers(serializer.data)
                response_data = {
                    'message': 'Company created successfully.',
                    'data': serializer.data
                }
                return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

        except ValidationError as e:
            return Response({'error': e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except APIException as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @role_based_permission('update_company')
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            response_data = {
                'message': 'Company updated successfully.',
                'data': serializer.data
            }
            return Response(response_data)
        except ValidationError as e:
            return Response({'error': e.detail}, status=status.HTTP_400_BAD_REQUEST)

    @role_based_permission('delete_company')
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            # Use soft delete method provided by the softdelete library
            instance.delete()
            return Response({'message': 'Company deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['patch'], detail=False)
    @role_based_permission('update_company')
    def bulk_update(self, request, *args, **kwargs):
        data = request.data
        updated_count = 0
        errors = []

        for item in data:
            company_id = item.get('id')
            company_data = item.get('data')
            try:
                # Use the correct manager for soft-deleted records
                company = Company.all_objects.filter(id=company_id).first()
                if company is None:
                    errors.append(f"Company with ID {company_id} does not exist.")
                    continue

                serializer = self.get_serializer(company, data=company_data, partial=True)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                updated_count += 1
            except ValidationError as e:
                errors.append(f"Validation error for company ID {company_id}: {e.detail}")

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': f'{updated_count} companies updated successfully.'}, status=status.HTTP_200_OK)


    @action(methods=['delete'], detail=False)
    @role_based_permission('delete_company')
    def bulk_delete(self, request, *args, **kwargs):
        data = request.data
        deleted_count = 0
        errors = []

        for company_id in data:
            try:
                company = Company.all_objects.filter(id=company_id).first() 
                if company is None:
                    errors.append(f"Company with ID {company_id} does not exist.")
                    continue

                company.delete() 
                deleted_count += 1
            except Exception as e:
                errors.append(f"Error deleting company with ID {company_id}: {str(e)}")

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': f'{deleted_count} companies deleted successfully.'}, status=status.HTTP_200_OK)

    

    @action(methods=['post'], detail=True)
    @role_based_permission('restore_company')
    def restore(self, request, *args, **kwargs):
        company_id = self.kwargs.get('pk')
        try:
            # Fetch the company including soft-deleted ones using deleted_objects manager
            company = Company.deleted_objects.filter(id=company_id).first()
            if company is None:
                raise APIException('Company not found.')

            # Check if the company is actually soft-deleted
            if not company.is_deleted:
                raise APIException('Company is not deleted.')

            # Restore the soft-deleted company
            with transaction.atomic():
                company.restore() 

            response_data = {
                'message': 'Company restored successfully.',
                'data': CompanySerializer(company).data
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except APIException as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)




class AssignCompaniesToAMView(generics.GenericAPIView):
    serializer_class = AssignCompaniesSerializer
    permission_classes = [IsTokenValid]

    def post(self, request, *args, **kwargs):
        # Check user role
        user = request.user
        if user.role not in ['CA', 'AM']:
            return Response({
                'error': 'You do not have permission to assign companies to Account Managers.'
            }, status=status.HTTP_403_FORBIDDEN)

        # Validate input data
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            account_manager_id = serializer.validated_data['account_manager_id']
            company_ids = serializer.validated_data['company_ids']

            try:
                account_manager = User.objects.get(id=account_manager_id, role='AM')
                companies = Company.objects.filter(id__in=company_ids)

                # Assign each company to the Account Manager
                for company in companies:
                    company.account_manager = account_manager
                    company.save()

                return Response({
                    'message': f'Companies successfully assigned to Account Manager {account_manager.full_name}.'
                }, status=status.HTTP_200_OK)

            except User.DoesNotExist:
                return Response({
                    'error': 'Account Manager not found or invalid Account Manager ID.'
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, account_manager_id=None):
        try:
            # Ensure the account manager exists
            account_manager = User.objects.get(id=account_manager_id, role='AM')
        except User.DoesNotExist:
            return Response({
                'error': 'Account Manager not found or invalid Account Manager ID.'
            }, status=status.HTTP_404_NOT_FOUND)

        # Get all companies assigned to this account manager
        companies = Company.objects.filter(account_manager=account_manager)

        # Serialize the data
        data = {
            'id': account_manager.id,
            'name': account_manager.full_name,
            'companies': CompanySerializer(companies, many=True).data
        }

        return Response(data, status=status.HTTP_200_OK)


    

class RemoveCompaniesFromAMView(generics.GenericAPIView):
    serializer_class = RemoveCompaniesFromAMSerializer
    permission_classes = [IsTokenValid]

    def post(self, request, *args, **kwargs):
        # Check user role
        user = request.user
        if user.role not in ['CA', 'AM']:
            return Response({
                'error': 'You do not have permission to remove companies from Account Managers.'
            }, status=status.HTTP_403_FORBIDDEN)

        # Validate input data
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            account_manager_id = serializer.validated_data['account_manager_id']
            company_ids = serializer.validated_data['company_ids']

            try:
                account_manager = User.objects.get(id=account_manager_id, role='AM')
                companies = Company.objects.filter(id__in=company_ids)

                # Remove each company from the Account Manager
                for company in companies:
                    if company.account_manager == account_manager:
                        company.account_manager = None
                        company.save()

                return Response({
                    'message': f'Companies successfully removed from Account Manager {account_manager.full_name}'
                }, status=status.HTTP_200_OK)

            except User.DoesNotExist:
                return Response({
                    'error': 'Account Manager not found or invalid Account Manager ID.'
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    


class RemoveCompaniesFromClientView(generics.GenericAPIView):
    serializer_class = RemoveCompaniesSerializer
    permission_classes = [IsTokenValid]

    def post(self, request, *args, **kwargs):
        user = request.user
        if user.role not in ['CA', 'AM']:
            return Response({
                'error': 'You do not have permission to remove companies from clients.'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            client_id = serializer.validated_data['client_id']
            company_ids = serializer.validated_data['company_ids']

            try:
                client = User.objects.get(id=client_id, role='CLNT')
                companies = Company.objects.filter(id__in=company_ids)

                for company in companies:
                    if company.client == client:
                        company.client = None
                        company.save()

                return Response({
                    'message': f'Companies successfully removed from client {client.full_name}.'
                }, status=status.HTTP_200_OK)

            except User.DoesNotExist:
                return Response({
                    'error': 'Client not found or invalid client ID.'
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    


class ClientCompaniesAndDocumentsView(generics.GenericAPIView):
    serializer_class = ClientCompanySerializer
    permission_classes = [IsTokenValid]

    def get(self, request, *args, **kwargs):
        user = request.user 
        client_id = request.query_params.get('client_id')

        if not client_id:
            return Response({
                'error': 'Client ID is required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            client = User.objects.get(id=client_id, role='CLNT')
        except User.DoesNotExist:
            return Response({
                'error': 'Client not found or invalid Client ID.'
            }, status=status.HTTP_404_NOT_FOUND)

        if user.role == 'CA':
            companies = Company.all_objects.filter(deleted_at__isnull=True)

        elif user.role == 'AM':
            companies = Company.all_objects.filter(account_manager=user, deleted_at__isnull=True)

        elif user.role == 'CLNT':
            companies = Company.all_objects.filter(client=client, deleted_at__isnull=True)

        else:
            return Response({
                'error': 'You do not have permission to view these companies.'
            }, status=status.HTTP_403_FORBIDDEN)

        # Serialize the filtered company data
        serializer = self.get_serializer(companies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)




class ClientsCompanyViewSet(generics.ListAPIView):
    serializer_class = ClientCompanylistSerializer
    permission_classes = [IsTokenValid]
    pagination_class = None

    def get_queryset(self):
        client_id = self.request.query_params.get('client_id')  
        if client_id:
            try:
                client = User.objects.get(id=client_id, role='CLNT')
                return Company.objects.filter(client=client, deleted_at__isnull=True)
            except User.DoesNotExist:
                return Company.objects.none()
        return Company.objects.none()
    


class ClientCompaniesAndDocumentsCommentsView(generics.GenericAPIView):
    serializer_class = ClientCompanySerializer
    permission_classes = [IsTokenValid]

    def get(self, request, *args, **kwargs):
        user = request.user
        company_id = request.query_params.get('company_id')

        if not company_id:
            return Response({
                'error': 'Company ID is required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get the company by ID and ensure it hasn't been soft-deleted
        try:
            company = Company.all_objects.get(id=company_id, deleted_at__isnull=True)
        except Company.DoesNotExist:
            return Response({
                'error': 'Company not found or has been deleted.'
            }, status=status.HTTP_404_NOT_FOUND)

        # Role-based access control
        if user.role == 'CA':
            pass  # CAs have access to all companies, no further filtering needed

        elif user.role == 'AM' and company.account_manager != user:
            return Response({
                'error': 'You do not have permission to view this company.'
            }, status=status.HTTP_403_FORBIDDEN)

        elif user.role == 'CLNT' and company.client != user:
            return Response({
                'error': 'You do not have permission to view this company.'
            }, status=status.HTTP_403_FORBIDDEN)

        else:
            return Response({
                'error': 'You do not have permission to view these companies.'
            }, status=status.HTTP_403_FORBIDDEN)

        # Serialize the company data along with related documents and comments
        serializer = self.get_serializer(company)
        return Response(serializer.data, status=status.HTTP_200_OK)