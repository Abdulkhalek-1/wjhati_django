import logging
import numpy as np
import time
from datetime import timedelta
from math import radians, cos, sin, asin, sqrt
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.db import transaction
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler
from scipy.spatial.distance import euclidean
from itertools import permutations

from apis.models import CasheBooking, Trip, Driver, Booking

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
        total_dist = sum(euclidean(route[i], route[i+1]) for i in range(len(route) - 1))
        if total_dist < min_total:
            min_total = total_dist
            best_order = route
    return best_order

class Command(BaseCommand):
    help = 'Hybrid clustering to create optimized trips from bookings.'

    def add_arguments(self, parser):
        parser.add_argument('--eps', type=float, default=0.1)
        parser.add_argument('--min_samples', type=int, default=3)

    def handle(self, *args, **options):
        while True:
            self.stdout.write(self.style.NOTICE("🔄 بدء تنفيذ جدولة الرحلات..."))
            logger.info("Starting hybrid scheduler...")
            self.run_scheduler(options)
            self.stdout.write(self.style.SUCCESS("✅ تم تنفيذ الجولة بنجاح. في انتظار الدورة القادمة..."))
            logger.info("Waiting 5 minutes before next run.")
            time.sleep(300)  # كل 5 دقائق

    def run_scheduler(self, options):
        eps = options['eps']
        min_samples = options['min_samples']

        bookings = CasheBooking.objects.filter(status=CasheBooking.Status.PENDING)
        if not bookings.exists():
            self.stdout.write(self.style.WARNING("⚠️ لا توجد حجوزات معلقة."))
            return

        coords, valid_bookings = [], []
        for b in bookings:
            try:
                lat1, lon1 = map(float, b.from_location.split(','))
                coords.append([lat1, lon1])
                valid_bookings.append(b)
            except:
                logger.warning(f"Invalid coordinates in booking {b.id}")
        
        if not coords:
            self.stdout.write(self.style.ERROR("❌ لا توجد إحداثيات صالحة."))
            return

        X = StandardScaler().fit_transform(np.array(coords))
        spatial_labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(X)

        all_drivers = Driver.objects.filter(is_available=True).prefetch_related('vehicles').select_related('user')
        if not all_drivers.exists():
            self.stdout.write(self.style.ERROR("❌ لا يوجد سائقون متاحون."))
            return

        for cid in set(spatial_labels):
            if cid == -1:
                continue
            cluster_indices = [i for i, label in enumerate(spatial_labels) if label == cid]
            cluster_bookings = [valid_bookings[i] for i in cluster_indices]

            dep_times = np.array([(b.departure_time - now()).total_seconds() / 60 for b in cluster_bookings]).reshape(-1, 1)
            time_labels = KMeans(n_clusters=max(1, len(cluster_bookings)//3)).fit_predict(dep_times) if len(cluster_bookings) > 1 else [0] * len(cluster_bookings)

            for time_cid in set(time_labels):
                group = [cluster_bookings[i] for i in range(len(cluster_bookings)) if time_labels[i] == time_cid]
                if not group:
                    continue

                sample = group[0]
                best_driver = self.select_driver(sample, all_drivers)
                if not best_driver or not best_driver.vehicles.first():
                    continue

                try:
                    with transaction.atomic():
                        vehicle = best_driver.vehicles.first()
                        route_points = [tuple(map(float, b.from_location.split(','))) for b in group]
                        optimized_route = optimize_route(route_points)

                        trip = Trip.objects.create(
                            from_location=sample.from_location,
                            to_location=sample.to_location,
                            departure_time=sample.departure_time,
                            available_seats=vehicle.capacity,
                            price_per_seat=25.0,
                            driver=best_driver,
                            route_coordinates=str(optimized_route)
                        )

                        best_driver.is_available = False
                        best_driver.save(update_fields=['is_available'])

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

                        trip.available_seats = vehicle.capacity - current_seats
                        if trip.available_seats == 0:
                            trip.status = 'full'
                        trip.save(update_fields=['available_seats', 'status'])

                        self.stdout.write(self.style.SUCCESS(f"🚐 رحلة {trip.id} تم إنشاؤها بنجاح مع السائق {best_driver.user.username}"))
                except Exception as e:
                    logger.exception(f"فشل في إنشاء الرحلة: {e}")

    def select_driver(self, booking, drivers):
        try:
            b_lat, b_lon = map(float, booking.from_location.split(','))
            scored = []
            for d in drivers:
                try:
                    d_lat, d_lon = map(float, d.where_location.split(','))
                    distance = haversine_distance(b_lat, b_lon, d_lat, d_lon)
                except:
                    distance = float('inf')
                score = (distance, -d.rating, d.total_trips)
                scored.append((score, d))
            return sorted(scored, key=lambda x: x[0])[0][1]
        except Exception as e:
            logger.error(f"اختيار السائق فشل: {e}")
            return None
