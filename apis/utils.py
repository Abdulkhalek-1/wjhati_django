import json
import math
from .models import Trip,TripStop,Booking,CasheBooking,Driver,Bonus
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User

def process_cashe_booking(booking, stop_proximity_threshold=1.0):
    """
    تقوم هذه الدالة بمعالجة طلب الحجز المسبق (CasheBooking) كالآتي:
    1. تحويل بيانات المواقع إلى إحداثيات.
    2. البحث عن رحلة موجودة (قيد الانتظار) تحتوي على نقاط توقف قريبة من
       موقعي الانطلاق والوصول.
    3. إذا وُجدت رحلة مطابقة يتم تسجيل الحجز بها.
    4. إذا لم توجد، يتم إنشاء رحلة جديدة باستخدام بيانات الطلب وحساب نقاط التوقف.
    5. يتم نقل بيانات الطلب إلى جدول الحجوزات (Booking) وتأكيد الحجز.
    """
    # تحويل الموقع من نص إلى إحداثيات
    from_coords = parse_location(booking.from_location)
    to_coords = parse_location(booking.to_location)
    if None in (from_coords[0], from_coords[1], to_coords[0], to_coords[1]):
        # يمكن إضافة معالجة خطأ هنا
        return

    # البحث عن رحلة موجودة (مثلاً حالة PENDING) ونبحث في نقاط توقفها
    candidate_trips = Trip.objects.filter(status=Trip.Status.PENDING, route_coordinates__isnull=False)
    matched_trip = None
    for trip in candidate_trips:
        if is_point_near_stops(trip, from_coords, threshold=stop_proximity_threshold) and \
           is_point_near_stops(trip, to_coords, threshold=stop_proximity_threshold):
            matched_trip = trip
            break

    if matched_trip:
        # تسجيل الحجز في الرحلة الموجودة
        new_booking = Booking.objects.create(
            trip=matched_trip,
            customer=booking.user,  # نفترض أن حقل user في CasheBooking هو العميل
            seats=[],  # يمكن تعبئتها بناءً على منطق آخر
            total_price=0,  # يمكن حسابها بناءً على السعر والمسافة
            status=Booking.Status.CONFIRMED
        )
        booking.status = CasheBooking.Status.ACCEPTED
        booking.save()
    else:
        # لا توجد رحلة مطابقة، إذًا إنشاء رحلة جديدة
        # اختيار سائق افتراضي من السائقين المتاحين
        default_driver = Driver.objects.filter(is_available=True).first()
        if not default_driver:
            # يمكن رفع استثناء أو اتخاذ إجراء بديل
            return

        # لتوليد مسار بسيط نستخدم نقطتي البداية والنهاية فقط،
        # ويمكن تعديل هذا الجزء لدمج API خارجي للحصول على مسار دقيق.
        route = [
            {"lat": from_coords[0], "lon": from_coords[1]},
            {"lat": to_coords[0], "lon": to_coords[1]},
        ]
        new_trip = Trip.objects.create(
            from_location=booking.from_location,
            to_location=booking.to_location,
            departure_time=booking.departure_time,
            available_seats=default_driver.vehicles.first().capacity if default_driver.vehicles.exists() else 100,
            driver=default_driver,
            route_coordinates=json.dumps(route)
        )
        # بعد إنشاء الرحلة، سيتم حساب نقاط التوقف تلقائيًا بواسطة إشارة post_save الخاصة بـ Trip

        # إنشاء حجز للرحلة الجديدة
        new_booking = Booking.objects.create(
            trip=new_trip,
            customer=booking.user,
            seats=[],
            total_price=0,
            status=Booking.Status.CONFIRMED
        )
        booking.status = CasheBooking.Status.ACCEPTED
        booking.save()


def haversine(lat1, lon1, lat2, lon2):
    """
    دالة لحساب المسافة (بالكيلومترات) بين نقطتين باستخدام صيغة haversine.
    """
    R = 6371  # نصف قطر الأرض بالكيلومتر
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def discrete_frechet_distance(P, Q):
    """
    حساب المسافة المنفصلة لخوارزمية Fréchet بين مسارين (قائمتين من النقاط)
    حيث تكون كل نقطة عبارة عن قاموس يحتوي على المفاتيح 'lat' و 'lon'.
    """
    n = len(P)
    m = len(Q)
    ca = [[-1 for _ in range(m)] for _ in range(n)]

    def c(i, j):
        if ca[i][j] > -1:
            return ca[i][j]
        d = haversine(P[i]['lat'], P[i]['lon'], Q[j]['lat'], Q[j]['lon'])
        if i == 0 and j == 0:
            ca[i][j] = d
        elif i > 0 and j == 0:
            ca[i][j] = max(c(i - 1, 0), d)
        elif i == 0 and j > 0:
            ca[i][j] = max(c(0, j - 1), d)
        elif i > 0 and j > 0:
            ca[i][j] = max(min(c(i - 1, j), c(i - 1, j - 1), c(i, j - 1)), d)
        else:
            ca[i][j] = float('inf')
        return ca[i][j]

    return c(n - 1, m - 1)

