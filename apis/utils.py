from django.db.models import Q
from datetime import timedelta

def get_available_driver():
    """
    دالة افتراضية لاختيار سائق متاح.
    يجب استبدالها بالمنطق الخاص بتطبيقك.
    """
    from .models import Driver  # تأكد من مسار نموذج السائق
    # البحث عن أول سائق متاح
    available_driver = Driver.objects.filter(is_available=True).first()
    return available_driver

def calculate_total_price(cashe_booking):
    """
    دالة افتراضية لحساب السعر الإجمالي بناءً على بيانات الحجز المسبق.
    يمكنك تعديل هذا المنطق بناءً على احتياجات التطبيق.
    """
    # كمثال بسيط: نفترض أن السعر لكل راكب هو 10.00
    price_per_passenger = 10.00
    return cashe_booking.passengers * price_per_passenger

def merge_bookings_into_trip():
    """
    تبحث هذه الدالة عن الحجوزات المسبقة (CasheBooking) ذات الحالة pending
    وتجمعها حسب (from_location, to_location, departure_time) ثم تنشئ رحلة لكل مجموعة.
    كما تقوم بتحويل كل حجز مسبق إلى حجز نهائي (Booking) وترتبط الرحلة به.
    """
    from .models import CasheBooking, Trip, Booking

    # جلب الحجوزات المسبقة ذات الحالة PENDING
    pending_bookings = CasheBooking.objects.filter(status=CasheBooking.Status.PENDING)

    # تجميع الحجوزات بناءً على (from_location, to_location, departure_time)
    bookings_group = {}
    for booking in pending_bookings:
        key = (booking.from_location, booking.to_location, booking.departure_time)
        bookings_group.setdefault(key, []).append(booking)

    # معالجة كل مجموعة من الحجوزات
    for key, cashe_bookings in bookings_group.items():
        if cashe_bookings:
            driver = get_available_driver()
            if driver:
                # إنشاء رحلة جديدة باستخدام البيانات المشتركة للمجموعة
                trip = Trip.objects.create(
                    driver=driver,
                    from_location=key[0],
                    to_location=key[1],
                    departure_time=key[2]
                )
                # تحويل كل حجز مسبق إلى حجز نهائي وربطه بالرحلة المنشأة
                for cashe_booking in cashe_bookings:
                    # تحديد المقاعد المحجوزة؛ هنا مثال افتراضي: إنشاء قائمة بأرقام المقاعد اعتمادًا على عدد الركاب
                    seats = [f"seat_{i+1}" for i in range(cashe_booking.passengers)]
                    total_price = calculate_total_price(cashe_booking)
                    Booking.objects.create(
                        trip=trip,
                        customer=cashe_booking.user,  # تأكد أن حقل customer في Booking يقبل cashe_booking.user
                        seats=seats,
                        total_price=total_price,
                        status=Booking.Status.PENDING  # أو الحالة المناسبة بحسب منطق التطبيق
                    )
                    # تحديث حالة الحجز المسبق
                    cashe_booking.status = CasheBooking.Status.ACCEPTED
                    cashe_booking.save()
            else:
                print("لا يوجد سائق متاح للرحلة من {} إلى {} في {}".format(
                    key[0], key[1], key[2]
                ))
