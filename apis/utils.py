import logging
import math
import json
import numpy as np
from datetime import timedelta
from uuid import uuid4
from sklearn.cluster import DBSCAN
from django.db import transaction
from django.contrib.gis.geos import Point
from django.db.models import F, Q
from django.utils import timezone
from django.core.exceptions import ValidationError

from apis.models import CasheBooking

logger = logging.getLogger(__name__)

class TripOptimizer:
    """فئة لتحسين وتجميع الرحلات باستخدام خوارزميات الذكاء الاصطناعي"""
    
    def __init__(self, time_window=15, max_detour=5, min_cluster_size=2):
        """
        تهيئة محسن الرحلات
        :param time_window: نافذة الوقت بالدقائق لتجميع الرحلات
        :param max_detour: أقصى انحراف مسموح به بالكيلومترات
        :param min_cluster_size: الحد الأدنى لحجم المجموعة
        """
        self.time_window = timedelta(minutes=time_window)
        self.max_detour_km = max_detour
        self.min_cluster_size = min_cluster_size
        self.dbscan_eps = 1000  # مسافة التجميع بالمتر

    @transaction.atomic
    def process_pending_bookings(self):
        """
        المعالجة الرئيسية للحجوزات المعلقة مع إدارة الأخطاء
        """
        from .models import CasheBooking, Trip, Booking, Driver
        
        try:
            # جلب الحجوزات المعلقة مع تحسين الاستعلام
            pending_bookings = CasheBooking.objects.filter(
                status=CasheBooking.Status.PENDING
            ).select_related('user').prefetch_related('passengers')
            
            if not pending_bookings.exists():
                logger.info("لا توجد حجوزات معلقة للمعالجة")
                return

            clusters = self._cluster_bookings(pending_bookings)
            self._process_clusters(clusters)
            
        except Exception as e:
            logger.error(f"فشل في معالجة الحجوزات: {str(e)}")
            raise

    def _cluster_bookings(self, bookings):
        """
        تجميع الحجوزات باستخدام خوارزمية DBSCAN
        :param bookings: queryset للحجوزات
        :return: قاموس للمجموعات
        """
        try:
            # تحضير البيانات للخوارزمية
            coords = []
            valid_bookings = []
            
            for booking in bookings:
                try:
                    coords.append([
                        booking.from_location.x,
                        booking.from_location.y,
                        booking.to_location.x,
                        booking.to_location.y,
                        booking.departure_time.timestamp()
                    ])
                    valid_bookings.append(booking)
                except AttributeError as e:
                    logger.warning(f"حجز غير صالح {booking.id}: {str(e)}")
                    continue

            if not coords:
                return {}

            # تطبيق خوارزمية التجميع
            X = np.array(coords)
            db = DBSCAN(eps=self.dbscan_eps, min_samples=self.min_cluster_size).fit(X)
            
            # تنظيم النتائج
            clusters = {}
            for label, booking in zip(db.labels_, valid_bookings):
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(booking)
                
            return clusters

        except Exception as e:
            logger.error(f"خطأ في تجميع الحجوزات: {str(e)}")
            raise

    def _process_clusters(self, clusters):
        """
        معالجة المجموعات وإنشاء الرحلات
        :param clusters: قاموس المجموعات
        """
        from .models import Trip, Booking, CasheBooking
        
        for cluster_id, cluster in clusters.items():
            if cluster_id == -1 or len(cluster) < self.min_cluster_size:
                self._handle_single_bookings(cluster)
                continue

            try:
                with transaction.atomic():
                    # تحسين المسار
                    optimized_route = self._optimize_route(cluster)
                    
                    # اختيار السائق الأنسب
                    driver = self._select_best_driver(optimized_route)
                    if not driver:
                        raise ValueError("لا يوجد سائق متاح")
                    
                    # إنشاء الرحلة
                    trip = self._create_trip(driver, optimized_route)
                    
                    # إنشاء الحجوزات
                    self._create_bookings(trip, optimized_route)
                    
                    # تحديث حالة الحجوزات المسبقة
                    self._update_cache_bookings(cluster, CasheBooking.Status.COMPLETED)
                    
                    logger.info(f"تم إنشاء رحلة {trip.id} لـ {len(cluster)} حجوزات")

            except Exception as e:
                logger.error(f"فشل معالجة المجموعة {cluster_id}: {str(e)}")
                self._update_cache_bookings(cluster, CasheBooking.Status.FAILED)

    def _optimize_route(self, cluster):
        """
        تحسين مسار الرحلة (تنفيذ مبسط لخوارزمية TSP)
        :param cluster: قائمة الحجوزات في المجموعة
        :return: قائمة مرتبة من الحجوزات
        """
        # يمكن استبدال هذا بتنفيذ أكثر تطوراً لخوارزمية TSP
        return sorted(
            cluster,
            key=lambda x: x.from_location.distance(x.to_location)
        )

    def _select_best_driver(self, cluster):
        """
        اختيار السائق الأنسب بناء على الموقع والتقييم
        :param cluster: قائمة الحجوزات
        :return: كائن السائق أو None
        """
        from .models import Driver
        
        try:
            centroid = self._calculate_centroid([b.from_location for b in cluster])
            total_passengers = sum(b.passengers.count() for b in cluster)
            
            return Driver.objects.filter(
                Q(is_available=True) &
                Q(capacity__gte=total_passengers) &
                Q(current_location__distance_lte=(centroid, self.max_detour_km * 1000))
            ).annotate(
                distance_score=F('current_location__distance') / 1000,
                overall_score=F('rating') - (F('distance_score') / self.max_detour_km)
            ).order_by('-overall_score').first()
            
        except Exception as e:
            logger.error(f"خطأ في اختيار السائق: {str(e)}")
            return None

    def _create_trip(self, driver, cluster):
        """
        إنشاء رحلة جديدة بناء على الحجوزات المجمعة
        :param driver: السائق المختار
        :param cluster: قائمة الحجوزات
        :return: كائن الرحلة
        """
        from .models import Trip
        
        departure_time = self._calculate_departure_time(cluster)
        from_location = self._calculate_centroid([b.from_location for b in cluster])
        to_location = self._calculate_centroid([b.to_location for b in cluster])
        
        return Trip.objects.create(
            driver=driver,
            from_location=from_location,
            to_location=to_location,
            departure_time=departure_time,
            price_per_seat=self._calculate_dynamic_price(cluster),
            available_seats=driver.capacity,
            status=Trip.Status.PENDING,
            route_data=self._generate_route_data(cluster),
            optimized_route=self._generate_optimized_route(cluster)
        )

    def _create_bookings(self, trip, cluster):
        """
        إنشاء حجوزات للرحلة الجديدة
        :param trip: الرحلة الجديدة
        :param cluster: قائمة الحجوزات المسبقة
        """
        from .models import Booking
        
        bookings = []
        for cache_booking in cluster:
            bookings.append(Booking(
                trip=trip,
                customer=cache_booking.user,
                seats=self._generate_seat_numbers(cache_booking.passengers.count()),
                total_price=cache_booking.passengers.count() * trip.price_per_seat,
                status=Booking.Status.CONFIRMED,
                meta_data={
                    'original_cache_id': cache_booking.id,
                    'passengers': [p.id for p in cache_booking.passengers.all()]
                }
            ))
        
        Booking.objects.bulk_create(bookings)

    # ==================== الوظائف المساعدة ====================

    def _calculate_centroid(self, points):
        """حساب المركز الجغرافي لنقاط متعددة"""
        x_coords = [p.x for p in points]
        y_coords = [p.y for p in points]
        return Point(np.mean(x_coords), np.mean(y_coords))

    def _calculate_departure_time(self, cluster):
        """حساب وقت المغادرة الأمثل"""
        latest_time = max(b.departure_time for b in cluster)
        return latest_time + (self.time_window / 2)

    def _calculate_dynamic_price(self, cluster):
        """حساب السعر الديناميكي بناء على الطلب والوقت"""
        base_price = 50.00
        demand_factor = min(2.0, 1 + (len(cluster) / 10))
        time_factor = 1.2 if self._is_peak_time() else 0.9
        return round(base_price * demand_factor * time_factor, 2)

    def _is_peak_time(self):
        """تحديد إذا كان الوقت ذروة"""
        now = timezone.now().time()
        return (timedelta(hours=7)) <= now <= (timedelta(hours=9)) or \
               (timedelta(hours=16)) <= now <= (timedelta(hours=19))

    def _generate_seat_numbers(self, count):
        """إنشاء أرقام مقاعد عشوائية"""
        return [str(uuid4())[:8] for _ in range(count)]

    def _generate_route_data(self, cluster):
        """إنشاء بيانات المسار"""
        return {
            'original_locations': [
                {
                    'from': {'lat': b.from_location.y, 'lng': b.from_location.x},
                    'to': {'lat': b.to_location.y, 'lng': b.to_location.x},
                    'time': b.departure_time.isoformat()
                }
                for b in cluster
            ]
        }

    def _generate_optimized_route(self, cluster):
        """إنشاء المسار المحسن"""
        # يمكن استبدال هذا بخوارزمية أكثر تطوراً
        points = []
        for b in cluster:
            points.extend([
                {'lat': b.from_location.y, 'lng': b.from_location.x},
                {'lat': b.to_location.y, 'lng': b.to_location.x}
            ])
        return {'path': points}

    def _update_cache_bookings(self, cluster, status):
        """تحديث حالة الحجوزات المسبقة"""
        from .models import CasheBooking
        CasheBooking.objects.filter(
            id__in=[b.id for b in cluster]
        ).update(status=status)

    def _handle_single_bookings(self, bookings):
        """معالجة الحجوزات المنفردة التي لا يمكن تجميعها"""
        if not bookings:
            return
            
        logger.info(f"معالجة {len(bookings)} حجوزات منفردة")
        self._update_cache_bookings(bookings, CasheBooking.Status.INDIVIDUAL)