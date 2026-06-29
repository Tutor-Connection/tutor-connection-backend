from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, CommissionViewSet, WalletViewSet

router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payments')
router.register(r'commissions', CommissionViewSet, basename='commissions')
router.register(r'wallets', WalletViewSet, basename='wallets')

urlpatterns = [
    path('', include(router.urls)),
]