from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'companies', CompanyViewSet, basename='companies')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/assign-companies/', AssignCompaniesToAMView.as_view(), name='assign-companies-to-client'),
    path('api/assign-companies/<int:account_manager_id>/', AssignCompaniesToAMView.as_view(), name='companies-for-am'),
    path('api/remove-companies-from-am/', RemoveCompaniesFromAMView.as_view(), name='remove-companies-from-am'),
    path('api/remove-companies-from-client/', RemoveCompaniesFromClientView.as_view(), name='remove-companies-from-client'),
    path('api/client-companies-documents/', ClientCompaniesAndDocumentsView.as_view(), name='client-companies-documents'),
    path('api/client-companies/', ClientsCompanyViewSet.as_view(), name='client-companies'),
    path('api/companies-details/', ClientCompaniesAndDocumentsCommentsView.as_view(), name='companies-details'),

]
