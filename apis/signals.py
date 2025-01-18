from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Transaction, Transfer

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