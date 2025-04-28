import json
import math
import logging
from datetime import timedelta
from django.db import transaction
from django.contrib.gis.geos import Point
from .models import Trip, TripStop, Booking, CasheBooking, Driver
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

class LocationUtils:
    """أدوات الموقع الجغرافي"""
    
    @staticmethod
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371  # نصف قطر الأرض بالكيلومتر
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    @staticmethod
    def parse_location(location_str):
        try:
            lat_str, lon_str = location_str.split(',')
            return float(lat_str.strip()), float(lon_str.strip())
        except Exception:
            logger.error(f"خطأ في تحويل الموقع: {location_str}")
            return None, None

class TripProcessor:
    """معالجة الرحلات والحجوزات"""
    
    @staticmethod
    def process_cashe_booking(cashe_booking):
        try:
            from_coords = LocationUtils.parse_location(cashe_booking.from_location)
            to_coords = LocationUtils.parse_location(cashe_booking.to_location)
            
            if None in (from_coords[0], from_coords[1], to_coords[0], to_coords[1]):
                raise ValueError("إحداثيات غير صالحة")
            
            matched_trip = TripProcessor.find_matching_trip(from_coords, to_coords, cashe_booking.departure_time)
            
            if matched_trip:
                TripProcessor.create_booking_for_trip(matched_trip, cashe_booking)
            else:
                TripProcessor.create_new_trip(cashe_booking)
                
        except Exception as e:
            logger.error(f"خطأ في معالجة الحجز: {e}")
            raise

    @staticmethod
    def find_matching_trip(from_coords, to_coords, departure_time):
        try:
            time_window = timedelta(minutes=30)
            trips = Trip.objects.filter(
                status=Trip.Status.PENDING,
                departure_time__range=(departure_time - time_window, departure_time + time_window),
                route_coordinates__isnull=False
            )
            for trip in trips:
                if (TripProcessor.is_point_near_stops(trip, from_coords) and 
                    TripProcessor.is_point_near_stops(trip, to_coords)):
                    return trip
            return None
        except Exception as e:
            logger.error(f"خطأ في البحث عن رحلة: {e}")
            return None

    @staticmethod
    def is_point_near_stops(trip, point, threshold=1.0):
        for stop in trip.stops.all():
            stop_coords = LocationUtils.parse_location(stop.location)
            if stop_coords and LocationUtils.haversine(*stop_coords, *point) <= threshold:
                return True
        return False

    @staticmethod
    def create_booking_for_trip(trip, cashe_booking):
        try:
            with transaction.atomic():
                price = trip.price_per_seat * cashe_booking.passengers
                Booking.objects.create(
                    trip=trip,
                    customer=cashe_booking.user,
                    seats=[],
                    total_price=price,
                    status=Booking.Status.CONFIRMED
                )
                CasheBooking.objects.filter(pk=cashe_booking.pk).update(status=CasheBooking.Status.ACCEPTED)
        except Exception as e:
            logger.error(f"خطأ في إنشاء الحجز: {e}")
            raise

    @staticmethod
    def create_new_trip(cashe_booking):
        try:
            driver = Driver.objects.filter(is_available=True).first()
            if not driver:
                raise ValueError("لا يوجد سائق متاح")
            
            from_coords = LocationUtils.parse_location(cashe_booking.from_location)
            to_coords = LocationUtils.parse_location(cashe_booking.to_location)
            
            distance = LocationUtils.haversine(*from_coords, *to_coords)
            route = [{"lat": from_coords[0], "lon": from_coords[1]}, {"lat": to_coords[0], "lon": to_coords[1]}]
            
            with transaction.atomic():
                new_trip = Trip.objects.create(
                    from_location=cashe_booking.from_location,
                    to_location=cashe_booking.to_location,
                    departure_time=cashe_booking.departure_time,
                    available_seats=driver.vehicles.first().capacity if driver.vehicles.exists() else 100,
                    price_per_seat=max(50.0, distance * 2.5),
                    estimated_duration=timedelta(hours=distance / 60),
                    driver=driver,
                    route_coordinates=json.dumps(route),
                    status=Trip.Status.PENDING
                )
                Booking.objects.create(
                    trip=new_trip,
                    customer=cashe_booking.user,
                    seats=[],
                    total_price=new_trip.price_per_seat * cashe_booking.passengers,
                    status=Booking.Status.CONFIRMED
                )
                CasheBooking.objects.filter(pk=cashe_booking.pk).update(status=CasheBooking.Status.ACCEPTED)
        except Exception as e:
            logger.error(f"خطأ في إنشاء الرحلة: {e}")
            raise

    @staticmethod
    def compute_trip_stops(trip, stop_interval=5):
        try:
            if not trip.route_coordinates:
                return
            
            route = json.loads(trip.route_coordinates)
            trip.stops.all().delete()
            
            accumulated_distance = 0.0
            prev_point = route[0]
            
            for i in range(1, len(route)):
                curr_point = route[i]
                segment_distance = LocationUtils.haversine(prev_point['lat'], prev_point['lon'], curr_point['lat'], curr_point['lon'])
                
                while accumulated_distance + segment_distance >= stop_interval:
                    remaining = stop_interval - accumulated_distance
                    fraction = remaining / segment_distance
                    
                    stop_lat = prev_point['lat'] + fraction * (curr_point['lat'] - prev_point['lat'])
                    stop_lon = prev_point['lon'] + fraction * (curr_point['lon'] - prev_point['lon'])
                    
                    TripStop.objects.create(
                        trip=trip,
                        location=f"{stop_lat},{stop_lon}",
                        order=trip.stops.count() + 1
                    )
                    
                    prev_point = {'lat': stop_lat, 'lon': stop_lon}
                    segment_distance = LocationUtils.haversine(stop_lat, stop_lon, curr_point['lat'], curr_point['lon'])
                    accumulated_distance = 0.0
                
                accumulated_distance += segment_distance
                prev_point = curr_point
        except Exception as e:
            logger.error(f"خطأ في حساب نقاط التوقف: {e}")
            raise

    @staticmethod
    def merge_similar_trips(current_trip, distance_threshold=1.0):
        try:
            current_route = json.loads(current_trip.route_coordinates)
            similar_trips = Trip.objects.exclude(pk=current_trip.pk).filter(
                status=Trip.Status.PENDING,
                route_coordinates__isnull=False
            )
            
            for trip in similar_trips:
                other_route = json.loads(trip.route_coordinates)
                if TripProcessor.discrete_frechet_distance(current_route, other_route) < distance_threshold:
                    with transaction.atomic():
                        for booking in trip.bookings.all():
                            booking.trip = current_trip
                            booking.save(update_fields=['trip'])
                        trip.delete()
        except Exception as e:
            logger.error(f"خطأ في دمج الرحلات: {e}")
            raise

    @staticmethod
    def discrete_frechet_distance(P, Q):
        n = len(P)
        m = len(Q)
        ca = [[-1 for _ in range(m)] for _ in range(n)]
        
        def c(i, j):
            if ca[i][j] > -1:
                return ca[i][j]
            d = LocationUtils.haversine(P[i]['lat'], P[i]['lon'], Q[j]['lat'], Q[j]['lon'])
            if i == 0 and j == 0:
                ca[i][j] = d
            elif i > 0 and j == 0:
                ca[i][j] = max(c(i-1, 0), d)
            elif i == 0 and j > 0:
                ca[i][j] = max(c(0, j-1), d)
            elif i > 0 and j > 0:
                ca[i][j] = max(min(c(i-1, j), c(i-1, j-1), c(i, j-1)), d)
            else:
                ca[i][j] = float('inf')
            return ca[i][j]
        
        return c(n-1, m-1)