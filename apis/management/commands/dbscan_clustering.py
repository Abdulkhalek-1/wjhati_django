import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from django.core.management.base import BaseCommand
from apis.models import CasheBooking, Trip, Driver, Vehicle, Booking
from django.utils.timezone import now


def haversine_distance(lat1, lon1, lat2, lon2):
    from math import radians, cos, sin, asin, sqrt
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return km


class Command(BaseCommand):
    help = 'إنشاء رحلات من حجوزات CasheBooking عبر DBSCAN وتخصيص أفضل سائق'

    def add_arguments(self, parser):
        parser.add_argument('--eps', type=float, default=0.5)
        parser.add_argument('--min_samples', type=int, default=3)

    def handle(self, *args, **options):
        eps = options['eps']
        min_samples = options['min_samples']

        bookings = CasheBooking.objects.filter(status=CasheBooking.Status.PENDING)
        if not bookings.exists():
            self.stdout.write(self.style.WARNING('لا توجد حجوزات معلقة.'))
            return

        coords = []
        valid_bookings = []
        for b in bookings:
            try:
                lat1, lon1 = map(float, b.from_location.split(','))
                lat2, lon2 = map(float, b.to_location.split(','))
                coords.append([lat1, lon1, lat2, lon2])
                valid_bookings.append(b)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'خطأ في الإحداثيات للحجز {b.id}: {e}'))

        if not coords:
            self.stdout.write(self.style.ERROR('لا توجد إحداثيات صالحة.'))
            return

        X = StandardScaler().fit_transform(np.array(coords))
        labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(X)

        clusters = set(labels)
        if -1 in clusters:
            clusters.remove(-1)

        for cid in clusters:
            indices = [i for i, lbl in enumerate(labels) if lbl == cid]
            cluster_bookings = [valid_bookings[i] for i in indices]
            sample = cluster_bookings[0]

            # اختيار أفضل سائق
            all_drivers = Driver.objects.filter(is_available=True, vehicles__isnull=False).distinct()
            if not all_drivers.exists():
                self.stdout.write(self.style.ERROR('لا يوجد سائقون متاحون.'))
                continue

            def score_driver(driver):
                try:
                    lat, lon = map(float, driver.where_location.split(','))
                    booking_lat, booking_lon = map(float, sample.from_location.split(','))
                    distance = haversine_distance(lat, lon, booking_lat, booking_lon)
                except:
                    distance = float('inf')
                return (-driver.rating, distance, driver.total_trips)

            sorted_drivers = sorted(all_drivers, key=score_driver)
            selected_driver = sorted_drivers[0]  # اختيار الأفضل أو الأول كخيار افتراضي
            vehicle = selected_driver.vehicles.first()
            if not vehicle:
                self.stdout.write(self.style.ERROR(f'السائق {selected_driver.id} ليس لديه مركبة.'))
                continue

            trip = Trip.objects.create(
                from_location=sample.from_location,
                to_location=sample.to_location,
                departure_time=sample.departure_time,
                estimated_duration=None,
                available_seats=vehicle.capacity,
                distance_km=None,
                price_per_seat=25.0,  # سعر افتراضي لكل راكب
                driver=selected_driver,
                route_coordinates='{}'
            )

            current_seats = 0
            for b in cluster_bookings:
                if current_seats + b.passengers > vehicle.capacity:
                    self.stdout.write(self.style.WARNING(f'تجاوز السعة في الرحلة {trip.id}، تجاهل حجز {b.id}'))
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
                b.save()

                trip.available_seats = vehicle.capacity - current_seats
                trip.save()

                if trip.available_seats == 0:
                    trip.status = 'full'  # تأكد من وجود هذا الحقل أو الحالة
                    trip.save()

            self.stdout.write(self.style.SUCCESS(f'تم إنشاء الرحلة {trip.id} وتعيين السائق {selected_driver.user.username}'))
