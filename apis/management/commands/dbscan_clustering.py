import logging
import numpy as np
import time
from datetime import timedelta
from math import radians, cos, sin, asin, sqrt
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.db import transaction
from sklearn.preprocessing import StandardScaler
from itertools import permutations
import hdbscan
from apis.models import CasheBooking, Trip, Driver, Booking
import warnings
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)


logger = logging.getLogger(__name__)

def haversine_distance(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * asin(sqrt(a))
    return 6371 * c

def optimize_route(locations):
    if len(locations) <= 2:
        return locations
    best_order = None
    min_total = float('inf')
    for perm in permutations(locations[1:]):
        route = [locations[0]] + list(perm)
        total_dist = sum(haversine_distance(*route[i], *route[i+1]) for i in range(len(route) - 1))
        if total_dist < min_total:
            min_total = total_dist
            best_order = route
    return best_order

class Command(BaseCommand):
    help = '🚀 جدولة الرحلات الذكية باستخدام HDBSCAN لتحسين تحليل الوجهات.'

    def add_arguments(self, parser):
        parser.add_argument('--min_cluster_size', type=int, default=3)

    def handle(self, *args, **options):
        while True:
            self.stdout.write(self.style.NOTICE("\n🔄 بدء تنفيذ جدولة الرحلات الذكية..."))
            logger.info("Running intelligent trip scheduler with DBSCAN...")
            self.run_scheduler(options)
            self.stdout.write(self.style.SUCCESS("✅ تم تنفيذ الجولة. بانتظار الجولة التالية بعد 5 دقائق..."))
            time.sleep(300)

    def run_scheduler(self, options):
        min_cluster_size = options['min_cluster_size']

        bookings = CasheBooking.objects.filter(status=CasheBooking.Status.PENDING)
        coords, valid_bookings = [], []

        for b in bookings:
            try:
                from_lat, from_lon = map(float, b.from_location.split(','))
                to_lat, to_lon = map(float, b.to_location.split(','))
                mid_lat = (from_lat + to_lat) / 2
                mid_lon = (from_lon + to_lon) / 2
                coords.append([mid_lat, mid_lon])
                valid_bookings.append(b)
            except Exception as e:
                logger.warning(f"📛 Booking {b.id} has invalid coordinates: {e}")

        if not coords:
            self.stdout.write(self.style.WARNING("❌ لا توجد حجوزات بصيغة إحداثيات صالحة."))
            return

        X = StandardScaler().fit_transform(np.array(coords))
        clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size)
        labels = clusterer.fit_predict(X)

        drivers = Driver.objects.filter(is_available=True).prefetch_related('vehicles').select_related('user')
        if not drivers.exists():
            self.stdout.write(self.style.ERROR("🚫 لا يوجد سائقون متاحون."))
            return

        for cid in set(labels):
            if cid == -1:
                continue

            cluster_indices = [i for i, label in enumerate(labels) if label == cid]
            group = [valid_bookings[i] for i in cluster_indices]
            if not group:
                continue

            sample = group[0]
            driver = self.select_driver(sample, drivers)
            if not driver or not driver.vehicles.first():
                continue

            try:
                with transaction.atomic():
                    # الحصول على أول مركبة مرتبطة بالسائق
                    vehicle = driver.vehicles.first()
                    if not vehicle:
                        logger.warning(f"🚫 السائق {driver.user.username} لا يملك مركبة مرتبطة. تخطي السائق.")
                        continue  # تخطي السائق إذا لم يكن لديه مركبة

                    # إنشاء الرحلة
                    trip = Trip.objects.create(
                        from_location=sample.from_location,
                        to_location=sample.to_location,
                        departure_time=sample.departure_time,
                        available_seats=vehicle.capacity,
                        price_per_seat=25.0,
                        driver=driver,
                        vehicle=vehicle,  # تعيين المركبة هنا
                        route_coordinates=str({
                            "pickup": optimize_route([list(map(float, b.from_location.split(','))) for b in group]),
                            "dropoff": optimize_route([list(map(float, b.to_location.split(','))) for b in group]),
                        })
                    )

                    # تحديث حالة السائق
                    driver.is_available = False
                    driver.save(update_fields=['is_available'])

                    # معالجة الحجوزات المرتبطة
                    current_seats = 0
                    for b in group:
                        if current_seats + b.passengers > vehicle.capacity:
                            continue
                        Booking.objects.create(
                            trip=trip,
                            customer=b.user,
                            seats=[str(i + 1) for i in range(current_seats, current_seats + b.passengers)],
                            total_price=b.passengers * trip.price_per_seat,
                            status=Booking.Status.CONFIRMED
                        )
                        b.status = CasheBooking.Status.ACCEPTED
                        b.save(update_fields=['status'])
                        current_seats += b.passengers

                    # تحديث عدد المقاعد المتاحة وحالة الرحلة
                    trip.available_seats = vehicle.capacity - current_seats
                    if trip.available_seats == 0:
                        trip.status = 'full'
                    trip.save(update_fields=['available_seats', 'status'])

                    self.stdout.write(self.style.SUCCESS(f"🚌 تم إنشاء الرحلة {trip.id} للسائق {driver.user.username}"))
            except Exception as e:
                logger.exception(f"❌ فشل إنشاء الرحلة: {e}")

    def select_driver(self, booking, drivers):
        try:
            pickup_lat, pickup_lon = map(float, booking.from_location.split(','))
            drop_lat, drop_lon = map(float, booking.to_location.split(','))
            scored = []
            for d in drivers:
                try:
                    d_lat, d_lon = map(float, d.where_location.split(','))
                    dist1 = haversine_distance(d_lat, d_lon, pickup_lat, pickup_lon)
                    dist2 = haversine_distance(d_lat, d_lon, drop_lat, drop_lon)
                    score = (dist1 + dist2) / 2
                except:
                    score = float('inf')
                scored.append((score, d))
            return sorted(scored, key=lambda x: x[0])[0][1]
        except Exception as e:
            logger.error(f"⚠️ فشل اختيار السائق: {e}")
            return None
