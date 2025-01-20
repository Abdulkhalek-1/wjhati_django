from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.schemas import get_schema_view
from .views import *

router = DefaultRouter()

# مسارات المصادقة
router.register(r'auth/users', CustomUserViewSet, basename='auth-users')

# مسارات المستخدمين
router.register(r'clients', ClientViewSet, basename='clients')
router.register(r'drivers', DriverViewSet, basename='drivers')

# مسارات النظام المالي
router.register(r'wallets', WalletViewSet, basename='wallets')
router.register(r'transactions', TransactionViewSet, basename='transactions')
# مسارات النقل
router.register(r'vehicles', VehicleViewSet, basename='vehicles')
router.register(r'trips', TripViewSet, basename='trips')
router.register(r'trip-stops', TripStopViewSet, basename='trip-stops')

# مسارات الحجوزات
router.register(r'bookings', BookingViewSet, basename='bookings')
router.register(r'cash-bookings', CasheBookingViewSet, basename='cash-bookings')

# مسارات الدعم
router.register(r'support-tickets', SupportTicketViewSet, basename='support-tickets')

# مسارات الاشتراكات
router.register(r'subscription-plans', SubscriptionPlanViewSet, basename='subscription-plans')
router.register(r'subscriptions', SubscriptionViewSet, basename='subscriptions')

# مسارات التقييمات
router.register(r'ratings', RatingViewSet, basename='ratings')

# مسارات الشحن
router.register(r'item-deliveries', ItemDeliveryViewSet, basename='item-deliveries')
router.register(r'cash-deliveries', CasheItemDeliveryViewSet, basename='cash-deliveries')

# مسارات التواصل
router.register(r'chats', ChatViewSet, basename='chats')
router.register(r'messages', MessageViewSet, basename='messages')

# التوثيق التلقائي
schema_view = get_schema_view(title="Transportation API")

urlpatterns = [
    # المصادقة
    path('auth/register/', CreateUserView.as_view(), name='register'),
    
    # المعاملات المالية
    path('financial/transactions/', TransactionView.as_view(), name='create-transaction'),
    path('financial/transfers/', TransferView.as_view(), name='create-transfer'),
    
    # التوثيق
    path('docs/', schema_view, name='api-docs'),
    
    # المسارات الأساسية
    path('', include(router.urls)),
]