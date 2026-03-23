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



class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [IsTokenValid]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['company', 'category']
    search_fields = ['company__name', 'category']
    ordering_fields = ['uploaded_at', 'category']
    ordering = ['-uploaded_at']

    def get_queryset(self):
        user = self.request.user
        show_deleted = self.request.query_params.get('show_deleted', 'false').lower() == 'true'

        if user.role in ['CA', 'AM']:
            if show_deleted:
                # Show only deleted documents
                return Document.deleted_objects.all()
            else:
                # Show only non-deleted documents
                return Document.objects.filter(deleted_at__isnull=True)
        
        elif user.role == 'CLNT':
            if show_deleted:
                # Show only deleted documents assigned to the client
                return Document.deleted_objects.filter(company__client=user)
            else:
                # Show only non-deleted documents assigned to the client
                return Document.objects.filter(company__client=user, deleted_at__isnull=True)
        
        return Document.objects.none()

    @role_based_permission('create_document')
    def create(self, request, *args, **kwargs):
        files = request.FILES.getlist('documents')
        if not files:
            return Response({'error': 'No documents provided.'}, status=status.HTTP_400_BAD_REQUEST)

        created_documents = []
        errors = []

        try:
            with transaction.atomic():
                for file in files:
                    data = {
                        'company': request.data.get('company'),
                        'file': file,
                        'category': request.data.get('category')
                    }
                    serializer = self.get_serializer(data=data)
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
                    created_documents.append(serializer.data)

            return Response({
                'message': f'{len(created_documents)} documents uploaded successfully.',
                'data': created_documents
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({'error': e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


    @role_based_permission('update_document')
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({
                'message': 'Document updated successfully.',
                'data': serializer.data
            })
        except ValidationError as e:
            return Response({'error': e.detail}, status=status.HTTP_400_BAD_REQUEST)

    @role_based_permission('delete_document')
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            instance.delete()
            return Response({'message': 'Document deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['patch'], detail=False)
    @role_based_permission('update_document')
    def bulk_update(self, request, *args, **kwargs):
        data = request.data
        updated_count = 0
        errors = []

        # Extract file uploads
        files = request.FILES.getlist('documents')

        for item in data:
            document_id = item.get('id')
            document_data = item.get('data')
            try:
                document = Document.objects.filter(id=document_id).first()
                if not document:
                    errors.append(f"Document with ID {document_id} does not exist.")
                    continue

                # Handle file updates
                if 'file' in document_data:
                    # Update file from request.FILES
                    new_file = request.FILES.get(document_data['file'])
                    if new_file:
                        document.file.save(new_file.name, new_file, save=True)

                # Update other fields
                serializer = self.get_serializer(document, data=document_data, partial=True)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                updated_count += 1
            except ValidationError as e:
                errors.append(f"Validation error for document ID {document_id}: {e.detail}")

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': f'{updated_count} documents updated successfully.'}, status=status.HTTP_200_OK)


    @action(methods=['delete'], detail=False)
    @role_based_permission('delete_document')
    def bulk_delete(self, request, *args, **kwargs):
        data = request.data
        deleted_count = 0
        errors = []

        for document_id in data:
            try:
                document = Document.objects.filter(id=document_id).first()
                if not document:
                    errors.append(f"Document with ID {document_id} does not exist.")
                    continue

                document.delete()
                deleted_count += 1
            except Exception as e:
                errors.append(f"Error deleting document with ID {document_id}: {str(e)}")

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': f'{deleted_count} documents deleted successfully.'}, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=True)
    @role_based_permission('restore_document')
    def restore(self, request, *args, **kwargs):
        document_id = self.kwargs.get('pk')
        try:
            document = Document.deleted_objects.filter(id=document_id).first()
            if not document:
                raise APIException('Document not found.')

            if not document.is_deleted:
                raise APIException('Document is not deleted.')

            with transaction.atomic():
                document.restore()

            return Response({
                'message': 'Document restored successfully.',
                'data': DocumentSerializer(document).data
            }, status=status.HTTP_200_OK)

        except APIException as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

