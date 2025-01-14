from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('driver', 'Driver'),
        ('customer', 'Customer'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_groups',
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_permissions',
        blank=True
    )

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        abstract = True

class Client(BaseModel):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='client')
    photo = models.TextField(null=True, verbose_name=_("رابط الصورة"))
    device_id = models.TextField(null=True, verbose_name=_("معرف الجهاز"))
    status = models.BooleanField(default=True, verbose_name=_("الحالة"))
    status_del = models.BooleanField(default=False, verbose_name=_("الحالة (محذوف)"))
    city = models.CharField(max_length=50, null=True, verbose_name=_("المدينة"))

    def __str__(self):
        return f"العميل {self.user.username}"

    class Meta:
        db_table = 'clients'
        verbose_name = _("عميل")
        verbose_name_plural = _("العملاء")

class Wallet(BaseModel):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='wallet', verbose_name=_("المحفظة الخاصة ب"))
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name=_("رصيد المحفظة"))

    def __str__(self):
        return f"المحفظة الخاصة ب {self.user.username}"

    class Meta:
        verbose_name = _("محفظة")
        verbose_name_plural = _("المحفظة")

class ChargeCard(BaseModel):
    card_code = models.CharField(max_length=20, unique=True, verbose_name=_("رمز الشحن"))
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("قيمة الشحن"))
    is_used = models.BooleanField(default=False, verbose_name=_("هل تم استخدام الكارت؟"))
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='charge_cards')

    def __str__(self):
        return f"كود الشحن: {self.card_code} - المبلغ: {self.amount}"

class Transaction(BaseModel):
    TRANSACTION_TYPES = [
        ('charge', 'Charge'),
        ('transfer', 'Transfer'),
        ('withdraw', 'Withdraw'),
        ('payment', 'Payment'),
    ]
    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        COMPLETED = 'completed', _("مكتمل")
        CANCELLED = 'cancelled', _("ملغى")

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, verbose_name=_("نوع العملية"))
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("المبلغ"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("حالة العملية"))
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Transaction: {self.transaction_type} - Amount: {self.amount}"

class Transfer(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        COMPLETED = 'completed', _("مكتمل")
        CANCELLED = 'cancelled', _("ملغى")

    from_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transfers_from', verbose_name=_("محفظة المرسل"))
    to_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transfers_to', verbose_name=_("محفظة المستلم"))
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("حالة العملية"))

    def __str__(self):
        return f"تحويل من {self.from_wallet.user.username} الى {self.to_wallet.user.username}"

    class Meta:
        verbose_name = _("حوالة")
        verbose_name_plural = _("الحوالات")

class Vehicle(BaseModel):
    model = models.CharField(max_length=100, verbose_name=_("الموديل"))
    plate_number = models.CharField(max_length=50, unique=True, verbose_name=_("رقم اللوحة"))
    color = models.CharField(max_length=30, verbose_name=_("اللون"))
    capacity = models.IntegerField(verbose_name=_("السعة"))
    status = models.BooleanField(default=True, verbose_name=_("الحالة"))

    class Meta:
        db_table = 'vehicles'
        verbose_name = _("مركبة")
        verbose_name_plural = _("المركبات")

class Driver(BaseModel):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='driver')
    license_number = models.CharField(max_length=100, unique=True, verbose_name=_("رقم الرخصة"))
    vehicle = models.OneToOneField(Vehicle, on_delete=models.CASCADE, verbose_name=_("المركبة"))
    status = models.BooleanField(default=True, verbose_name=_("الحالة"))

    class Meta:
        verbose_name = _("سائق")
        verbose_name_plural = _("السائقون")

class Bonus(BaseModel):
    amount = models.FloatField(null=True, verbose_name=_("المبلغ"))
    status = models.BooleanField(default=True, verbose_name=_("الحالة"))
    status_del = models.BooleanField(default=False, verbose_name=_("الحالة (محذوف)"))
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name=_("معرف المستخدم"))

    class Meta:
        db_table = 'bonuses'
        verbose_name = _("مكافأة")
        verbose_name_plural = _("المكافآت")

class Trip(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        IN_PROGRESS = 'in_progress', _("قيد التنفيذ")
        COMPLETED = 'completed', _("مكتمل")

    start_location = models.CharField(max_length=100, verbose_name=_("نقطة الانطلاق"))
    end_location = models.CharField(max_length=100, verbose_name=_("وجهة الوصول"))
    departure_time = models.DateTimeField(verbose_name=_("وقت المغادرة"))
    available_seats = models.IntegerField(verbose_name=_("عدد المقاعد المتاحة"))
    price_per_seat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("سعر المقعد"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("حالة الرحلة"))
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, verbose_name=_("السائق"))

    def __str__(self):
        return f"رحلة إلى {self.end_location} بواسطة {self.driver.user.username}"

    class Meta:
        indexes = [
            models.Index(fields=['status']),
        ]

class TripStop(BaseModel):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='stops', verbose_name=_("الرحلة"))
    location = models.CharField(max_length=255, verbose_name=_("الموقع الحالي"))

    class Meta:
        db_table = 'stops'
        verbose_name = _("الرحلة وين")
        verbose_name_plural = _("تتبع الرحلات")

