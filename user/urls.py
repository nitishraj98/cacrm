from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'register/ca', CARegistrationViewSet, basename='ca-registration')
router.register(r'users', UserViewSet, basename='users')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/login/', CustomLoginView.as_view(), name='login'),
    path('api/logout/', LogoutAPIView.as_view(), name='logout'),
    path('api/permissions/', GrantPermissionView.as_view(), name='grant-permission'),
    path('api/permissions/remove/', RemovePermissionView.as_view(), name='remove-permission'),
    path('api/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('api/assign-client/', AssignClientView.as_view(), name='assign-client'),
    path('api/assign-client/<int:account_manager_id>/', AssignClientView.as_view(), name='assigned-clients'),
    path('api/remove-assign-client/', RemoveAccountManagerView.as_view(), name='remove-account-manager'),
]
