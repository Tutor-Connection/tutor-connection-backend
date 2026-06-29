from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SupportTicketViewSet, ReviewReportViewSet

router = DefaultRouter()
router.register(r'tickets', SupportTicketViewSet, basename='ticket')
router.register(r'reports', ReviewReportViewSet, basename='report')

urlpatterns = [
    path('', include(router.urls)),
]