class Rating(BaseModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name=_("العميل"))
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, verbose_name=_("الرحلة"))
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, verbose_name=_("السائق"))
    rating = models.IntegerField(verbose_name=_("التقييم (1 إلى 5)"))
    comment = models.TextField(null=True, blank=True, verbose_name=_("التعليق"))

    class Meta:
        verbose_name = _("تقييم")
        verbose_name_plural = _("التقييمات")

class Support(BaseModel):
    STATUS_CHOICES = [
        ('open', _("مفتوح")),
        ('in_progress', _("قيد التنفيذ")),
        ('resolved', _("محلولة")),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name=_("العميل"))
    subject = models.CharField(max_length=255, verbose_name=_("الموضوع"))
    message = models.TextField(verbose_name=_("الرسالة"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', verbose_name=_("الحالة"))

    class Meta:
        verbose_name = _("تذكرة دعم")
        verbose_name_plural = _("تذاكر الدعم")

class SubscriptionPlan(BaseModel):
    name = models.CharField(max_length=100, verbose_name=_("اسم الخطة"))
    description = models.TextField(null=True, blank=True, verbose_name=_("الوصف"))
    price = models.FloatField(verbose_name=_("السعر"))
    duration = models.IntegerField(verbose_name=_("المدة (بالأيام)"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشطة"))

    class Meta:
        db_table = 'subscription_plans'
        verbose_name = _("خطة اشتراك")
        verbose_name_plural = _("خطط الاشتراك")

class Subscription(BaseModel):
    user = models.ForeignKey(Driver, on_delete=models.CASCADE, verbose_name=_("العميل"))
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, verbose_name=_("خطة الاشتراك"))
    start_date = models.DateField(verbose_name=_("تاريخ البدء"))
    end_date = models.DateField(verbose_name=_("تاريخ الانتهاء"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشطة"))

    class Meta:
        verbose_name = _("اشتراك")
        verbose_name_plural = _("الاشتراكات")

class Booking(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        COMPLETED = 'completed', _("مكتمل")
        CANCELLED = 'cancelled', _("ملغى")

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, verbose_name=_("الرحلة"))
    customer = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name=_("العميل"))
    seat_number = models.IntegerField(verbose_name=_("عدد المقاعد"))
    booking_date = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الحجز"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("الحالة"))

    def __str__(self):
        return f"حجز في الرحلة إلى {self.trip.end_location}"

class CasheBooking(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        COMPLETED = 'completed', _("مكتمل")
        CANCELLED = 'cancelled', _("ملغى")

    where_from = models.CharField(max_length=60, verbose_name=_("من وين"))
    to_where = models.CharField(max_length=60, verbose_name=_("على وين"))
    number_set = models.IntegerField(verbose_name=_("انت ومن: العدد"))
    at_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("الحالة"))

    def __str__(self):
        return f"رحلة من {self.where_from} الى {self.to_where} العدد {self.number_set}"

class ItemDelivery(BaseModel):
    STATUS_CHOICES = [
        ('pending', _("قيد الانتظار")),
        ('in_transit', _("قيد النقل")),
        ('delivered', _("تم التسليم")),
        ('cancelled', _("ملغاة")),
    ]

    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_items', verbose_name=_("المرسل"))
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_items', verbose_name=_("المستلم"))
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, verbose_name=_("الرحلة"))
    pickup_location = models.CharField(max_length=100, verbose_name=_("موقع الاستلام"), blank=True, null=True)
    dropoff_location = models.CharField(max_length=100, verbose_name=_("موقع التسليم"), blank=True, null=True)
    item_description = models.TextField(verbose_name=_("وصف العنصر"))
    weight = models.FloatField(verbose_name=_("الوزن بالكيلوجرام"))
    insurance = models.BooleanField(default=False, verbose_name=_("قابل للكسر/ضمان"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name=_("الحالة"))

    class Meta:
        verbose_name = _("تسليم عنصر")
        verbose_name_plural = _("تسليم العناصر")

class CasheItemDelivery(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        COMPLETED = 'completed', _("مكتمل")
        CANCELLED = 'cancelled', _("ملغى")

    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='cashe_sent_items', verbose_name=_("المرسل"), blank=True, null=True)
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='cashe_received_items', verbose_name=_("المستلم"))
    pickup_location = models.CharField(max_length=100, verbose_name=_("موقع الاستلام"), blank=True, null=True)
    dropoff_location = models.CharField(max_length=100, verbose_name=_("موقع التسليم"), blank=True, null=True)
    item_description = models.TextField(verbose_name=_("وصف العنصر"))
    weight = models.FloatField(verbose_name=_("الوزن بالكيلوجرام"))
    at_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("الحالة"))

    def __str__(self):
        return f"رسالة من {self.sender} الى {self.dropoff_location} الحجم {self.weight}"
    
class UserActivityLog(BaseModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name=_("المستخدم"))
    activity_type = models.CharField(max_length=50, verbose_name=_("نوع النشاط"))
    activity_data = models.JSONField(verbose_name=_("بيانات النشاط"))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("الطابع الزمني"))

    def __str__(self):
        return f"نشاط {self.user.username} - {self.activity_type}"

    class Meta:
        verbose_name = _("سجل النشاط")
        verbose_name_plural = _("سجلات النشاط")

class Recommendation(BaseModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name=_("المستخدم"))
    recommended_items = models.JSONField(verbose_name=_("العناصر الموصى بها"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الإنشاء"))

    def __str__(self):
        return f"توصيات {self.user.username}"

    class Meta:
        verbose_name = _("توصية")
        verbose_name_plural = _("توصيات")