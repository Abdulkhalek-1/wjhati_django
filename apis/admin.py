from django.contrib import admin
from .models import *

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'user_type', 'phone_number', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('user_type', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'phone_number')


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_username', 'photo', 'device_id', 'status', 'status_del', 'city', 'created_at', 'updated_at')
    list_filter = ('status', 'status_del', 'city')
    search_fields = ('user__username', 'city')

    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'Username'


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_username', 'balance', 'created_at', 'updated_at')
    search_fields = ('user__username',)

    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'Username'


@admin.register(ChargeCard)
class ChargeCardAdmin(admin.ModelAdmin):
    list_display = ('id', 'card_code', 'amount', 'is_used', 'wallet_user', 'created_at', 'updated_at')
    list_filter = ('is_used',)
    search_fields = ('card_code', 'wallet__user__username')

    def wallet_user(self, obj):
        return obj.wallet.user.username
    wallet_user.short_description = 'Wallet User'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'wallet_user', 'transaction_type', 'amount', 'status', 'description', 'created_at', 'updated_at')
    list_filter = ('transaction_type', 'status')
    search_fields = ('wallet__user__username', 'description')

    def wallet_user(self, obj):
        return obj.wallet.user.username
    wallet_user.short_description = 'Wallet User'


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_wallet_user', 'to_wallet_user', 'amount', 'status', 'created_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('from_wallet__user__username', 'to_wallet__user__username')

    def from_wallet_user(self, obj):
        return obj.from_wallet.user.username
    from_wallet_user.short_description = 'From User'

    def to_wallet_user(self, obj):
        return obj.to_wallet.user.username
    to_wallet_user.short_description = 'To User'


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('id', 'model', 'plate_number', 'color', 'capacity', 'status', 'created_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('model', 'plate_number')


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_username', 'license_number', 'vehicle_model', 'status', 'created_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'license_number')

    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'Username'

    def vehicle_model(self, obj):
        return obj.vehicle.model
    vehicle_model.short_description = 'Vehicle Model'