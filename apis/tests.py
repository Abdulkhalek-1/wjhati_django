# -*- coding: utf-8 -*-
import uuid
import logging
import numpy as np
from datetime import timedelta

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
from django.db import models, transaction
from django.utils import timezone

# إعداد اللوجر
logger = logging.getLogger(__name__)

# ============================
# تعريف النماذج
# ============================

# نموذج المستخدم (مثال)
class Client(models.Model):
    user = models.CharField(max_length=100)  # افتراض بسيط لتخزين اسم المستخدم

    def __str__(self):
        return self.user

# نموذج السائق (مثال)
class Driver(models.Model):
    name = models.CharField(max_length=100)
    is_available = models.BooleanField(default=True)
    capacity = models.IntegerField(default=4)
    current_location = models.PointField()

    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.0)

    def __str__(self):
        return self.name

# نموذج الرحلة
class Trip(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', "قيد الانتظار"
        IN_PROGRESS = 'in_progress', "قيد التنفيذ"
        COMPLETED = 'completed', "مكتمل"
        CANCELLED = 'cancelled', "ملغاة"

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='trips')
    from_location = models.PointField(verbose_name="من")
    to_location = models.PointField(verbose_name="إلى")
    departure_time = models.DateTimeField(verbose_name="وقت المغادرة")
    available_seats = models.IntegerField(default=0, verbose_name="عدد المقاعد المتاحة")
    price_per_seat = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="السعر لكل مقعد")
    route_data = models.JSONField(null=True, blank=True, verbose_name="بيانات المسار")  # مسار الرحلة (مثلاً قائمة من النقاط)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="الحالة")

    class Meta:
        ordering = ['-departure_time']
        indexes = [
            models.Index(fields=['departure_time']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"رحلة من {self.from_location} إلى {self.to_location} في {self.departure_time}"

# نموذج طلب الحجز المبدئي (قبل دمجها في رحلة)
class BookingRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', "قيد الانتظار"
        MERGED = 'merged', "تم الدمج"
        FAILED = 'failed', "فشل"

    user = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='booking_requests')
    # مواقع الالتقاط والوصول كنقاط GIS
    from_location = models.PointField(verbose_name="نقطة الانطلاق")
    to_location = models.PointField(verbose_name="نقطة الوصول")
    departure_time = models.DateTimeField(verbose_name="وقت المغادرة المطلوب")
    passengers = models.IntegerField(default=1, verbose_name="عدد الركاب")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="حالة الطلب")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"طلب حجز {self.user} من {self.from_location} إلى {self.to_location}"

# نموذج الحجز النهائي (بعد الدمج مع الرحلة)
class Booking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = 'confirmed', "مؤكد"
        COMPLETED = 'completed', "مكتمل"
        CANCELLED = 'cancelled', "ملغى"

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='bookings')
    customer = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='bookings')
    seats = models.JSONField(default=list, verbose_name="المقاعد المحجوزة", help_text="قائمة بأرقام المقاعد")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="المبلغ الإجمالي")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED, verbose_name="الحالة")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"حجز {self.customer} للرحلة {self.trip}"

