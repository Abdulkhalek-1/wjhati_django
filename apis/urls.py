from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *
from .views import WalletViewSet,TransactionViewSet

router = DefaultRouter()
router.register(r'wallets', WalletViewSet, basename='wallet')
router.register(r'user', UserViewSet)
router.register(r'clients', ClientViewSet)
router.register(r'transactions', TransactionViewSet, basename='Transaction')
router.register(r'vehicles', VehicleViewSet)
router.register(r'drivers', DriverViewSet,basename='Driver')
router.register(r'trips', TripViewSet,basename='Trip')
router.register(r'bookings', BookingViewSet , basename='Booking')
router.register(r'ratings', RatingViewSet)
router.register(r'chats', ChatViewSet ,basename='Chat')
router.register(r'messages', MessageViewSet)
router.register(r'support-tickets', SupportTicketViewSet)
router.register(r'notifications', NotificationViewSet, basename='Notification')
router.register(r'transfers', TransferViewSet)
router.register(r'subscription-plans', SubscriptionPlanViewSet)
router.register(r'subscriptions', SubscriptionViewSet)
router.register(r'bonuses', BonusViewSet)
router.register(r'trip-stops', TripStopViewSet)
router.register(r'item-deliveries', ItemDeliveryViewSet)
router.register(r'cashe-bookings', CasheBookingViewSet)
router.register(r'cashe-item-deliveries', CasheItemDeliveryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]