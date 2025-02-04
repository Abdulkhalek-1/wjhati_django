import logging
from math import radians, cos, sin, asin, sqrt
from datetime import timedelta

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

# إعداد مسجل الأخطاء
logger = logging.getLogger(__name__)

###########################
# دوال مساعدة للتحليل الجغرافي
###########################

def haversine(lon1, lat1, lon2, lat2):
    """
    احسب المسافة بين نقطتين جغرافيتين باستخدام معادلة Haversine.
    تُرجع الدالة المسافة بالكيلومترات.
    """
    # تحويل الدرجات إلى راديان
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    km = 6371 * c  # نصف قطر الأرض بالكيلومترات
    return km

def parse_location_string(location_str):
    """
    تحويل سلسلة نصية تحتوي على إحداثيات بالشكل "lat, lon"
    إلى زوج من القيم الرقمية (lon, lat).
    تُعاد القيم بحيث يكون الترتيب (longitude, latitude) بما يتوافق مع دالة Haversine.
    """
    try:
        lat_str, lon_str = location_str.split(',')
        lat = float(lat_str.strip())
        lon = float(lon_str.strip())
        return lon, lat
    except Exception as e:
        logger.error("خطأ في تحويل سلسلة الإحداثيات '%s': %s", location_str, e)
        return None, None

def compute_route_coordinates(from_location, to_location):
    """
    دالة افتراضية لحساب مسار الرحلة.
    في هذا المثال، نقوم بإرجاع قائمة تحتوي على نقطتين (البداية والنهاية).
    يمكنك تعديل هذه الدالة لاستدعاء خدمة خارحية لحساب الطريق الفعلي.
    """
    from_lon, from_lat = parse_location_string(from_location)
    to_lon, to_lat = parse_location_string(to_location)
    if None in (from_lon, from_lat, to_lon, to_lat):
        return None
    # مثال: إرجاع نقطة البداية والنهاية فقط
    return [
        {"lon": from_lon, "lat": from_lat},
        {"lon": to_lon, "lat": to_lat}
    ]

###########################
# دوال دمج الحجوزات وإنشاء الرحلات
###########################

def get_available_driver():
    """
    دالة افتراضية لاختيار سائق متاح.
    يجب تعديلها لتناسب منطق تطبيقك.
    """
    from .models import Driver  # تأكد من تعديل مسار النموذج حسب مشروعك
    driver = Driver.objects.filter(is_available=True).first()
    return driver

def calculate_total_price(cashe_booking):
    """
    دالة افتراضية لحساب السعر الإجمالي بناءً على بيانات الحجز المسبق.
    يمكنك تعديل هذا المنطق بناءً على احتياجات التطبيق.
    """
    price_per_passenger = 10.00
    return cashe_booking.passengers * price_per_passenger