# ============================
# كلاس تحسين الرحلة (Trip Optimizer)
# ============================
class TripOptimizer:
    def __init__(self, time_window=15, max_detour_km=5, proximity_threshold_m=1000):
        """
        :param time_window: فترة زمنية للتحقق من تداخل الحجوزات (بالدقائق)
        :param max_detour_km: الحد الأقصى للالتفاف المسموح (بالكيلومترات)
        :param proximity_threshold_m: العتبة الجغرافية للتقارب بين النقاط (بالمتر)
        """
        self.time_window = time_window
        self.max_detour_km = max_detour_km
        self.proximity_threshold_m = proximity_threshold_m

    def is_route_close(self, pt1_from, pt1_to, pt2_from, pt2_to):
        """
        التحقق من تقارب مسارين عبر مقارنة مسافة نقطة الانطلاق ونقطة الوصول.
        """
        distance_from = pt1_from.distance(pt2_from)  # المسافة بين نقاط الانطلاق
        distance_to = pt1_to.distance(pt2_to)          # المسافة بين نقاط الوصول
        return (distance_from * 100) <= self.proximity_threshold_m and (distance_to * 100) <= self.proximity_threshold_m
        # ملحوظة: قد تحتاج لتعديل معامل التحويل بحسب وحدة القياس لنقاط GIS (عادةً تكون بالدرجات؛ استخدم طرق التحويل المناسبة)

    def calculate_centroid(self, points):
        """
        حساب مركز مجموعة من النقاط.
        """
        x_coords = [point.x for point in points]
        y_coords = [point.y for point in points]
        return Point(np.mean(x_coords), np.mean(y_coords))

    def generate_route_data(self, from_point, to_point):
        """
        إنشاء بيانات المسار بين نقطتين بصيغة JSON.
        هنا مثال مبسط يرجع قائمة بالإحداثيات.
        """
        return {
            "from": {"lat": from_point.y, "lng": from_point.x},
            "to": {"lat": to_point.y, "lng": to_point.x},
        }

    def calculate_dynamic_pricing(self, total_passengers):
        """
        حساب سعر الديناميكي لكل مقعد.
        """
        base_price = 50.00
        demand_factor = total_passengers / 10
        time_factor = 1.2 if self.is_peak_time() else 0.9
        return round(base_price * demand_factor * time_factor, 2)

    def is_peak_time(self):
        """
        تحديد ما إذا كان الوقت الحالي ضمن أوقات الذروة.
        """
        current_hour = timezone.now().hour
        return (7 <= current_hour <= 9) or (17 <= current_hour <= 19)

    def assign_seats(self, passengers):
        """
        توليد أرقام المقاعد بشكل عشوائي.
        """
        return [f"{uuid.uuid4().hex[:6]}" for _ in range(passengers)]

    @transaction.atomic
    def process_new_booking(self, new_request):
        """
        عند إنشاء طلب حجز جديد يتم البحث عن طلبات أخرى متقاربة من حيث المسار والوقت،
        فإذا وُجدت تُدمج في رحلة واحدة ويتم إنشاء الحجز النهائي.
        """
        from django.db.models import Q

        # البحث عن طلبات حجز مبدئية ضمن الفترة الزمنية المحددة والتي لم تُدمج بعد
        time_lower_bound = new_request.departure_time - timedelta(minutes=self.time_window)
        time_upper_bound = new_request.departure_time + timedelta(minutes=self.time_window)

        similar_requests = BookingRequest.objects.filter(
            status=BookingRequest.Status.PENDING,
            departure_time__range=(time_lower_bound, time_upper_bound)
        ).exclude(pk=new_request.pk)  # استبعاد الطلب الحالي

        merged_requests = [new_request]  # نبدأ بالطلب الجديد

        # البحث عن الطلبات التي مساراتها متقاربة مع الطلب الجديد
        for req in similar_requests:
            if self.is_route_close(new_request.from_location, new_request.to_location,
                                   req.from_location, req.to_location):
                merged_requests.append(req)

        total_passengers = sum(req.passengers for req in merged_requests)
        logger.info(f"تم العثور على {len(merged_requests)} طلب/طلبات متقاربة بإجمالي {total_passengers} راكب/ركاب.")

        # تحديد نقطة الانطلاق والوجهة للرحلة عبر حساب المركز (centroid) لمواقع جميع الطلبات
        merged_from_locations = [req.from_location for req in merged_requests]
        merged_to_locations = [req.to_location for req in merged_requests]

        trip_from = self.calculate_centroid(merged_from_locations)
        trip_to = self.calculate_centroid(merged_to_locations)
        departure_time = max(req.departure_time for req in merged_requests) + timedelta(minutes=self.time_window // 2)

        # اختيار سائق مناسب (مثال مبسط: أول سائق متاح قريب من نقطة الانطلاق)
        driver = Driver.objects.filter(
            is_available=True,
            capacity__gte=total_passengers,
            current_location__distance_lte=(trip_from, Distance(km=self.max_detour_km))
        ).order_by('-rating').first()

        if not driver:
            # في حالة عدم وجود سائق متاح، يتم تغيير حالة الطلب إلى فشل
            for req in merged_requests:
                req.status = BookingRequest.Status.FAILED
                req.save()
            logger.error("لم يتم العثور على سائق متاح للطلبات المدمجة.")
            return None

        # حساب السعر لكل مقعد باستخدام التسعير الديناميكي
        price_per_seat = self.calculate_dynamic_pricing(total_passengers)

        # إنشاء الرحلة الجديدة
        trip = Trip.objects.create(
            driver=driver,
            from_location=trip_from,
            to_location=trip_to,
            departure_time=departure_time,
            available_seats=driver.capacity,
            price_per_seat=price_per_seat,
            route_data=self.generate_route_data(trip_from, trip_to),
            status=Trip.Status.PENDING
        )

        # إنشاء الحجوزات النهائية لكل طلب مدمج
        bookings = []
        for req in merged_requests:
            booking = Booking(
                trip=trip,
                customer=req.user,
                seats=self.assign_seats(req.passengers),
                total_price=req.passengers * price_per_seat,
                status=Booking.Status.CONFIRMED
            )
            bookings.append(booking)
            # تحديث حالة طلب الحجز ليصبح مدمجاً
            req.status = BookingRequest.Status.MERGED
            req.save()

        Booking.objects.bulk_create(bookings)
        logger.info(f"تم إنشاء رحلة {trip.id} مع {len(bookings)} حجز/حجوزات.")

        return trip

# ============================
# مثال على الاستخدام
# ============================
if __name__ == "__main__":
    # افتراض وجود طلب حجز جديد (مثال تجريبي)
    from django.contrib.gis.geos import GEOSGeometry

    # يتم إنشاء نقاط باستخدام خطوط الطول والعرض (مثال: النقاط بصيغة WKT)
    point_a = GEOSGeometry('POINT(30.0 31.0)')
    point_b = GEOSGeometry('POINT(30.05 31.05)')

    # إنشاء عميل وهمي
    client, _ = Client.objects.get_or_create(user="user1")

    # إنشاء طلب حجز جديد
    new_booking_request = BookingRequest.objects.create(
        user=client,
        from_location=point_a,
        to_location=point_b,
        departure_time=timezone.now() + timedelta(hours=1),
        passengers=2
    )

    optimizer = TripOptimizer(time_window=15, max_detour_km=5, proximity_threshold_m=1000)
    optimizer.process_new_booking(new_booking_request)
