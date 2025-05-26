# File: apis/management/commands/dbscan_scheduler.py
import logging
import time
import numpy as np
from math import radians, sin, cos, sqrt, asin
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.db import transaction
from sklearn.preprocessing import StandardScaler
import hdbscan

from apis.models import (
    CasheBooking, Booking,
    CasheItemDelivery, ItemDelivery,
    Driver, Trip
)
from apis.driver_selector import select_best_driver
from apis.route_optimizer import nearest_neighbor_route
from apis.retry_queue import add_to_retry_queue

logger = logging.getLogger(__name__)

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

    def find_pending_trip(self, from_loc, to_loc):
        return Trip.objects.filter(
            from_location=from_loc,
            to_location=to_loc,
            status__in=[Trip.Status.PENDING, Trip.Status.IN_PROGRESS],
            available_seats__gt=0
        ).order_by('departure_time').first()

    def run_scheduler(self, options):
        # 1. جمع الطلبات المعلقة
        bookings = list(CasheBooking.objects.filter(status=CasheBooking.Status.PENDING))
        deliveries = list(CasheItemDelivery.objects.filter(status=CasheItemDelivery.Status.PENDING))
        requests = bookings + deliveries

        # 2. استخراج الإحداثيات
        coords, items = [], []
        for req in requests:
            try:
                lat, lon = map(float, req.from_location.split(','))
                coords.append([lat, lon])
                items.append(req)
            except Exception as e:
                logger.warning(f"⚠️ طلب {req.id} إحداثيات غير صالحة: {e}")
                add_to_retry_queue(req, str(e))

        if not coords:
            self.stdout.write(self.style.WARNING("🚫 لا توجد طلبات صالحه للمعالجة."))
            return

        # 3. تجميع باستخدام HDBSCAN
        scaled = StandardScaler().fit_transform(np.array(coords))
        labels = hdbscan.HDBSCAN(min_cluster_size=options['min_cluster_size']).fit_predict(scaled)

        # 4. قائمة السائقين المتاحين
        drivers = Driver.objects.filter(is_available=True).prefetch_related('vehicles').select_related('user')
        if not drivers.exists():
            self.stdout.write(self.style.ERROR("🚫 لا يوجد سائقون متاحون."))
            return

        # 5. المعالجة العنقودية
        label_set = set(labels)
        if label_set == {-1}:
            logger.info("⚠️ جميع النقاط ضوضاء. معالجة كل طلبٍ على حدة.")
            for req in items:
                self.process_cluster([req])
        else:
            for cid in label_set - {-1}:
                cluster_items = [items[i] for i, lbl in enumerate(labels) if lbl == cid]
                if not cluster_items:
                    continue
                logger.info(f"ℹ️ معالجة العنقود {cid} بعدد عناصر {len(cluster_items)}")
                self.process_cluster(cluster_items)

    def process_cluster(self, cluster_items):
        # تصنيف الركاب والشحنات
        bookings = [r for r in cluster_items if hasattr(r, 'passengers')]
        deliveries = [r for r in cluster_items if hasattr(r, 'weight')]
        group = cluster_items

        # اختيار السائق
        driver = select_best_driver(group, Driver.objects.filter(is_available=True))
        if not driver or not driver.vehicles.first():
            logger.warning("🚫 لم يتم العثور على سائق مناسب للمجموعة.")
            for r in group:
                add_to_retry_queue(r, 'no_driver')
            return

        vehicle = driver.vehicles.first()
        from_loc = group[0].from_location
        to_loc = group[0].to_location

        # البحث عن رحلة معلقة
        trip = self.find_pending_trip(from_loc, to_loc)

        # تحسين المسارات
        pickups = [list(map(float, r.from_location.split(','))) for r in group]
        drops = [list(map(float, r.to_location.split(','))) for r in group]
        pickup_coords = nearest_neighbor_route(pickups)
        dropoff_coords = nearest_neighbor_route(drops)

        with transaction.atomic():
            if not trip:
                trip = Trip.objects.create(
                    from_location=from_loc,
                    to_location=to_loc,
                    departure_time=now(),
                    available_seats=vehicle.capacity,
                    price_per_seat=25.0,
                    driver=driver,
                    vehicle=vehicle,
                    route_coordinates=str({'pickup': pickup_coords, 'dropoff': dropoff_coords}),
                    status=Trip.Status.PENDING
                )
                driver.is_available = False
                driver.save(update_fields=['is_available'])

            seats_used = vehicle.capacity - trip.available_seats

            # إضافة الحجوزات
            for b in bookings:
                try:
                    if seats_used + b.passengers <= vehicle.capacity:
                        Booking.objects.create(
                            trip=trip,
                            customer=b.user,
                            seats=[str(i+1) for i in range(seats_used, seats_used + b.passengers)],
                            total_price=b.passengers * trip.price_per_seat,
                            status=Booking.Status.CONFIRMED
                        )
                        b.status = CasheBooking.Status.ACCEPTED
                        b.save(update_fields=['status'])
                        seats_used += b.passengers
                except Exception as e:
                    logger.exception(f"❌ فشل إضافة حجز {b.id}: {e}")
                    add_to_retry_queue(b, str(e))

            # إضافة الشحنات
            for d in deliveries:
                try:
                    ItemDelivery.objects.create(
                        trip=trip,
                        sender=d.user.user,
                        receiver_name='Unknown',
                        receiver_phone='000000000',
                        item_description=d.item_description,
                        weight=d.weight,
                        insurance_amount=0,
                        delivery_code=f"D{d.id:06d}",
                        status=ItemDelivery.Status.IN_TRANSIT
                    )
                    d.status = CasheItemDelivery.Status.ACCEPTED
                    d.save(update_fields=['status'])
                except Exception as e:
                    logger.exception(f"❌ فشل إضافة شحنة {d.id}: {e}")
                    add_to_retry_queue(d, str(e))

            # تحديث حالة الرحلة
            trip.available_seats = vehicle.capacity - seats_used
            trip.status = Trip.Status.FULL if trip.available_seats <= 0 else Trip.Status.IN_PROGRESS
            trip.save(update_fields=['available_seats','status'])

            logger.info(f"🚌 {'تم إنشاء' if seats_used == 0 else 'تم تحديث'} الرحلة {trip.id} للسائق {driver.user.username}")
