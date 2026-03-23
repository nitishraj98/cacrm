from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from .models import Permission


def role_based_permission(action):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(self, request, *args, **kwargs):
            current_user = request.user
            print(f"Action: {action}, Current User Role: {current_user.role}") 

            if current_user.role == 'CA':
                print("CA role detected, proceeding with the operation.")  
                return view_func(self, request, *args, **kwargs)

            if current_user.role == 'AM':
                if Permission.objects.filter(granted_to=current_user, permission_type=action).exists():
                    print("Permission granted to AccountManager, proceeding.")  
                    return view_func(self, request, *args, **kwargs)
                else:
                    print("Permission denied for AccountManager.") 
                    return Response({"error": f"You do not have permission to {action.replace('_', ' ')}."},
                                    status=status.HTTP_403_FORBIDDEN)

            if current_user.role == 'CLNT':
                allowed_client_actions = {'create_comment', 'create_document'}
                if action in allowed_client_actions:
                    print("Client allowed for action, proceeding.")
                    return view_func(self, request, *args, **kwargs)
                print("Permission denied, client role detected.") 
                return Response({"error": "Clients do not have permission to perform this action."}, 
                                status=status.HTTP_403_FORBIDDEN)

            print("Permission denied, unknown role.") 
            return Response({"error": "You do not have permission to perform this action."}, 
                            status=status.HTTP_403_FORBIDDEN)

        return _wrapped_view
    return decorator
