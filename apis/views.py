from rest_framework import viewsets
from .models import *
from .serializers import *
from rest_framework import generics
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Wallet
from .serializers import WalletSerializer
from rest_framework.permissions import IsAuthenticated
from .models import Trip

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer


class WalletViewSet(viewsets.ModelViewSet):
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Wallet.objects.filter(user=user)

    def retrieve(self, request, *args, **kwargs):
        wallet = self.get_queryset().first()
        if wallet:
            serializer = self.get_serializer(wallet)
            return Response(serializer.data)
        else:
            return Response({"detail": "المحفظة غير موجودة."}, status=status.HTTP_404_NOT_FOUND)
        
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
    queryset = Booking.objects.filter(status='confirmed')
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

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
