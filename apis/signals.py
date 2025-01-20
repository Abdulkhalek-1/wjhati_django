from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Transaction, Transfer
from django.core.exceptions import ObjectDoesNotExist
from .models import Bonus, Wallet

@receiver(post_save, sender=Bonus)
def update_wallet_on_bonus(sender, instance, created, **kwargs):
    """
    إشارة تلقائية لتحديث رصيد المحفظة عند إضافة مكافأة
    المهام الرئيسية:
    1. التحقق من أن المكافأة جديدة (created=True)
    2. البحث عن محفظة المستخدم
    3. زيادة الرصيد بقيمة المكافأة
    4. معالجة الأخطاء المحتملة
    
    المعلمات:
    - sender: نموذج Bonus
    - instance: كائن المكافأة الذي تم حفظه
    - created: حالة الإنشاء (True/False)
    """
    
    if created:
        try:
            # الحصول على محفظة المستخدم
            user_wallet = Wallet.objects.get(user=instance.user)
            
            # التحقق من صحة المبلغ
            if instance.amount <= 0:
                raise ValueError("قيمة المكافأة يجب أن تكون أكبر من الصفر")
                
            # تحديث الرصيد
            user_wallet.balance += instance.amount
            user_wallet.save()
            
        except Wallet.DoesNotExist:
            raise ObjectDoesNotExist(f"المستخدم {instance.user} ليس لديه محفظة")
            
        except Exception as e:
            # تسجيل الخطأ في نظام التسجيلات
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"فشل في إضافة المكافأة: {str(e)}")
            raise
@receiver(post_save, sender=Transaction)
def update_wallet_balance(sender, instance, **kwargs):
    wallet = instance.wallet
    if instance.transaction_type == 'charge':
        wallet.balance += instance.amount
    elif instance.transaction_type in ['withdraw', 'payment']:
        if wallet.balance >= instance.amount:
            wallet.balance -= instance.amount
        else:
            raise ValueError("رصيد غير كافي")
    wallet.save()

@receiver(post_save, sender=Transfer)
def update_wallets_balance(sender, instance, **kwargs):
    from_wallet = instance.from_wallet
    to_wallet = instance.to_wallet
    amount = instance.amount

    if from_wallet.balance >= amount:
        from_wallet.balance -= amount
        to_wallet.balance += amount
        from_wallet.save()
        to_wallet.save()
    else:
        raise ValueError("رصيد غير كافي في محفظة المرسل")