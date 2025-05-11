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
from rest_framework.views import APIView
import logging

logger = logging.getLogger(__name__)

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
    serializer_class = DriverSerializer
    queryset = Driver.objects.all()

class TripViewSet(viewsets.ModelViewSet):
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        driver = getattr(user, 'driver', None)
        if driver:
            return Trip.objects.filter(driver=driver)
        return Trip.objects.none()

class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(customer=self.request.user, status='confirmed')

class RatingViewSet(viewsets.ModelViewSet):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer

class ChatViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Chat.objects.filter(participants=self.request.user)

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

class SupportTicketViewSet(viewsets.ModelViewSet):
    queryset = SupportTicket.objects.all()
    serializer_class = SupportTicketSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Notification.objects.filter(user=user)

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



class SaveFCMTokenView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        token = request.data.get('token')
        
        if not token:
            logger.warning('Attempt to save FCM token without providing token')
            return Response(
                {'error': 'Token is required.', 'code': 'missing_token'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if not isinstance(token, str) or len(token) < 10:
            logger.warning(f'Invalid token format: {token}')
            return Response(
                {'error': 'Invalid token format.', 'code': 'invalid_token'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            obj, created = FCMToken.objects.update_or_create(
                token=token,
                defaults={'user': request.user}
            )
            
            logger.info(f'FCM token {"created" if created else "updated"} for user {request.user.id}')
            
            return Response({
                'message': 'Token saved successfully.',
                'created': created,
                'token_id': obj.id
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f'Error saving FCM token: {str(e)}', exc_info=True)
            return Response(
                {'error': 'Failed to save token.', 'code': 'server_error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )