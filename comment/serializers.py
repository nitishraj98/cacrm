from rest_framework import serializers
from comment.models import Comment

class CommentSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'user', 'username', 'role', 'content', 'created_at', 'updated_at', 'company']
        read_only_fields = ['user']

    def get_username(self, obj):
        return obj.user.full_name if obj.user else ""

    def get_role(self, obj):
        return obj.user.role if obj.user else ""
