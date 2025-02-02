from datetime import timedelta
import uuid
from venv import logger
from django.db import transaction
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
from django.utils import timezone
from sklearn.cluster import DBSCAN
import numpy as np

from apis import models

class TripOptimizer:
    def __init__(self, time_window=15, max_detour=5):
        self.time_window = time_window  # دقائق
        self.max_detour = max_detour    # كم

    # --------------------------------------------------
    # مرحلة 1: تجميع الحجوزات باستخدام خوارزمية DBSCAN
    # --------------------------------------------------
    def cluster_bookings(self, bookings):
        coords = []
        for b in bookings:
            coords.append([
                b.from_location.x,
                b.from_location.y,
                b.to_location.x,
                b.to_location.y,
                b.departure_time.timestamp()
            ])

        X = np.array(coords)
        epsilon = 1000  # مسافة بالمتر + 15 دقيقة
        db = DBSCAN(eps=epsilon, min_samples=2).fit(X)
        
        clusters = {}
        for label, booking in zip(db.labels_, bookings):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(booking)
        return clusters

    # --------------------------------------------------
    # مرحلة 2: حساب المسار الأمثل باستخدام خوارزمية TSP
    # --------------------------------------------------
    def optimize_route(self, cluster):
        # تنفيذ خوارزمية المسار الأقصر (مثال مبسط)
        locations = sorted(
            cluster,
            key=lambda x: x.from_location.distance(x.to_location)
        )
        return locations

    # --------------------------------------------------
    # مرحلة 3: تخصيص السائق باستخدام التعلم الآلي
    # --------------------------------------------------
    def select_best_driver(self, cluster):
        from .models import Driver
        centroid = self.calculate_cluster_centroid(cluster)
        
        drivers = Driver.objects.filter(
            is_available=True,
            capacity__gte=sum(b.passengers for b in cluster),
            current_location__distance_lte=(
                centroid,
                Distance(km=self.max_detour)
            )
        ).annotate(
            rating_score=models.F('rating'),
            distance=Distance('current_location', centroid)
        ).order_by('-rating_score', 'distance')
        
        return drivers.first()

    def calculate_cluster_centroid(self, cluster):
        x_coords = [b.from_location.x for b in cluster]
        y_coords = [b.from_location.y for b in cluster]
        return Point(np.mean(x_coords), np.mean(y_coords))

    # --------------------------------------------------
    # التنفيذ الرئيسي مع إدارة الأخطاء المتقدمة
    # --------------------------------------------------
    @transaction.atomic
    def process_bookings(self):
        from .models import CasheBooking, Trip, Booking
        
        pending_bookings = CasheBooking.objects.filter(
            status=CasheBooking.Status.PENDING
        ).select_related('user').prefetch_related('from_location', 'to_location')

        clusters = self.cluster_bookings(pending_bookings)

        for cluster_id, cluster in clusters.items():
            if cluster_id == -1 or len(cluster) < 2:
                continue  # تجاهل الحجوزات المنفردة

            try:
                optimized_route = self.optimize_route(cluster)
                driver = self.select_best_driver(optimized_route)
                
                if not driver:
                    self.handle_failed_cluster(cluster)
                    continue

                trip = self.create_trip(driver, optimized_route)
                self.create_bookings(trip, optimized_route)
                self.update_cache_bookings(cluster)

            except Exception as e:
                self.handle_processing_error(e, cluster)
                continue

    def create_trip(self, driver, cluster):
        from .models import Trip
        
        departure_time = self.calculate_optimal_departure(cluster)
        from_location = self.calculate_centroid([b.from_location for b in cluster])
        to_location = self.calculate_centroid([b.to_location for b in cluster])

        return Trip.objects.create(
            driver=driver,
            from_location=from_location,
            to_location=to_location,
            departure_time=departure_time,
            price_per_seat=self.calculate_dynamic_pricing(cluster),
            available_seats=driver.capacity,
            status=Trip.Status.PENDING,
            route_data=self.generate_route_data(cluster)
        )

    def calculate_optimal_departure(self, cluster):
        times = [b.departure_time for b in cluster]
        return max(times) + timedelta(minutes=self.time_window//2)

    def create_bookings(self, trip, cluster):
        bookings = []
        for booking in cluster:
            bookings.append(models.Booking(
                trip=trip,
                customer=booking.user,
                seats=self.assign_seats(booking.passengers),
                total_price=booking.passengers * trip.price_per_seat,
                status=models.Booking.Status.CONFIRMED
            ))
        models.Booking.objects.bulk_create(bookings)

    # --------------------------------------------------
    # وظائف مساعدة متقدمة
    # --------------------------------------------------
    def calculate_dynamic_pricing(self, cluster):
        base_price = 50.00
        demand_factor = len(cluster) / 10
        time_factor = 1.2 if self.is_peak_time() else 0.9
        return round(base_price * demand_factor * time_factor, 2)

    def assign_seats(self, passengers):
        return [f"{uuid.uuid4().hex[:6]}" for _ in range(passengers)]

    def handle_failed_cluster(self, cluster):
        for booking in cluster:
            booking.status = models.CasheBooking.Status.FAILED
            booking.save()

    def handle_processing_error(self, error, cluster):
        logger.error(f"Error processing cluster: {error}")
        self.handle_failed_cluster(cluster)

# --------------------------------------------------
# مثال على الاستخدام:
# --------------------------------------------------
optimizer = TripOptimizer(
    time_window=20,
    max_detour=7
)
optimizer.process_bookings()