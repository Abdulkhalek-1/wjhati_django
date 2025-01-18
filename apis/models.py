from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('driver', _('سائق')),
        ('customer', _('عميل')),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, verbose_name=_("نوع المستخدم"))
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name=_("رقم الهاتف"))
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_groups',
        blank=True,
        verbose_name=_("المجموعات")
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_permissions',
        blank=True,
        verbose_name=_("صلاحيات المستخدم")
    )

    class Meta:
        verbose_name = _("مستخدم مخصص")
        verbose_name_plural = _("المستخدمون المخصصون")

    def __str__(self):
        return self.username


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الإنشاء"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("تاريخ التحديث"))

    class Meta:
        abstract = True


class Client(BaseModel):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='client', verbose_name=_("المستخدم"))
    photo = models.URLField(null=True, blank=True, verbose_name=_("رابط الصورة"))
    device_id = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("معرف الجهاز"))
    status = models.BooleanField(default=True, verbose_name=_("الحالة"))
    status_del = models.BooleanField(default=False, verbose_name=_("الحالة (محذوف)"))
    city = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("المدينة"))

    def __str__(self):
        return f"{self.user.username} - {self.city}"

    class Meta:
        db_table = 'clients'
        verbose_name = _("عميل")
        verbose_name_plural = _("العملاء")


class Wallet(BaseModel):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='wallet', verbose_name=_("المستخدم"))
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name=_("رصيد المحفظة"))

    def __str__(self):
        return f"{self.user.username} - {self.balance}"

    class Meta:
        verbose_name = _("محفظة")
        verbose_name_plural = _("المحافظ")


class Transaction(BaseModel):
    TRANSACTION_TYPES = [
        ('charge', _("شحن")),
        ('transfer', _("تحويل")),
        ('withdraw', _("سحب")),
        ('payment', _("دفع")),
    ]

    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        COMPLETED = 'completed', _("مكتمل")
        CANCELLED = 'cancelled', _("ملغى")

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions', verbose_name=_("المحفظة"))
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, verbose_name=_("نوع العملية"))
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("المبلغ"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("حالة العملية"))
    description = models.TextField(blank=True, null=True, verbose_name=_("الوصف"))

    def __str__(self):
        return f"{self.transaction_type} - {self.amount}"

    class Meta:
        verbose_name = _("عملية")
        verbose_name_plural = _("العمليات")


class Transfer(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        COMPLETED = 'completed', _("مكتمل")
        CANCELLED = 'cancelled', _("ملغى")

    from_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transfers_from', verbose_name=_("محفظة المرسل"))
    to_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transfers_to', verbose_name=_("محفظة المستلم"))
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("المبلغ"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("حالة العملية"))

    def __str__(self):
        return f"تحويل من {self.from_wallet.user.username} إلى {self.to_wallet.user.username}"

    class Meta:
        verbose_name = _("حوالة")
        verbose_name_plural = _("الحوالات")


class Vehicle(BaseModel):
    model = models.CharField(max_length=100, verbose_name=_("الموديل"))
    plate_number = models.CharField(max_length=50, unique=True, verbose_name=_("رقم اللوحة"))
    color = models.CharField(max_length=30, verbose_name=_("اللون"))
    capacity = models.IntegerField(verbose_name=_("السعة"))
    status = models.BooleanField(default=True, verbose_name=_("الحالة"))

    def __str__(self):
        return f"{self.model} - {self.plate_number}"

    class Meta:
        db_table = 'vehicles'
        verbose_name = _("مركبة")
        verbose_name_plural = _("المركبات")


class Driver(BaseModel):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='driver', verbose_name=_("المستخدم"))
    license_number = models.CharField(max_length=100, unique=True, verbose_name=_("رقم الرخصة"))
    vehicle = models.OneToOneField(Vehicle, on_delete=models.CASCADE, verbose_name=_("المركبة"))
    status = models.BooleanField(default=True, verbose_name=_("الحالة"))

    def __str__(self):
        return f"{self.user.username} - {self.license_number}"

    class Meta:
        verbose_name = _("سائق")
        verbose_name_plural = _("السائقون")


class Bonus(BaseModel):
    amount = models.FloatField(verbose_name=_("المبلغ"))
    status = models.BooleanField(default=True, verbose_name=_("الحالة"))
    status_del = models.BooleanField(default=False, verbose_name=_("الحالة (محذوف)"))
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name=_("المستخدم"))

    def __str__(self):
        return f"{self.user.username} - {self.amount}"

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
        return f"رحلة من {self.start_location} إلى {self.end_location}"

    class Meta:
        indexes = [
            models.Index(fields=['status']),
        ]
        verbose_name = _("رحلة")
        verbose_name_plural = _("الرحلات")


class TripStop(BaseModel):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='stops', verbose_name=_("الرحلة"))
    location = models.CharField(max_length=255, verbose_name=_("الموقع"))

    def __str__(self):
        return f"{self.trip} - {self.location}"

    class Meta:
        db_table = 'trip_stops'
        verbose_name = _("توقف الرحلة")
        verbose_name_plural = _("توقفات الرحلات")


