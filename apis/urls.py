from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'users', CustomUserViewSet)
router.register(r'clients', ClientViewSet)
router.register(r'wallets', WalletViewSet)
router.register(r'vehicles', VehicleViewSet)
router.register(r'drivers', DriverViewSet)
router.register(r'bonuses', BonusViewSet)
router.register(r'trips', TripViewSet)
router.register(r'trip-stops', TripStopViewSet)
router.register(r'ratings', RatingViewSet)
router.register(r'supports', SupportViewSet)
router.register(r'subscription-plans', SubscriptionPlanViewSet)
router.register(r'subscriptions', SubscriptionViewSet)
router.register(r'bookings', BookingViewSet)
router.register(r'cashe-bookings', CasheBookingViewSet)
router.register(r'item-deliveries', ItemDeliveryViewSet)
router.register(r'cashe-item-deliveries', CasheItemDeliveryViewSet)
router.register(r'chats', ChatViewSet)
router.register(r'messages', MessageViewSet)

urlpatterns = [
    path('', include(router.urls)),
]