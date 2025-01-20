from django.shortcuts import render
from .serializers import *
from rest_framework import generics
from rest_framework import viewsets
from .models import *
from rest_framework.permissions import  AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .permissions import IsWalletOwner 

class CreateUserView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

class WalletViewSet(viewsets.ModelViewSet):
    serializer_class = WalletSerializer
    permission_classes = [IsWalletOwner]  # تطبيق الصلاحية المخصصة

    def get_queryset(self):
        user = self.request.user
        return Wallet.objects.filter(user=user)


class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer

class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer

class BonusViewSet(viewsets.ModelViewSet):
    queryset = Bonus.objects.all()
    serializer_class = BonusSerializer

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer

class TripStopViewSet(viewsets.ModelViewSet):
    queryset = TripStop.objects.all()
    serializer_class = TripStopSerializer

class RatingViewSet(viewsets.ModelViewSet):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer

class SupportViewSet(viewsets.ModelViewSet):
    queryset = Support.objects.all()
    serializer_class = SupportSerializer

class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer

class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

class CasheBookingViewSet(viewsets.ModelViewSet):
    queryset = CasheBooking.objects.all()
    serializer_class = CasheBookingSerializer

class ItemDeliveryViewSet(viewsets.ModelViewSet):
    queryset = ItemDelivery.objects.all()
    serializer_class = ItemDeliverySerializer

class CasheItemDeliveryViewSet(viewsets.ModelViewSet):
    queryset = CasheItemDelivery.objects.all()
    serializer_class = CasheItemDeliverySerializer


class ChatViewSet(viewsets.ModelViewSet):
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer


class TransactionView(APIView):
    def post(self, request):
        serializer = TransactionSerializer(data=request.data)
        if serializer.is_valid():
            wallet = serializer.validated_data['wallet']
            amount = serializer.validated_data['amount']
            transaction_type = serializer.validated_data['transaction_type']

            # تحديث رصيد المحفظة بناءً على نوع الحركة
            if transaction_type == 'charge':
                wallet.balance += amount
            elif transaction_type == 'withdraw':
                if wallet.balance >= amount:
                    wallet.balance -= amount
                else:
                    return Response({"error": "رصيد غير كافي"}, status=status.HTTP_400_BAD_REQUEST)
            elif transaction_type == 'payment':
                if wallet.balance >= amount:
                    wallet.balance -= amount
                else:
                    return Response({"error": "رصيد غير كافي"}, status=status.HTTP_400_BAD_REQUEST)

            wallet.save()
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class TransferView(APIView):
    def post(self, request):
        serializer = TransferSerializer(data=request.data)
        if serializer.is_valid():
            from_wallet = serializer.validated_data['from_wallet']
            to_wallet = serializer.validated_data['to_wallet']
            amount = serializer.validated_data['amount']

            # التحقق من وجود رصيد كافي في محفظة المرسل
            if from_wallet.balance >= amount:
                from_wallet.balance -= amount
                to_wallet.balance += amount

                from_wallet.save()
                to_wallet.save()
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response({"error": "رصيد غير كافي"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)