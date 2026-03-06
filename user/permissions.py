from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.exceptions import AuthenticationFailed
from .models import BlacklistedToken

class IsTokenValid(BasePermission):
    def has_permission(self, request, view):
        auth_header = request.headers.get('Authorization')

        if auth_header:
            if isinstance(auth_header, str) and auth_header.startswith('Bearer '):
                token = auth_header[len('Bearer '):].strip()

                if BlacklistedToken.objects.filter(token=token).exists():
                    raise AuthenticationFailed('Token is blacklisted')

                try:
                    AccessToken(token)
                    return True
                except (IndexError, ValueError, AuthenticationFailed):
                    raise AuthenticationFailed('Invalid token')
            else:
                raise AuthenticationFailed('Authorization header must start with Bearer')
        return False



class IsCA(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'CA'

class IsAccountManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'AccountManager'

class IsClient(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'Client'
