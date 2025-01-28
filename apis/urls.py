from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'clients', ClientViewSet)
router.register(r'wallets', WalletViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'vehicles', VehicleViewSet)
router.register(r'drivers', DriverViewSet)
router.register(r'trips', TripViewSet)
router.register(r'bookings', BookingViewSet)
router.register(r'ratings', RatingViewSet)
router.register(r'chats', ChatViewSet)
router.register(r'messages', MessageViewSet)
router.register(r'support-tickets', SupportTicketViewSet)
router.register(r'notifications', NotificationViewSet)
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