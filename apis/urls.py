from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *  # Import all views
from .views import SupportTicketViewSet  # Explicitly import SupportTicketViewSet

router = DefaultRouter()
router.register(r'wallets', WalletViewSet, basename='wallet')
router.register(r'user', UserViewSet)
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'transactions', TransactionViewSet, basename='Transaction')
router.register(r'vehicles', VehicleViewSet)
router.register(r'drivers', DriverViewSet,basename='Driver')
router.register(r'trips', TripViewSet,basename='Trip')
router.register(r'bookings', BookingViewSet , basename='Booking')
router.register(r'ratings', RatingViewSet, basename='Rating')
router.register(r'support-tickets', SupportTicketViewSet, basename='SupportTicket')
router.register(r'notifications', NotificationViewSet, basename='Notification')
router.register(r'transfers', TransferViewSet, basename='Transfer')
router.register(r'subscription-plans', SubscriptionPlanViewSet, basename='SubscriptionPlan')
router.register(r'subscriptions', SubscriptionViewSet, basename='Subscription')
router.register(r'bonuses', BonusViewSet, basename='Bonus')
router.register(r'trip-stops', TripStopViewSet, basename='TripStop')
router.register(r'item-deliveries', ItemDeliveryViewSet, basename='ItemDelivery')
router.register(r'cashe-bookings', CasheBookingViewSet, basename='CasheBooking')
router.register(r'cashe-item-deliveries', CasheItemDeliveryViewSet, basename='CasheItemDelivery')

urlpatterns = [
    path('', include(router.urls)),
    path('chats/', ChatListAPIView.as_view(), name='chat-list'),
    path('messages/', MessageListAPIView.as_view(), name='message-list'),
]