def merge_bookings_into_trip():
    """
    تقوم هذه الدالة بالبحث عن الحجوزات المسبقة (CasheBooking) ذات الحالة PENDING،
    وتجميعها بناءً على القرب الجغرافي (المواقع والوقت) بحيث يتم دمج الحجوزات المتقاربة في رحلة واحدة.
    
    يُفترض أن نموذج CasheBooking يحتوي على الحقول التالية:
      - from_location: سلسلة نصية بصيغة "lat, lon"
      - to_location: سلسلة نصية بصيغة "lat, lon"
      - departure_time: حقل التاريخ والوقت
      - passengers: عدد الركاب
      - user: المستخدم الذي قام بالحجز
      - status: حالة الحجز
    كما يُفترض أن نموذج Trip يحتوي على الحقول المناسبة لاستقبال بيانات الموقع والوقت.
    """
    from .models import CasheBooking, Trip, Booking

    # جلب الحجوزات المسبقة ذات الحالة PENDING
    pending_bookings = CasheBooking.objects.filter(status=CasheBooking.Status.PENDING)

    # معايير التجميع
    DISTANCE_THRESHOLD = 0.5  # بالكيلومتر
    TIME_DELTA = timedelta(minutes=15)  # فرق زمني مسموح

    booking_clusters = []

    def add_to_cluster(booking):
        """
        محاولة إضافة الحجز إلى إحدى المجموعات الموجودة إذا كانت المواقع والوقت متقاربين.
        """
        for cluster in booking_clusters:
            ref_booking = cluster[0]
            # استخراج الإحداثيات من الحقول النصية
            ref_from_lon, ref_from_lat = parse_location_string(ref_booking.from_location)
            ref_to_lon, ref_to_lat = parse_location_string(ref_booking.to_location)

            booking_from_lon, booking_from_lat = parse_location_string(booking.from_location)
            booking_to_lon, booking_to_lat = parse_location_string(booking.to_location)

            if None in (ref_from_lon, ref_from_lat, ref_to_lon, ref_to_lat,
                        booking_from_lon, booking_from_lat, booking_to_lon, booking_to_lat):
                continue

            distance_from = haversine(ref_from_lon, ref_from_lat, booking_from_lon, booking_from_lat)
            distance_to = haversine(ref_to_lon, ref_to_lat, booking_to_lon, booking_to_lat)
            time_diff = abs(ref_booking.departure_time - booking.departure_time)

            if distance_from <= DISTANCE_THRESHOLD and distance_to <= DISTANCE_THRESHOLD and time_diff <= TIME_DELTA:
                cluster.append(booking)
                return True
        return False

    # تجميع الحجوزات في مجموعات بناءً على القرب الجغرافي والزمني
    for booking in pending_bookings:
        if not add_to_cluster(booking):
            booking_clusters.append([booking])

    # استخدام معاملة قاعدة البيانات لضمان تماسك العملية
    with transaction.atomic():
        for cluster in booking_clusters:
            if cluster:
                driver = get_available_driver()
                if driver:
                    ref_booking = cluster[0]
                    try:
                        trip = Trip.objects.create(
                            driver=driver,
                            from_location=ref_booking.from_location,
                            to_location=ref_booking.to_location,
                            departure_time=ref_booking.departure_time
                            # يمكنك إضافة حقول إضافية حسب الحاجة
                        )
                    except Exception as e:
                        logger.error("خطأ عند إنشاء الرحلة: %s", e)
                        continue

                    # تحويل كل حجز مسبق في المجموعة إلى حجز نهائي وربطه بالرحلة
                    for cashe_booking in cluster:
                        try:
                            seats = [f"seat_{i+1}" for i in range(cashe_booking.passengers)]
                            total_price = calculate_total_price(cashe_booking)
                            Booking.objects.create(
                                trip=trip,
                                customer=cashe_booking.user,
                                seats=seats,
                                total_price=total_price,
                                status=Booking.Status.PENDING  # أو الحالة المناسبة وفقًا لمنطق التطبيق
                            )
                            cashe_booking.status = CasheBooking.Status.ACCEPTED
                            cashe_booking.save()
                        except Exception as e:
                            logger.error("خطأ عند تحويل حجز مسبق إلى حجز نهائي: %s", e)
                else:
                    logger.warning(
                        "لا يوجد سائق متاح للرحلة من %s إلى %s في %s",
                        ref_booking.from_location,
                        ref_booking.to_location,
                        ref_booking.departure_time
                    )

###########################
# إشارات (Signals) لتحديث التقييم ودمج الحجوزات
###########################

@receiver(post_save, sender='apis.Rating')  # استبدل 'your_app' باسم التطبيق الخاص بك
def update_driver_rating(sender, instance, **kwargs):
    """
    تحديث التقييم العام للسائق عند إضافة تقييم جديد.
    """
    driver = instance.driver
    try:
        driver.update_rating()
    except Exception as e:
        logger.error("خطأ عند تحديث تقييم السائق: %s", e)

@receiver(post_save, sender='apis.CasheBooking')  # استبدل 'your_app' باسم التطبيق الخاص بك
def handle_booking_post_save(sender, instance, created, **kwargs):
    """
    عند حفظ حجز مسبق جديد (CasheBooking) بحالة PENDING، يتم محاولة دمجه في رحلة.
    """
    if created and instance.status == instance.Status.PENDING:
        # استدعاء الدالة بدون تمرير instance، لأنها تتعامل مع جميع الحجوزات PENDING
        merge_bookings_into_trip()
