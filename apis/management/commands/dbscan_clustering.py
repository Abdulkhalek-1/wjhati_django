import logging
import numpy as np
from math import radians, cos, sin, asin, sqrt
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import now
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN

from apis.models import CasheBooking, Trip, Driver, Booking

logger = logging.getLogger(__name__)

def haversine_distance(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return 6371 * c

class Command(BaseCommand):
    help = 'إنشاء رحلات جماعية ذكية من الحجوزات المعلقة باستخدام DBSCAN واختيار السائق المناسب'

    def add_arguments(self, parser):
        parser.add_argument('--eps', type=float, default=0.5)
        parser.add_argument('--min_samples', type=int, default=3)

    def handle(self, *args, **options):
        eps = options['eps']
        min_samples = options['min_samples']

        bookings = CasheBooking.objects.filter(status=CasheBooking.Status.PENDING)
        if not bookings.exists():
            self.stdout.write(self.style.WARNING("لا توجد حجوزات معلقة."))
            return

        coords, valid_bookings = [], []
        for b in bookings:
            try:
                lat, lon = map(float, b.from_location.split(','))
                coords.append([lat, lon])
                valid_bookings.append(b)
            except Exception as e:
                logger.warning(f"إحداثيات غير صالحة للحجز {b.id}: {e}")

        if not coords:
            self.stdout.write(self.style.WARNING("لا توجد إحداثيات صالحة."))
            return

        try:
            X = StandardScaler().fit_transform(np.array(coords))
            labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(X)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"فشل في تجميع DBSCAN: {e}"))
            return

        clusters = set(labels)
        clusters.discard(-1)
        if not clusters:
            self.stdout.write(self.style.WARNING("لم يتم العثور على عناقيد."))
            return

        drivers = Driver.objects.filter(is_available=True, vehicles__isnull=False).prefetch_related('vehicles').select_related('user').distinct()
        if not drivers.exists():
            self.stdout.write(self.style.ERROR("لا يوجد سائقون متاحون."))
            return

        for cid in clusters:
            indices = [i for i, lbl in enumerate(labels) if lbl == cid]
            cluster_bookings = [valid_bookings[i] for i in indices]
            if not cluster_bookings:
                continue

            sample = cluster_bookings[0]

            def driver_score(driver):
                try:
                    d_lat, d_lon = map(float, driver.where_location.split(','))
                    b_lat, b_lon = map(float, sample.from_location.split(','))
                    distance = haversine_distance(d_lat, d_lon, b_lat, b_lon)
                except:
                    distance = float('inf')
                return (distance, -driver.rating, driver.total_trips)

            sorted_drivers = sorted(drivers, key=driver_score)
            selected_driver = sorted_drivers[0]
            vehicle = selected_driver.vehicles.first()

            if not vehicle:
                logger.warning(f"السائق {selected_driver.id} لا يملك مركبة.")
                continue

            try:
                with transaction.atomic():
                    trip = Trip.objects.create(
                        from_location=sample.from_location,
                        to_location=sample.to_location,
                        departure_time=sample.departure_time or now(),
                        available_seats=vehicle.capacity,
                        price_per_seat=25.0,
                        driver=selected_driver,
                        route_coordinates=str([b.from_location for b in cluster_bookings])
                    )

                    selected_driver.is_available = False
                    selected_driver.save(update_fields=['is_available'])

                    current_seats = 0
                    for b in cluster_bookings:
                        if current_seats + b.passengers > vehicle.capacity:
                            logger.info(f"تجاوز السعة للرحلة {trip.id}، تجاهل الحجز {b.id}")
                            continue

                        Booking.objects.create(
                            trip=trip,
                            customer=b.user,
                            seats=[str(i + 1) for i in range(current_seats, current_seats + b.passengers)],
                            total_price=b.passengers * trip.price_per_seat,
                            status=Booking.Status.CONFIRMED
                        )
                        current_seats += b.passengers

                        b.status = CasheBooking.Status.ACCEPTED
                        b.save(update_fields=['status'])

                    trip.available_seats = vehicle.capacity - current_seats
                    trip.status = 'in_progress' if trip.available_seats == 0 else 'available'
                    trip.save(update_fields=['available_seats', 'status'])

                    self.stdout.write(self.style.SUCCESS(f"تم إنشاء الرحلة {trip.id} وتعيين السائق {selected_driver.user.username}"))
            except Exception as e:
                logger.exception(f"فشل في إنشاء الرحلة للمجموعة {cid}: {e}")
                self.stdout.write(self.style.ERROR(f"فشل في إنشاء الرحلة للمجموعة {cid}"))
