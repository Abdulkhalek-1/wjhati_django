# -*- coding: utf-8 -*-
import uuid
import logging
import numpy as np
from datetime import timedelta
from django.db import models, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# ========================================
# النماذج (Models)
# ========================================
class Client(models.Model):
    user = models.CharField(max_length=100)
    def __str__(self):
        return self.user

class Driver(models.Model):
    name = models.CharField(max_length=100)
    is_available = models.BooleanField(default=True)
    capacity = models.IntegerField(default=4)
    current_lat = models.FloatField()  # خط العرض الحالي للسائق
    current_lng = models.FloatField()  # خط الطول الحالي للسائق
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.0)
    def __str__(self):
        return self.name

class Trip(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', "قيد الانتظار"
        IN_PROGRESS = 'in_progress', "قيد التنفيذ"
        COMPLETED = 'completed', "مكتمل"
        CANCELLED = 'cancelled', "ملغاة"

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='trips')
    from_lat = models.FloatField()  # خط العرض المبدئي
    from_lng = models.FloatField()  # خط الطول المبدئي
    to_lat = models.FloatField()    # خط العرض النهائي
    to_lng = models.FloatField()    # خط الطول النهائي
    departure_time = models.DateTimeField()
    available_seats = models.IntegerField(default=0)
    price_per_seat = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ['-departure_time']
        indexes = [models.Index(fields=['departure_time']), models.Index(fields=['status'])]

    def __str__(self):
        return f"رحلة ID: {self.id} - {self.get_status_display()}"

class BookingRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', "قيد الانتظار"
        MERGED = 'merged', "تم الدمج"
        FAILED = 'failed', "فشل"

    user = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='booking_requests')
    from_lat = models.FloatField()
    from_lng = models.FloatField()
    to_lat = models.FloatField()
    to_lng = models.FloatField()
    departure_time = models.DateTimeField()
    passengers = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"طلب حجز ID: {self.id} - {self.user}"

class Booking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = 'confirmed', "مؤكد"
        COMPLETED = 'completed', "مكتمل"
        CANCELLED = 'cancelled', "ملغى"

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='bookings')
    customer = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='bookings')
    seats = models.JSONField(default=list)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"حجز ID: {self.id} - {self.customer}"

# ========================================
# محسن الرحلة (Trip Optimizer)
# ========================================
class TripOptimizer:
    def __init__(self, time_window=15, max_detour_km=5, proximity_threshold_m=1000):
        self.time_window = time_window
        self.max_detour_km = max_detour_km
        self.proximity_threshold_m = proximity_threshold_m

    def haversine(self, lat1, lng1, lat2, lng2):
        """حساب المسافة بين نقطتين بالكيلومترات"""
        from math import radians, sin, cos, sqrt, atan2
        R = 6371  # نصف قطر الأرض
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c

    def is_route_close(self, req1, req2):
        """التحقق من تقارب المسارين"""
        # حساب المسافة بين نقاط الانطلاق
        distance_from = self.haversine(req1.from_lat, req1.from_lng, req2.from_lat, req2.from_lng)
        # حساب المسافة بين نقاط الوصول
        distance_to = self.haversine(req1.to_lat, req1.to_lng, req2.to_lat, req2.to_lng)
        # التحقق من العتبة المحددة (بالأمتار)
        return (distance_from * 1000 <= self.proximity_threshold_m and 
                distance_to * 1000 <= self.proximity_threshold_m)

    def calculate_centroid(self, points):
        """حساب المركز الجغرافي لمجموعة نقاط"""
        lats = [point[0] for point in points]
        lngs = [point[1] for point in points]
        return (np.mean(lats), np.mean(lngs))

    def find_nearest_driver(self, merged_from_lat, merged_from_lng, total_passengers):
        """البحث عن أقرب سائق متاح ضمن نطاق الالتفاف المسموح"""
        drivers = Driver.objects.filter(is_available=True, capacity__gte=total_passengers)
        for driver in drivers:
            distance = self.haversine(
                merged_from_lat, merged_from_lng,
                driver.current_lat, driver.current_lng
            )
            if distance <= self.max_detour_km:
                return driver
        return None

    @transaction.atomic
    def process_new_booking(self, new_request):
        # الخطوة 1: البحث عن طلبات متشابهة
        time_lower = new_request.departure_time - timedelta(minutes=self.time_window)
        time_upper = new_request.departure_time + timedelta(minutes=self.time_window)
        
        similar_requests = BookingRequest.objects.filter(
            status=BookingRequest.Status.PENDING,
            departure_time__range=(time_lower, time_upper)
        ).exclude(pk=new_request.pk)

        # الخطوة 2: دمج الطلبات المتقاربة
        merged_requests = [new_request]
        for req in similar_requests:
            if self.is_route_close(new_request, req):
                merged_requests.append(req)

        # الخطوة 3: حساب إجمالي الركاب والنقاط المركزية
        total_passengers = sum(req.passengers for req in merged_requests)
        from_points = [(req.from_lat, req.from_lng) for req in merged_requests]
        to_points = [(req.to_lat, req.to_lng) for req in merged_requests]
        merged_from_lat, merged_from_lng = self.calculate_centroid(from_points)
        merged_to_lat, merged_to_lng = self.calculate_centroid(to_points)
        departure_time = max(req.departure_time for req in merged_requests) + timedelta(minutes=10)

        # الخطوة 4: البحث عن سائق مناسب
        driver = self.find_nearest_driver(merged_from_lat, merged_from_lng, total_passengers)
        if not driver:
            for req in merged_requests:
                req.status = BookingRequest.Status.FAILED
                req.save()
            logger.error("فشل في إيجاد سائق")
            return None

        # الخطوة 5: إنشاء الرحلة
        trip = Trip.objects.create(
            driver=driver,
            from_lat=merged_from_lat,
            from_lng=merged_from_lng,
            to_lat=merged_to_lat,
            to_lng=merged_to_lng,
            departure_time=departure_time,
            available_seats=driver.capacity - total_passengers,
            price_per_seat=100.00,  # يمكن استبدالها بمنطق التسعير
            status=Trip.Status.PENDING
        )

        # الخطوة 6: إنشاء الحجوزات وتحديث حالة الطلبات
        bookings = []
        for req in merged_requests:
            booking = Booking.objects.create(
                trip=trip,
                customer=req.user,
                seats=[str(uuid.uuid4().hex[:6]) for _ in range(req.passengers)],
                total_price=req.passengers * trip.price_per_seat,
                status=Booking.Status.CONFIRMED
            )
            bookings.append(booking)
            req.status = BookingRequest.Status.MERGED
            req.save()

        logger.info(f"تم إنشاء رحلة جديدة ID: {trip.id} مع {len(bookings)} حجوزات")
        return trip