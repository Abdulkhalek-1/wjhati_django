from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db.models import Index

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('driver', _('سائق')),
        ('customer', _('عميل')),
        ('admin', _('مدير النظام')),
    )
    
    # تحسينات على نموذج المستخدم
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, verbose_name=_("نوع المستخدم"))
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message=_("رقم الهاتف يجب أن يكون بالتنسيق: '+999999999'. حتى 15 رقمًا.")
    )
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=17,
        unique=True,
        verbose_name=_("رقم الهاتف")
    )
    profile_picture = models.URLField(null=True, blank=True, verbose_name=_("صورة الملف الشخصي"))
    is_verified = models.BooleanField(default=False, verbose_name=_("حساب موثوق"))
    last_activity = models.DateTimeField(auto_now=True, verbose_name=_("آخر نشاط"))
    
    # تعديلات على نظام الصلاحيات
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_groups',
        blank=True,
        verbose_name=_("المجموعات"),
        help_text=_("المجموعات التي ينتمي إليها المستخدم.")
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_permissions',
        blank=True,
        verbose_name=_("صلاحيات المستخدم"),
        help_text=_("الصلاحيات المحددة لهذا المستخدم.")
    )

    class Meta:
        verbose_name = _("مستخدم")
        verbose_name_plural = _("المستخدمون")
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['user_type']),
        ]

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"


