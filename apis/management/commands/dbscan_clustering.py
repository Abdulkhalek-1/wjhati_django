import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import logging
import time
import numpy as np
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.db import transaction
from django.contrib.auth import get_user_model
from sklearn.preprocessing import StandardScaler
import hdbscan

from apis.models import (
    CasheBooking, Booking,
    CasheItemDelivery, ItemDelivery,
    Driver, Trip, Notification
)
from apis.driver_selector import haversine_distance, select_best_driver
from apis.route_optimizer import nearest_neighbor_route
from apis.retry_queue import add_to_retry_queue

logger = logging.getLogger(__name__)
User = get_user_model()

def send_notification(user, title, message, notification_type='system', related_object_id=None):
    """
    يؤجّل إنشاء الإشعار حتى تنتهي المعاملة بنجاح.
    """
    def _create():
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            related_object_id=related_object_id
        )
        logger.info(f"🔔 [DB] إشعار تم إنشاؤه لـ {user}: {title} – {message}")

    # يتم الاستدعاء بعد نجاح المعاملة
    transaction.on_commit(_create)


class Command(BaseCommand):
    help = '🚀 جدولة الرحلات الذكية بشكل دوري مع دعم الدمج بين الشحنات والركاب.'

    def add_arguments(self, parser):
        parser.add_argument('--min_cluster_size', type=int, default=3)
        parser.add_argument('--interval', type=int, default=20,
                            help='زمن الانتظار بالثواني بين كل جولة جدولية')

    def handle(self, *args, **options):
        interval = options['interval']
        self.stdout.write(self.style.NOTICE("🔄 بدء البث الدوري لجدولة الرحلات..."))
        while True:
            start_ts = now()
            self.stdout.write(self.style.NOTICE(f"🔁 بدء الجولة في {start_ts}"))
            try:
                self.run_scheduler(options)
                self.stdout.write(self.style.SUCCESS("✅ انتهت الجولة بنجاح."))
            except Exception:
                logger.exception("⚠️ فشل الجولة الجدولية.")
            self.stdout.write(self.style.NOTICE(f"⏱️ النوم لـ {interval} ثانية..."))
            time.sleep(interval)

    def find_pending_trip(self, from_loc, to_loc, min_capacity=1, max_distance_km=3):
        try:
            from_lat, from_lon = map(float, from_loc.split(','))
            to_lat, to_lon = map(float, to_loc.split(','))
        except ValueError:
            logger.warning(f"⚠️ إحداثيات غير صالحة: {from_loc} - {to_loc}")
            return None

        trips = Trip.objects.filter(
            status__in=[Trip.Status.PENDING, Trip.Status.IN_PROGRESS],
            available_seats__gte=min_capacity
        )

        for trip in trips:
            try:
                t_from_lat, t_from_lon = map(float, trip.from_location.split(','))
                t_to_lat, t_to_lon     = map(float, trip.to_location.split(','))
                if (haversine_distance(from_lat, from_lon, t_from_lat, t_from_lon) <= max_distance_km and
                    haversine_distance(to_lat,   to_lon,   t_to_lat,   t_to_lon)   <= max_distance_km):
                    return trip
            except Exception as e:
                logger.warning(f"⚠️ فشل في حساب مسافة الرحلة {trip.id}: {e}")
        return None

    def run_scheduler(self, options):
        # 1. جمع الطلبات المعلقة
        bookings  = list(CasheBooking.objects.filter(status=CasheBooking.Status.PENDING))
        deliveries = list(CasheItemDelivery.objects.filter(status=CasheItemDelivery.Status.PENDING))
        requests = bookings + deliveries

        # 2. استخراج الإحداثيات
        coords, items = [], []
        for req in requests:
            try:
                f_lat, f_lon = map(float, req.from_location.split(','))
                t_lat, t_lon = map(float, req.to_location.split(','))
                coords.append([f_lat, f_lon, t_lat, t_lon])
                items.append(req)
            except Exception as e:
                logger.warning(f"⚠️ طلب {req.id} إحداثيات غير صالحة: {e}")
                add_to_retry_queue(req)

        if not coords:
            self.stdout.write(self.style.WARNING("🚫 لا توجد طلبات صالحه للمعالجة."))
            return

        # 3. ضبط العتبة وتجنب return مبكر حتى يصدر إشعار
        scaled = StandardScaler().fit_transform(np.array(coords))
        required = max(2, options['min_cluster_size'])  # خفّضنا العتبة للتأكد من المعالجة حتى عند نقطتين
        if len(scaled) < required:
            self.stdout.write(self.style.WARNING(
                f"🚫 عدد النقاط ({len(scaled)}) أقل من الحد ({required}) — سيتم المعالجة فردياً مع إشعارات"
            ))
            for item in items:
                self.process_cluster([item], force_notify=True)
            return

        labels = hdbscan.HDBSCAN(min_cluster_size=options['min_cluster_size']).fit_predict(scaled)
        for cid in set(labels):
            cluster_items = [items[i] for i, lbl in enumerate(labels) if lbl == cid]
            self.process_cluster(cluster_items, force_notify=False)

    def process_cluster(self, cluster_items, force_notify=False):
        """
        إذا force_notify=True، نرسل إشعار "في الانتظار" لكل طلب.
        """
        # لإشعار المستخدمين بأن طلبهم في الانتظار
        if force_notify:
            for r in cluster_items:
                user = getattr(r, 'user', getattr(r.user, 'user', None))
                if isinstance(user, User):
                    send_notification(
                        user,
                        "طلبك قيد الانتظار",
                        "عدد الطلبات قليل حالياً، سنعالج طلبك فور توفر المزيد.",
                        notification_type='retry',
                        related_object_id=r.id
                    )

        bookings   = [r for r in cluster_items if hasattr(r, 'passengers')]
        deliveries = [r for r in cluster_items if hasattr(r, 'weight')]
        group      = cluster_items

        from_loc = group[0].from_location
        to_loc   = group[0].to_location
        total_p  = sum(b.passengers for b in bookings)

        # بحث عن رحلة قائمة
        trip = self.find_pending_trip(from_loc, to_loc, min_capacity=max(1, total_p))

        # تجهيز المسارات
        pickups = [list(map(float, r.from_location.split(','))) for r in group]
        drops   = [list(map(float, r.to_location.split(',')))   for r in group]
        route   = {
            'pickup':  nearest_neighbor_route(pickups),
            'dropoff': nearest_neighbor_route(drops)
        }

        with transaction.atomic():
            # إذا لا توجد رحلة، ننشئ رحلة جديدة
            if not trip:
                driver = select_best_driver(group, Driver.objects.filter(is_available=True))
                if not driver or not driver.vehicles.first():
                    for r in group:
                        add_to_retry_queue(r)
                    return
                vehicle = driver.vehicles.first()
                trip = Trip.objects.create(
                    from_location=from_loc,
                    to_location=to_loc,
                    departure_time=now(),
                    available_seats=vehicle.capacity,
                    price_per_seat=25.0,
                    driver=driver,
                    vehicle=vehicle,
                    route_coordinates=str(route),
                    status=Trip.Status.PENDING
                )
                driver.is_available = False
                driver.save(update_fields=['is_available'])
                send_notification(
                    driver.user,
                    "رحلة جديدة",
                    f"تم تعيين رحلة جديدة لك من {from_loc} إلى {to_loc}.",
                    notification_type='trip',
                    related_object_id=trip.id
                )

            # إضافة الحجوزات
            seats_used = trip.vehicle.capacity - trip.available_seats
            added = False

            for b in bookings:
                try:
                    if seats_used + b.passengers <= trip.vehicle.capacity:
                        bk = Booking.objects.create(
                            trip=trip,
                            customer=b.user,
                            seats=[str(i+1) for i in range(seats_used, seats_used + b.passengers)],
                            total_price=b.passengers * trip.price_per_seat,
                            status=Booking.Status.CONFIRMED
                        )
                        b.status = CasheBooking.Status.ACCEPTED
                        b.save(update_fields=['status'])
                        seats_used += b.passengers
                        added = True
                        send_notification(
                            b.user,
                            "رحلتك جاهزة",
                            f"تم تأكيد حجزك من {from_loc} إلى {to_loc}.",
                            notification_type='booking',
                            related_object_id=bk.id
                        )
                except Exception:
                    add_to_retry_queue(b)

            # إضافة الشحنات
            for d in deliveries:
                try:
                    itm = ItemDelivery.objects.create(
                        trip=trip,
                        sender=d.user.user,
                        receiver_name=d.receiver_name,
                        receiver_phone=d.receiver_phone,
                        item_description=d.item_description,
                        weight=d.weight,
                        insurance_amount=d.insurance_amount or 0,
                        delivery_code=f"D{d.id:06d}",
                        status=ItemDelivery.Status.IN_TRANSIT
                    )
                    d.status = CasheItemDelivery.Status.ACCEPTED
                    d.save(update_fields=['status'])
                    added = True
                    send_notification(
                        d.user.user,
                        "شحنك جاهز",
                        f"تم تأكيد شحنتك من {from_loc} إلى {to_loc}.",
                        notification_type='delivery',
                        related_object_id=itm.id
                    )
                except Exception:
                    add_to_retry_queue(d)

            # تحديث حالة الرحلة
            if added:
                trip.available_seats = trip.vehicle.capacity - seats_used
                trip.status = (
                    Trip.Status.FULL
                    if trip.available_seats <= 0 else Trip.Status.IN_PROGRESS
                )
                trip.save(update_fields=['available_seats', 'status'])
