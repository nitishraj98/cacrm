from rest_framework import viewsets,status,generics,filters
from rest_framework.response import Response
from .models import *
from .serializers import *
from user.permissions import *
from django.shortcuts import get_object_or_404
from user.decorators import *
from django_filters.rest_framework import DjangoFilterBackend
from django.db import IntegrityError,transaction
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.exceptions import APIException




class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsTokenValid]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['user', 'company']
    search_fields = ['user__full_name', 'content','company']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        show_deleted = self.request.query_params.get('show_deleted', 'false').lower() == 'true'

        if user.role in ['CA', 'AM']:
            if show_deleted:
                return Comment.objects.filter(deleted_at__isnull=False)
            else:
                return Comment.objects.filter(deleted_at__isnull=True)
        
        elif user.role == 'CLNT':
            if show_deleted:
                return Comment.objects.filter(company__client=user, deleted_at__isnull=False)
            else:
                return Comment.objects.filter(company__client=user, deleted_at__isnull=True)
        
        return Comment.objects.none()

    @role_based_permission('create_comment')
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                serializer.save(user=request.user)
                headers = self.get_success_headers(serializer.data)
                response_data = {
                    'message': 'Comment created successfully.',
                    'data': serializer.data
                }
                return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

        except IntegrityError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response({'error': e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except APIException as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @role_based_permission('update_comment')
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            response_data = {
                'message': 'Comment updated successfully.',
                'data': serializer.data
            }
            return Response(response_data)
        except ValidationError as e:
            return Response({'error': e.detail}, status=status.HTTP_400_BAD_REQUEST)

    @role_based_permission('delete_comment')
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            # Use soft delete method provided by the softdelete library
            instance.delete()
            return Response({'message': 'Comment deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['patch'], detail=False)
    @role_based_permission('update_comment')
    def bulk_update(self, request, *args, **kwargs):
        data = request.data
        updated_count = 0
        errors = []

        for item in data:
            comment_id = item.get('id')
            comment_data = item.get('data')
            try:
                comment = Comment.objects.filter(id=comment_id).first()
                if not comment:
                    errors.append(f"Comment with ID {comment_id} does not exist.")
                    continue

                serializer = self.get_serializer(comment, data=comment_data, partial=True)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                updated_count += 1
            except ValidationError as e:
                errors.append(f"Validation error for comment ID {comment_id}: {e.detail}")

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': f'{updated_count} comments updated successfully.'}, status=status.HTTP_200_OK)


    @action(methods=['delete'], detail=False)
    @role_based_permission('delete_comment')
    def bulk_delete(self, request, *args, **kwargs):
        data = request.data
        deleted_count = 0
        errors = []

        for comment_id in data:
            try:
                comment = Comment.objects.filter(id=comment_id).first()
                if not comment:
                    errors.append(f"Comment with ID {comment_id} does not exist.")
                    continue

                comment.delete()
                deleted_count += 1
            except Exception as e:
                errors.append(f"Error deleting comment with ID {comment_id}: {str(e)}")

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': f'{deleted_count} comments deleted successfully.'}, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=True)
    @role_based_permission('restore_comment')
    def restore(self, request, *args, **kwargs):
        comment_id = self.kwargs.get('pk')
        try:
            comment = Comment.deleted_objects.filter(id=comment_id).first()
            if not comment:
                raise APIException('Comment not found.')

            if not comment.is_deleted:
                raise APIException('Comment is not deleted.')

            with transaction.atomic():
                comment.restore()

            return Response({
                'message': 'Comment restored successfully.',
                'data': CommentSerializer(comment).data
            }, status=status.HTTP_200_OK)

        except APIException as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
