from rest_framework import permissions


class IsClientOwner(permissions.BasePermission):
    """
    صلاحية تتحقق من ملكية سجل العميل
    - يسمح بإجراءات (GET, PUT, PATCH, DELETE) فقط لمالك السجل
    - ينطبق على عمليات تفصيلية (retrieve/update/destroy)
    - مناسب لنموذج Client
    """
    
    def has_object_permission(self, request, view, obj):
        # التحقق من تطابق مستخدم العميل مع المستخدم الحالي
        return obj.user == request.user

class IsWalletOwner(permissions.BasePermission):
    """
    صلاحية تتحقق من ملكية المحفظة
    - يسمح بإجراءات مالية فقط لمالك المحفظة
    - ينطبق على نماذج Wallet والعمليات المرتبطة
    - يمنع التعديلات على محافظ أخرى
    """
    
    def has_object_permission(self, request, view, obj):
        # التحقق من تطابق مستخدم المحفظة مع المستخدم الحالي
        return obj.user == request.user

class ClientAccessPolicy(permissions.BasePermission):
    """
    سياسة وصول متكاملة لجدول العملاء تشمل:
    1. إنشاء سجلات جديدة للمستخدمين المصادق عليهم
    2. الوصول الكامل لمالكي السجلات
    3. وصول قراءة فقط للموظفين
    4. منع الوصول غير المصرح به
    """
    
    def has_permission(self, request, view):
        # التحقق من المصادقة أولاً
        if not request.user.is_authenticated:
            return False
            
        # صلاحية الإنشاء لجميع المستخدمين المصادق عليهم
        if view.action == 'create':
            return True
            
        # صلاحية العرض القائمة على الصلاحيات
        return True  # يتم التحكم بالتفاصيل في has_object_permission
    
    def has_object_permission(self, request, view, obj):
        # الصلاحيات المسموحة:
        # - مالك السجل: كافة الصلاحيات
        # - الموظفون: صلاحيات قراءة فقط
        if obj.user == request.user:
            return True
            
        if request.user.is_staff:
            return request.method in permissions.SAFE_METHODS
            
        return False