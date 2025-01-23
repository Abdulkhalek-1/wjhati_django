from rest_framework import viewsets
from .models import (
    CustomUser, Client, Wallet, Transaction, Vehicle, Driver, Trip, Booking,
    Rating, Chat, Message, SupportTicket, Notification, Transfer, SubscriptionPlan,
    Subscription, Bonus, TripStop, ItemDelivery, CasheBooking, CasheItemDelivery
)
from .serializers import (
    CustomUserSerializer, ClientSerializer, WalletSerializer, TransactionSerializer,
    VehicleSerializer, DriverSerializer, TripSerializer, BookingSerializer,
    RatingSerializer, ChatSerializer, MessageSerializer, SupportTicketSerializer,
    NotificationSerializer, TransferSerializer, SubscriptionPlanSerializer,
    SubscriptionSerializer, BonusSerializer, TripStopSerializer, ItemDeliverySerializer,
    CasheBookingSerializer, CasheItemDeliverySerializer
)

class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

class WalletViewSet(viewsets.ModelViewSet):
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer

class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

class RatingViewSet(viewsets.ModelViewSet):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer

class ChatViewSet(viewsets.ModelViewSet):
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

class SupportTicketViewSet(viewsets.ModelViewSet):
    queryset = SupportTicket.objects.all()
    serializer_class = SupportTicketSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

class TransferViewSet(viewsets.ModelViewSet):
    queryset = Transfer.objects.all()
    serializer_class = TransferSerializer

class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer

class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer

class BonusViewSet(viewsets.ModelViewSet):
    queryset = Bonus.objects.all()
    serializer_class = BonusSerializer

class TripStopViewSet(viewsets.ModelViewSet):
    queryset = TripStop.objects.all()
    serializer_class = TripStopSerializer

class ItemDeliveryViewSet(viewsets.ModelViewSet):
    queryset = ItemDelivery.objects.all()
    serializer_class = ItemDeliverySerializer

class CasheBookingViewSet(viewsets.ModelViewSet):
    queryset = CasheBooking.objects.all()
    serializer_class = CasheBookingSerializer

class CasheItemDeliveryViewSet(viewsets.ModelViewSet):
    queryset = CasheItemDelivery.objects.all()
    serializer_class = CasheItemDeliverySerializer