class BaseModel(models.Model):
    """
    النموذج الأساسي الذي يحتوي على حقول التوقيت الزمني
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الإنشاء"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("تاريخ التحديث"))

    class Meta:
        abstract = True
        ordering = ['-created_at']


class Client(BaseModel):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='client',
        verbose_name=_("المستخدم")
    )
    device_id = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("معرف الجهاز"))
    status = models.BooleanField(default=True, verbose_name=_("الحالة"))
    status_del = models.BooleanField(default=False, verbose_name=_("محذوف"))
    city = models.CharField(max_length=50, verbose_name=_("المدينة"))
    preferred_language = models.CharField(
        max_length=10,
        default='ar',
        choices=[('ar', 'العربية'), ('en', 'الإنجليزية')],
        verbose_name=_("اللغة المفضلة")
    )

    class Meta:
        db_table = 'clients'
        verbose_name = _("عميل")
        verbose_name_plural = _("العملاء")
        indexes = [
            models.Index(fields=['city']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.city}"


class Wallet(BaseModel):
    CURRENCY_CHOICES = (
        ('YE', 'ريال يمني'),
        ('SAR', 'ريال سعودي'),
        ('USD', 'دولار أمريكي'),
    )
    
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='wallet',
        verbose_name=_("المستخدم")
    )
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name=_("الرصيد")
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='SAR',
        verbose_name=_("العملة")
    )
    is_locked = models.BooleanField(
        default=False,
        verbose_name=_("محظورة"),
        help_text=_("يمنع إجراء المعاملات إذا كانت المحفظة محظورة")
    )

    class Meta:
        verbose_name = _("محفظة")
        verbose_name_plural = _("المحافظ")

    def __str__(self):
        return f"{self.user} - {self.balance} {self.currency}"


class Transaction(BaseModel):
    TRANSACTION_TYPES = [
        ('charge', _("شحن")),
        ('transfer', _("تحويل")),
        ('withdraw', _("سحب")),
        ('payment', _("دفع")),
        ('refund', _("استرداد")),
    ]

    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        COMPLETED = 'completed', _("مكتمل")
        CANCELLED = 'cancelled', _("ملغى")
        FAILED = 'failed', _("فشل")

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name=_("المحفظة")
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPES,
        verbose_name=_("نوع العملية")
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_("المبلغ")
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("الحالة")
    )
    reference_number = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        verbose_name=_("رقم المرجع")
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("الوصف")
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("بيانات إضافية")
    )

    class Meta:
        verbose_name = _("عملية")
        verbose_name_plural = _("العمليات")
        indexes = [
            models.Index(fields=['transaction_type']),
            models.Index(fields=['status']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount} {self.wallet.currency}"


class Vehicle(BaseModel):
    VEHICLE_TYPES = (
        ('sedan', _("سيدان")),
        ('suv', _("SUV")),
        ('van', _("فان")),
        ('truck', _("شاحنة")),
    )
    
    model = models.CharField(max_length=100, verbose_name=_("الموديل"))
    plate_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("رقم اللوحة")
    )
    color = models.CharField(max_length=30, verbose_name=_("اللون"))
    capacity = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_("السعة")
    )
    vehicle_type = models.CharField(
        max_length=20,
        choices=VEHICLE_TYPES,
        default='sedan',
        verbose_name=_("نوع المركبة")
    )
    manufacture_year = models.IntegerField(
        verbose_name=_("سنة الصنع"),
        null=True,
        blank=True
    )
    inspection_expiry = models.DateField(
        verbose_name=_("انتهاء الفحص الفني"),
        null=True,
        blank=True
    )
    status = models.BooleanField(default=True, verbose_name=_("الحالة"))

    class Meta:
        db_table = 'vehicles'
        verbose_name = _("مركبة")
        verbose_name_plural = _("المركبات")
        indexes = [
            models.Index(fields=['vehicle_type']),
            models.Index(fields=['plate_number']),
        ]

    def __str__(self):
        return f"{self.get_vehicle_type_display()} - {self.plate_number}"


class Driver(BaseModel):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='driver',
        verbose_name=_("المستخدم")
    )
    license_number = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("رقم الرخصة")
    )
    vehicles = models.ManyToManyField(
        Vehicle,
        related_name='drivers',
        verbose_name=_("المركبات")
    )
    rating = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        verbose_name=_("التقييم")
    )
    total_trips = models.IntegerField(default=0, verbose_name=_("إجمالي الرحلات"))
    is_available = models.BooleanField(default=True, verbose_name=_("متاح للرحلات"))

    class Meta:
        verbose_name = _("سائق")
        verbose_name_plural = _("السائقون")
        indexes = [
            models.Index(fields=['rating']),
            models.Index(fields=['is_available']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.license_number}"


class Trip(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        IN_PROGRESS = 'in_progress', _("قيد التنفيذ")
        COMPLETED = 'completed', _("مكتمل")
        CANCELLED = 'cancelled', _("ملغاة")

    start_location = models.CharField(max_length=100, verbose_name=_("نقطة الانطلاق"))
    end_location = models.CharField(max_length=100, verbose_name=_("وجهة الوصول"))
    departure_time = models.DateTimeField(verbose_name=_("وقت المغادرة"))
    estimated_duration = models.DurationField(
        null=True,
        blank=True,
        verbose_name=_("المدة المتوقعة")
    )
    available_seats = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_("المقاعد المتاحة")
    )
    price_per_seat = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("سعر المقعد")
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("الحالة")
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name='trips',
        verbose_name=_("السائق")
    )
    route_coordinates = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("إحداثيات المسار"),
        help_text=_("تنسيق JSON لإحداثيات المسار (خط الطول والعرض)")
    )

    class Meta:
        verbose_name = _("رحلة")
        verbose_name_plural = _("الرحلات")
        indexes = [
            models.Index(fields=['departure_time']),
            models.Index(fields=['status']),
        ]
        ordering = ['-departure_time']

    def __str__(self):
        return f"{self.start_location} → {self.end_location} ({self.departure_time})"


class Booking(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        CONFIRMED = 'confirmed', _("مؤكد")
        COMPLETED = 'completed', _("مكتمل")
        CANCELLED = 'cancelled', _("ملغى")

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name=_("الرحلة")
    )
    customer = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name=_("العميل")
    )
    seats = models.JSONField(
        default=list,
        verbose_name=_("المقاعد المحجوزة"),
        help_text=_("قائمة بأرقام/أسماء المقاعد المحددة")
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("المبلغ الإجمالي")
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("الحالة")
    )

    class Meta:
        verbose_name = _("حجز")
        verbose_name_plural = _("الحجوزات")
        unique_together = ('trip', 'customer')
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.customer.user} - {self.trip} ({len(self.seats)} مقاعد)"


class Rating(BaseModel):
    RATING_CHOICES = [
        (1, '★☆☆☆☆'),
        (2, '★★☆☆☆'),
        (3, '★★★☆☆'),
        (4, '★★★★☆'),
        (5, '★★★★★'),
    ]

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name=_("الرحلة")
    )
    rated_by = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        verbose_name=_("المقيّم")
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name=_("السائق")
    )
    rating = models.IntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_("التقييم")
    )
    comment = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("تعليق")
    )

    class Meta:
        verbose_name = _("تقييم")
        verbose_name_plural = _("التقييمات")
        unique_together = ('trip', 'rated_by')
        indexes = [
            models.Index(fields=['rating']),
        ]

    def __str__(self):
        return f"{self.rated_by.user} → {self.driver.user} ({self.rating}/5)"


class Chat(BaseModel):
    participants = models.ManyToManyField(
        CustomUser,
        related_name='chats',
        verbose_name=_("المشاركون")
    )
    is_group = models.BooleanField(default=False, verbose_name=_("محادثة جماعية"))
    title = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_("عنوان المحادثة")
    )

    class Meta:
        verbose_name = _("محادثة")
        verbose_name_plural = _("المحادثات")
        ordering = ['-updated_at']

    def __str__(self):
        if self.is_group:
            return self.title or f"Group Chat #{self.id}"
        participants = self.participants.all()
        return f"Chat بين {participants[0]} و {participants[1]}"


class Message(BaseModel):
    chat = models.ForeignKey(
        Chat,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_("المحادثة")
    )
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name=_("المرسل")
    )
    content = models.TextField(verbose_name=_("المحتوى"))
    attachment = models.FileField(
        upload_to='chat_attachments/',
        null=True,
        blank=True,
        verbose_name=_("مرفق")
    )
    is_read = models.BooleanField(default=False, verbose_name=_("تم القراءة"))

    class Meta:
        verbose_name = _("رسالة")
        verbose_name_plural = _("الرسائل")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_read']),
        ]

    def __str__(self):
        return f"{self.sender}: {self.content[:50]}"


class SupportTicket(BaseModel):
    STATUS_CHOICES = [
        ('open', _("مفتوح")),
        ('in_progress', _("قيد المتابعة")),
        ('resolved', _("تم الحل")),
        ('closed', _("مغلق")),
    ]

    PRIORITY_CHOICES = [
        ('low', _("منخفض")),
        ('medium', _("متوسط")),
        ('high', _("عالي")),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='tickets',
        verbose_name=_("المستخدم")
    )
    subject = models.CharField(max_length=255, verbose_name=_("الموضوع"))
    message = models.TextField(verbose_name=_("الرسالة"))
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open',
        verbose_name=_("الحالة")
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name=_("الأولوية")
    )
    assigned_to = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        verbose_name=_("مُعيّن إلى")
    )

    class Meta:
        verbose_name = _("تذكرة دعم")
        verbose_name_plural = _("تذاكر الدعم")
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user}: {self.subject} ({self.get_status_display()})"


class Notification(BaseModel):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_("المستخدم")
    )
    title = models.CharField(max_length=200, verbose_name=_("العنوان"))
    message = models.TextField(verbose_name=_("المحتوى"))
    is_read = models.BooleanField(default=False, verbose_name=_("تم القراءة"))
    notification_type = models.CharField(
        max_length=50,
        choices=[
            ('booking', _("حجز")),
            ('trip', _("رحلة")),
            ('payment', _("دفع")),
            ('system', _("نظام")),
        ],
        default='system',
        verbose_name=_("نوع الإشعار")
    )
    related_object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("معرّف الكائن المرتبط")
    )

    class Meta:
        verbose_name = _("إشعار")
        verbose_name_plural = _("الإشعارات")
        indexes = [
            models.Index(fields=['is_read']),
            models.Index(fields=['notification_type']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user}"
    
# ... (الكود السابق يبقى كما هو)

class Transfer(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        COMPLETED = 'completed', _("مكتمل")
        CANCELLED = 'cancelled', _("ملغى")
        FAILED = 'failed', _("فشل")

    from_wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transfers_sent',
        verbose_name=_("محفظة المرسل")
    )
    to_wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transfers_received',
        verbose_name=_("محفظة المستقبل")
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_("المبلغ")
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("الحالة")
    )
    transfer_code = models.CharField(
        max_length=10,
        unique=True,
        verbose_name=_("رمز التحويل")
    )

    class Meta:
        verbose_name = _("تحويل مالي")
        verbose_name_plural = _("التحويلات المالية")
        indexes = [
            models.Index(fields=['transfer_code']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"تحويل {self.amount} من {self.from_wallet.user} إلى {self.to_wallet.user}"


class SubscriptionPlan(BaseModel):
    name = models.CharField(max_length=100, verbose_name=_("اسم الخطة"))
    description = models.TextField(verbose_name=_("الوصف"))
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("السعر الشهري")
    )
    duration_days = models.IntegerField(
        verbose_name=_("المدة بالأيام"),
        help_text=_("عدد أيام سريان الاشتراك")
    )
    max_trips = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("الحد الأقصى للرحلات"),
        help_text=_("إذا كان غير محدد، عدد الرحلات غير محدود")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("نشطة"))

    class Meta:
        verbose_name = _("خطة اشتراك")
        verbose_name_plural = _("خطط الاشتراك")
        ordering = ['price']

    def __str__(self):
        return f"{self.name} ({self.price} SAR)"


class Subscription(BaseModel):
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name=_("السائق")
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE,
        verbose_name=_("الخطة")
    )
    start_date = models.DateField(verbose_name=_("تاريخ البدء"))
    end_date = models.DateField(verbose_name=_("تاريخ الانتهاء"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشط"))
    remaining_trips = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("الرحلات المتبقية")
    )

    class Meta:
        verbose_name = _("اشتراك")
        verbose_name_plural = _("الاشتراكات")
        indexes = [
            models.Index(fields=['end_date']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.driver.user} - {self.plan}"


class Bonus(BaseModel):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='bonuses',
        verbose_name=_("المستخدم")
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("المبلغ")
    )
    reason = models.CharField(
        max_length=255,
        choices=[
            ('referral', _("مكافأة إحالة")),
            ('promotion', _("عرض ترويجي")),
            ('other', _("أخرى")),
        ],
        default='other',
        verbose_name=_("السبب")
    )
    expiration_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("تاريخ الانتهاء")
    )

    class Meta:
        verbose_name = _("مكافأة")
        verbose_name_plural = _("المكافآت")
        indexes = [
            models.Index(fields=['expiration_date']),
        ]

    def __str__(self):
        return f"{self.user} - {self.amount} SAR ({self.get_reason_display()})"


class TripStop(BaseModel):
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='stops',
        verbose_name=_("الرحلة")
    )
    location = models.CharField(max_length=255, verbose_name=_("الموقع"))
    order = models.PositiveIntegerField(verbose_name=_("ترتيب المحطة"))
    arrival_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("وقت الوصول المتوقع")
    )

    class Meta:
        db_table = 'trip_stops'
        verbose_name = _("محطة توقف")
        verbose_name_plural = _("محطات التوقف")
        ordering = ['order']
        unique_together = ('trip', 'order')

    def __str__(self):
        return f"{self.trip} - {self.location} ({self.order})"


class ItemDelivery(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        IN_TRANSIT = 'in_transit', _("قيد النقل")
        DELIVERED = 'delivered', _("تم التسليم")
        CANCELLED = 'cancelled', _("ملغاة")

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='deliveries',
        verbose_name=_("الرحلة")
    )
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='sent_deliveries',
        verbose_name=_("المرسل")
    )
    receiver_name = models.CharField(max_length=255, verbose_name=_("اسم المستلم"))
    receiver_phone = models.CharField(max_length=20, verbose_name=_("هاتف المستلم"))
    item_description = models.TextField(verbose_name=_("وصف الشحنة"))
    weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("الوزن (كجم)")
    )
    insurance_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("مبلغ التأمين")
    )
    delivery_code = models.CharField(
        max_length=10,
        unique=True,
        verbose_name=_("كود الشحنة")
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("الحالة")
    )

    class Meta:
        verbose_name = _("شحنة")
        verbose_name_plural = _("الشحنات")
        indexes = [
            models.Index(fields=['delivery_code']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"شحنة #{self.delivery_code} - {self.get_status_display()}"


class CasheBooking(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        ACCEPTED = 'accepted', _("مقبول"),
        COMPLETED = 'completed', _("مكتمل"),
        CANCELLED = 'cancelled', _("ملغى")

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='cashe_bookings',
        verbose_name=_("المستخدم")
    )
    from_location = models.CharField(max_length=255, verbose_name=_("من"))
    to_location = models.CharField(max_length=255, verbose_name=_("إلى"))
    departure_time = models.DateTimeField(verbose_name=_("وقت المغادرة"))
    passengers = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_("عدد الركاب")
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("الحالة")
    )
    notes = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("ملاحظات إضافية")
    )

    class Meta:
        verbose_name = _("حجز مسبق")
        verbose_name_plural = _("الحجوزات المسبقة")
        indexes = [
            models.Index(fields=['departure_time']),
        ]

    def __str__(self):
        return f"حجز مسبق #{self.id} - {self.user}"


class CasheItemDelivery(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        ACCEPTED = 'accepted', _("مقبول"),
        IN_PROGRESS = 'in_progress', _("قيد التوصيل"),
        DELIVERED = 'delivered', _("تم التسليم"),
        CANCELLED = 'cancelled', _("ملغى")

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='cashe_deliveries',
        verbose_name=_("المستخدم")
    )
    from_location = models.CharField(max_length=255, verbose_name=_("من"))
    to_location = models.CharField(max_length=255, verbose_name=_("إلى"))
    item_description = models.TextField(verbose_name=_("وصف الشحنة"))
    weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("الوزن (كجم)")
    )
    urgent = models.BooleanField(default=False, verbose_name=_("عاجل"))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("الحالة")
    )

    class Meta:
        verbose_name = _("طلب توصيل مسبق")
        verbose_name_plural = _("طلبات التوصيل المسبقة")
        indexes = [
            models.Index(fields=['urgent']),
        ]

    def __str__(self):
        return f"طلب توصيل #{self.id} - {self.user}"