def compute_trip_stops(trip, stop_interval=5):
    """
    دالة تقوم بحساب وإنشاء نقاط التوقف للرحلة (Trip) على طول المسار
    كل stop_interval (افتراضي 5 كم). تفترض الدالة أن حقل route_coordinates
    يحتوي على JSON يمثل قائمة من النقاط، حيث يحتوي كل عنصر على مفاتيح 'lat' و 'lon'.
    """
    if not trip.route_coordinates:
        return

    try:
        route = json.loads(trip.route_coordinates)
    except Exception as e:
        # في حال وجود خطأ في تنسيق الإحداثيات
        return

    if not isinstance(route, list) or len(route) < 2:
        return

    # حذف نقاط التوقف الحالية (إن وجدت)
    trip.stops.all().delete()

    accumulated_distance = 0.0
    target_distance = stop_interval  # المسافة المستهدفة لإنشاء محطة توقف
    prev_point = route[0]
    order = 1

    # المرور عبر النقاط في المسار
    for i in range(1, len(route)):
        curr_point = route[i]
        segment_distance = haversine(prev_point['lat'], prev_point['lon'],
                                     curr_point['lat'], curr_point['lon'])
        # بينما تكون المسافة التراكمية ضمن هذا المقطع أكبر من الهدف
        while accumulated_distance + segment_distance >= target_distance:
            remaining = target_distance - accumulated_distance
            fraction = remaining / segment_distance if segment_distance != 0 else 0
            # الاستيفاء الخطي لحساب الإحداثيات
            stop_lat = prev_point['lat'] + fraction * (curr_point['lat'] - prev_point['lat'])
            stop_lon = prev_point['lon'] + fraction * (curr_point['lon'] - prev_point['lon'])
            # إنشاء محطة التوقف في قاعدة البيانات
            TripStop.objects.create(
                trip=trip,
                location=f"{stop_lat},{stop_lon}",
                order=order
            )
            order += 1
            # تحديث نقطة البداية للمقطع الحالي لتكون موقع المحطة الجديدة
            prev_point = {'lat': stop_lat, 'lon': stop_lon}
            segment_distance = haversine(prev_point['lat'], prev_point['lon'],
                                         curr_point['lat'], curr_point['lon'])
            accumulated_distance = 0.0
            target_distance = stop_interval
        accumulated_distance += segment_distance
        prev_point = curr_point

def merge_similar_trips(current_trip, distance_threshold=1.0):
    """
    دالة تفحص الرحلات المشابهة (استناداً إلى المسافة المحسوبة بخوارزمية Fréchet)
    وتقوم بدمج الحجوزات من الرحلات المتشابهة في الرحلة الحالية.
    distance_threshold: الحد الأعلى للمسافة (بالكيلومتر) الذي تعتبر به الرحلتين متشابهتين.
    """
    if not current_trip.route_coordinates:
        return

    try:
        current_route = json.loads(current_trip.route_coordinates)
    except Exception:
        return

    # البحث عن رحلات أخرى تحتوي على مسار صالح وليست الرحلة الحالية نفسها
    similar_trips = Trip.objects.exclude(id=current_trip.id).filter(route_coordinates__isnull=False)

    for other_trip in similar_trips:
        try:
            other_route = json.loads(other_trip.route_coordinates)
        except Exception:
            continue
        # حساب مسافة Fréchet بين المسارين
        distance = discrete_frechet_distance(current_route, other_route)
        if distance < distance_threshold:
            # دمج الحجوزات: إعادة ربط الحجوزات بالرحلة الحالية
            for booking in other_trip.bookings.all():
                booking.trip = current_trip
                booking.save()
            # حذف الرحلة المكررة بعد الدمج
            other_trip.delete()

def parse_location(location_str):
    """
    تحويل سلسلة إحداثيات من الشكل "lat,lon" إلى Tuple (lat, lon) كقيم float.
    """
    try:
        lat_str, lon_str = location_str.split(',')
        return float(lat_str.strip()), float(lon_str.strip())
    except Exception:
        return None, None

def is_point_near_stops(trip, point, threshold=1.0):
    """
    تفحص ما إذا كانت النقطة (tuple: (lat, lon)) تقع ضمن مسافة threshold (بالكيلومتر)
    من إحدى نقاط التوقف الخاصة بالرحلة.
    """
    stops = trip.stops.all()
    for stop in stops:
        stop_lat, stop_lon = parse_location(stop.location)
        if stop_lat is None or stop_lon is None:
            continue
        if haversine(stop_lat, stop_lon, point[0], point[1]) <= threshold:
            return True
    return False


def calculate_user_rewards(user):
    trips = user.trips.count()
    bonus_amount = (trips // 10) * 5  # كل 10 رحلات = 5 ريال
    if bonus_amount > 0:
        Bonus.objects.create(user=user, amount=bonus_amount, reason='loyalty')
        user.wallet.credit(bonus_amount)



POINTS_MAP = {
    'trip': 10,
    'delivery': 15,
    'referral': 25,
}

def reward_user_points(user: User, activity_type: str):
    """
    Award points for user activities and convert to Bonus if threshold reached.
    """
    profile = user.profile  # assuming a Profile model with points field
    profile.points += POINTS_MAP.get(activity_type, 0)
    profile.save()

    if profile.points >= 100:
        Bonus.objects.create(
            user=user,
            amount=1000,
            reason='مكافأة النقاط'
        )
        profile.points -= 100
        profile.save()
