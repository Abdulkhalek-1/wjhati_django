from datetime import timedelta
from django.utils import timezone
from geopy.distance import geodesic
from .models import Subscription, Trip, Booking, CasheBooking, Driver
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count, Avg
from django.template.loader import render_to_string
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Booking, Transfer, Notification
from django.utils import timezone
from django.utils.timezone import now

MATCH_RADIUS_KM = 5
TIME_WINDOW_HOURS = 2

def match_cashe_bookings():
    """
    Match pending CasheBooking and CasheItemDelivery to existing Trips.
    """
    now = timezone.now()
    bookings = CasheBooking.objects.filter(status=CasheBooking.Status.PENDING)
    for cb in bookings:
        window_start = cb.departure_time - timedelta(hours=TIME_WINDOW_HOURS)
        window_end = cb.departure_time + timedelta(hours=TIME_WINDOW_HOURS)
        trips = Trip.objects.filter(
            departure_time__range=(window_start, window_end),
            status=Trip.Status.PENDING
        )
        for trip in trips:
            if geodesic((cb.from_lat, cb.from_lng), (trip.from_lat, trip.from_lng)).km <= MATCH_RADIUS_KM:
                # create booking and update status
                Booking.objects.create(
                    trip=trip,
                    customer=cb.user.user,
                    seats=[str(cb.id)],
                    total_price=cb.passengers * trip.price_per_seat,
                    status=Booking.Status.CONFIRMED
                )
                cb.status = CasheBooking.Status.ACCEPTED
                cb.save()
                break

# =======================
# myapp/views/trip_tracking.py
# =======================


class TripLocationUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        """
        Update current location of a Trip for real-time tracking.
        """
        trip = Trip.objects.get(id=pk, driver__user=request.user)
        trip.current_lat = request.data.get('lat')
        trip.current_lng = request.data.get('lng')
        trip.save()
        return Response({'status': 'location updated'})

# =======================
# myapp/admin/dashboard.py
# =======================

def get_driver_statistics():
    """
    Compute driver stats: total trips and average rating.
    """
    return Driver.objects.annotate(
        total_trips=Count('trips'),
        average_rating=Avg('ratings__rating')
    )


# =======================
# myapp/signals.py
# =======================


@receiver(post_save, sender=Booking)
def notify_booking_confirmed(sender, instance, created, **kwargs):
    if created and instance.status == Booking.Status.CONFIRMED:
        Notification.objects.create(
            user=instance.customer.user,
            title="تم تأكيد الحجز",
            body="تمت معالجة حجزك بنجاح."
        )

@receiver(post_save, sender=Transfer)
def notify_transfer_completed(sender, instance, created, **kwargs):
    if created and instance.status == Transfer.Status.COMPLETED:
        Notification.objects.create(
            user=instance.to_wallet.user,
            title="استلمت تحويلًا ماليًا",
            body=f"تلقيت {instance.amount} من حساب {instance.from_wallet.user.username}."
        )
def check_expiring_subscriptions():
    """
    Daily task: Remind drivers of expiring subscriptions and auto-renew when possible.
    """
    soon = now().date() + timezone.timedelta(days=3)
    expiring = Subscription.objects.filter(end_date__lte=soon, is_active=True)
    for sub in expiring:
        wallet = sub.driver.user.wallet
        if sub.auto_renew and wallet.balance >= sub.plan.price:
            # Auto-renew subscription
            wallet.debit(sub.plan.price)
            sub.renew()
            Notification.objects.create(
                user=sub.driver.user,
                title="تم تجديد اشتراكك",
                body=f"تم تجديد اشتراكك في خطة {sub.plan.name} بنجاح."
            )
        else:
            # Notify about upcoming expiration
            Notification.objects.create(
                user=sub.driver.user,
                title="انتهاء قريب للاشتراك",
                body=f"ينتهي اشتراكك في خطة {sub.plan.name} خلال 3 أيام."
            )
