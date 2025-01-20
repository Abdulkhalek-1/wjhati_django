from django.shortcuts import render
from .serializers import *
from rest_framework import generics, viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response
from .permissions import IsWalletOwner, ClientAccessPolicy, IsClientOwner
from django.core.exceptions import PermissionDenied

class CreateUserView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [AllowAny]

class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    permission_classes = [ClientAccessPolicy]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Client.objects.all()
        return Client.objects.filter(user=self.request.user)

class WalletViewSet(viewsets.ModelViewSet):
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated, IsWalletOwner]

    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user)

class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsAuthenticated]

class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Driver.objects.all()
        return Driver.objects.filter(user=self.request.user)

class BonusViewSet(viewsets.ModelViewSet):
    serializer_class = BonusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Bonus.objects.filter(user=self.request.user)

class TripViewSet(viewsets.ModelViewSet):
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Trip.objects.all()
        return Trip.objects.filter(driver__user=self.request.user)

class TripStopViewSet(viewsets.ModelViewSet):
    serializer_class = TripStopSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TripStop.objects.filter(trip__driver__user=self.request.user)

class RatingViewSet(viewsets.ModelViewSet):
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Rating.objects.filter(rated_by=self.request.user)

class SupportTicketViewSet(viewsets.ModelViewSet):
    serializer_class = SupportTicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return SupportTicket.objects.all()
        return SupportTicket.objects.filter(user=self.request.user)

class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsAdminUser]

class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Subscription.objects.filter(driver__user=self.request.user)

class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(customer__user=self.request.user)

class CasheBookingViewSet(viewsets.ModelViewSet):
    serializer_class = CasheBookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CasheBooking.objects.filter(user=self.request.user)

class ItemDeliveryViewSet(viewsets.ModelViewSet):
    serializer_class = ItemDeliverySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ItemDelivery.objects.filter(sender=self.request.user)

class CasheItemDeliveryViewSet(viewsets.ModelViewSet):
    serializer_class = CasheItemDeliverySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CasheItemDelivery.objects.filter(user=self.request.user)

class ChatViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Chat.objects.filter(participants=self.request.user)

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Message.objects.filter(sender=self.request.user)

class TransactionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TransactionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            wallet = serializer.validated_data['wallet']
            
            # التحقق من ملكية المحفظة
            if wallet.user != request.user:
                return Response({"error": "ليس لديك صلاحية لهذه المحفظة"}, status=status.HTTP_403_FORBIDDEN)
            
            # تنفيذ العملية
            amount = serializer.validated_data['amount']
            transaction_type = serializer.validated_data['transaction_type']
            
            if transaction_type == 'charge':
                wallet.balance += amount
            elif transaction_type in ['withdraw', 'payment']:
                if wallet.balance < amount:
                    return Response({"error": "الرصيد غير كافي"}, status=status.HTTP_400_BAD_REQUEST)
                wallet.balance -= amount
            
            wallet.save()
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TransferView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TransferSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            from_wallet = serializer.validated_data['from_wallet']
            to_wallet = serializer.validated_data['to_wallet']
            amount = serializer.validated_data['amount']

            # التحقق من ملكية المحفظة المرسلة
            if from_wallet.user != request.user:
                return Response({"error": "ليس لديك صلاحية لهذه المحفظة"}, status=status.HTTP_403_FORBIDDEN)

            # تنفيذ التحويل
            if from_wallet.balance < amount:
                return Response({"error": "الرصيد غير كافي"}, status=status.HTTP_400_BAD_REQUEST)

            from_wallet.balance -= amount
            to_wallet.balance += amount

            from_wallet.save()
            to_wallet.save()
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
from django.core.exceptions import PermissionDenied
from rest_framework import viewsets

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(wallet__user=self.request.user)

    def perform_create(self, serializer):
        # التحقق من ملكية المحفظة قبل الإنشاء
        wallet = serializer.validated_data.get('wallet')
        
        if not wallet or wallet.user != self.request.user:
            raise PermissionDenied("صلاحيات غير كافية لهذه العملية")
            
        # التحقق من الرصيد قبل السحب/الدفع
        if serializer.validated_data['transaction_type'] in ['withdraw', 'payment']:
            if wallet.balance < serializer.validated_data['amount']:
                raise PermissionDenied("الرصيد غير كافي لإتمام العملية")
        
        super().perform_create(serializer)
        wallet.save()  # حفظ التحديثات على المحفظة