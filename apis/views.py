from .models import Chat, Message, FCMToken, Wallet, Transaction, Vehicle, Driver, Trip, Booking, Rating, SupportTicket, Notification, Transfer, SubscriptionPlan, Subscription, Bonus, TripStop, ItemDelivery, CasheBooking, CasheItemDelivery
from .serializers import ChatSerializer, MessageSerializer, UserSerializer, ClientSerializer, WalletSerializer, TransactionSerializer, VehicleSerializer, DriverSerializer, TripSerializer, BookingSerializer, RatingSerializer, SupportTicketSerializer, NotificationSerializer, TransferSerializer, SubscriptionPlanSerializer, SubscriptionSerializer, BonusSerializer, TripStopSerializer, ItemDeliverySerializer, CasheBookingSerializer, CasheItemDeliverySerializer
from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Q, Count, Prefetch
from django.contrib.auth import get_user_model
import logging

User = get_user_model()

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
        messages_prefetch = Prefetch(
            'messages',
            queryset=Message.objects.order_by('-created_at')
        )
        return Chat.objects.prefetch_related(messages_prefetch)

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
    queryset = Trip.objects.all()

class BookingViewSet(viewsets.ModelViewSet):
    """
    واجهة للتعامل مع الحجوزات مع فلترة حسب المستخدم والحالة
    """
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

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



class ChatListAPIView(generics.ListAPIView):
    serializer_class = ChatSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # ارجع كل المحادثات التي يشارك فيها المستخدم مرتبة حسب آخر تحديث
        return Chat.objects.filter(participants=self.request.user).order_by('-updated_at')


class MessageListAPIView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        chat_id = self.kwargs['chat_id']
        # تأكد من أن المستخدم مشارك في المحادثة
        chat = Chat.objects.filter(id=chat_id, participants=self.request.user).first()
        if not chat:
            return Message.objects.none()
        # ارجع الرسائل في المحادثة، الأحدث أولاً
        return Message.objects.filter(chat=chat).order_by('created_at')  # ترتيب قديم إلى جديد


class MessageCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, chat_id):
        # تحقق أن المستخدم مشارك في المحادثة
        chat = Chat.objects.filter(id=chat_id, participants=request.user).first()
        if not chat:
            return Response({'detail': 'غير مصرح أو المحادثة غير موجودة'}, status=status.HTTP_403_FORBIDDEN)

        content = request.data.get('content', '').strip()
        if not content:
            return Response({'detail': 'المحتوى مطلوب'}, status=status.HTTP_400_BAD_REQUEST)

        # إنشاء رسالة جديدة
        message = Message.objects.create(chat=chat, sender=request.user, content=content)
        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    