class Rating(BaseModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name=_("المستخدم"))
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, verbose_name=_("الرحلة"))
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, verbose_name=_("السائق"))
    rating = models.IntegerField(verbose_name=_("التقييم (1 إلى 5)"))
    comment = models.TextField(null=True, blank=True, verbose_name=_("التعليق"))

    def __str__(self):
        return f"{self.user.username} - {self.rating}"

    class Meta:
        verbose_name = _("تقييم")
        verbose_name_plural = _("التقييمات")


class Support(BaseModel):
    STATUS_CHOICES = [
        ('open', _("مفتوح")),
        ('in_progress', _("قيد التنفيذ")),
        ('resolved', _("محلول")),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name=_("المستخدم"))
    subject = models.CharField(max_length=255, verbose_name=_("الموضوع"))
    message = models.TextField(verbose_name=_("الرسالة"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', verbose_name=_("الحالة"))

    def __str__(self):
        return f"{self.user.username} - {self.subject}"

    class Meta:
        verbose_name = _("تذكرة دعم")
        verbose_name_plural = _("تذاكر الدعم")


class SubscriptionPlan(BaseModel):
    name = models.CharField(max_length=100, verbose_name=_("اسم الخطة"))
    description = models.TextField(null=True, blank=True, verbose_name=_("الوصف"))
    price = models.FloatField(verbose_name=_("السعر"))
    duration = models.IntegerField(verbose_name=_("المدة (بالأيام)"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشط"))

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'subscription_plans'
        verbose_name = _("خطة اشتراك")
        verbose_name_plural = _("خطط الاشتراك")


class Subscription(BaseModel):
    user = models.ForeignKey(Driver, on_delete=models.CASCADE, verbose_name=_("المستخدم"))
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, verbose_name=_("الخطة"))
    start_date = models.DateField(verbose_name=_("تاريخ البدء"))
    end_date = models.DateField(verbose_name=_("تاريخ الانتهاء"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشط"))

    def __str__(self):
        return f"{self.user.user.username} - {self.plan.name}"

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
    number_of_seats = models.IntegerField(verbose_name=_("عدد المقاعد"))
    booking_date = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الحجز"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("حالة الحجز"))

    def __str__(self):
        return f"{self.customer.user.username} - {self.trip}"

    class Meta:
        verbose_name = _("حجز")
        verbose_name_plural = _("الحجوزات")


class CasheBooking(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        COMPLETED = 'completed', _("مكتمل")
        CANCELLED = 'cancelled', _("ملغى")

    where_from = models.CharField(max_length=60, verbose_name=_("من أين"))
    to_where = models.CharField(max_length=60, verbose_name=_("إلى أين"))
    number_of_people = models.IntegerField(verbose_name=_("عدد الأشخاص"))
    at_time = models.DateTimeField(auto_now_add=True, verbose_name=_("الوقت"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("الحالة"))

    def __str__(self):
        return f"رحلة من {self.where_from} إلى {self.to_where}"

    class Meta:
        verbose_name = _("طلب رحلة ")
        verbose_name_plural = _(" طلبات الرحلات")


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
    weight = models.FloatField(verbose_name=_("الوزن (كجم)"))
    insurance = models.BooleanField(default=False, verbose_name=_("التأمين"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name=_("الحالة"))

    def __str__(self):
        return f"تسليم من {self.sender.username} إلى {self.receiver.username}"

    class Meta:
        verbose_name = _("ارسال الاغرض")
        verbose_name_plural = _("الاغراض المرسة معا الرحلات")


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
    weight = models.FloatField(verbose_name=_("الوزن (كجم)"))
    at_time = models.DateTimeField(auto_now_add=True, verbose_name=_("الوقت"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("الحالة"))

    def __str__(self):
        return f"تسليم نقدي من {self.sender.username} إلى {self.receiver.username}"

    class Meta:
        verbose_name = _("طلب ارسال ")
        verbose_name_plural = _("طلبات الارسال ")

class Chat(BaseModel):
    participants = models.ManyToManyField(CustomUser, related_name='chats', verbose_name=_("المشاركون"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الإنشاء"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("تاريخ التحديث"))

    def __str__(self):
        return f"محادثة بين {', '.join([user.username for user in self.participants.all()])}"

    class Meta:
        verbose_name = _("محادثة")
        verbose_name_plural = _("المحادثات")


class Message(BaseModel):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages', verbose_name=_("المحادثة"))
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_messages', verbose_name=_("المرسل"))
    content = models.TextField(verbose_name=_("المحتوى"))
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name=_("وقت الإرسال"))

    def __str__(self):
        return f"{self.sender.username} - {self.content[:50]}"

    class Meta:
        verbose_name = _("رسالة")
        verbose_name_plural = _("الرسائل")