from .models import *
from .serializers import *
from rest_framework import generics
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Q
from django.core.exceptions import ValidationError
import logging



logger = logging.getLogger(__name__)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'client'):
            return Client.objects.filter(id=user.client.id)
        return Client.objects.none()


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

        # إذا كان المستخدم سائقًا
        if hasattr(user, 'driver'):
            return Trip.objects.filter(driver=user.driver)

        # إذا كان المستخدم عميلًا
        elif hasattr(user, 'client'):
            return Trip.objects.filter(booking__client=user.client).distinct()

        # إذا كان المستخدم مديرًا (نفترض أنه ليس له علاقة بـ driver أو client)
        elif user.is_staff or user.is_superuser:
            return Trip.objects.all()

        # إذا لم ينطبق عليه أي من الأدوار
        return Trip.objects.none()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_update(serializer)

            # تحديث المقاعد المتاحة بعد أي تعديل
            instance.refresh_from_db()

            return Response(serializer.data)

        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error updating trip: {str(e)}")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class BookingViewSet(viewsets.ModelViewSet):
    """
    واجهة للتعامل مع الحجوزات مع فلترة حسب المستخدم والحالة
    """
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    queryset = Booking.objects.all()

    def get_queryset(self):
        """
        فلترة الحجوزات حسب:
        - إذا كان المستخدم عميلاً: يعرض حجوزاته فقط
        - إذا كان المستخدم سائقاً: يعرض حجوزات رحلاته فقط
        - إذا كان مديراً: يعرض جميع الحجوزات
        مع إمكانية تصفية حسب الحالة
        """
        user = self.request.user
        queryset = super().get_queryset()
        
        # فلترة الحالة إذا كانت موجودة في البارامترات
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status=status)
        
        # إذا كان المستخدم عميلاً
        if hasattr(user, 'client'):
            return queryset.filter(customer=user.client)
        
        # إذا كان المستخدم سائقاً
        elif hasattr(user, 'driver'):
            return queryset.filter(trip__driver=user.driver)
        
        # إذا كان مديراً أو لا ينتمي لأي نوع معين
        return queryset

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
        token = request.data.get('fcm_token')
        device_info = request.data.get('device_info', {})

        if not token:
            return Response({"error": "FCM token is required"}, status=400)

        # هنا نحفظ أو نحدّث التوكن للمستخدم
        FCMToken.objects.update_or_create(
            token=token,
            defaults={
                'user': request.user,
                'device_info': device_info
            }
        )
        return Response({"message": "FCM token saved successfully"}, status=200)
