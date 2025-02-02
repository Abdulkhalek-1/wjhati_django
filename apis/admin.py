from django.contrib import admin
from .models import *
from django.utils.translation import gettext_lazy as _

class ClientAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'status')
    list_filter = ('status', 'city')
    raw_id_fields = ('user',)

class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'currency', 'is_locked')
    list_filter = ('currency', 'is_locked')
    search_fields = ('user__username',)

class TransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'transaction_type', 'amount', 'status', 'created_at')
    list_filter = ('transaction_type', 'status')
    readonly_fields = ('reference_number', 'created_at')

class TransferAdmin(admin.ModelAdmin):
    list_display = ('from_wallet', 'to_wallet', 'amount', 'status', 'transfer_code')
    list_filter = ('status',)
    search_fields = ('transfer_code',)
    readonly_fields = ('transfer_code',)

class VehicleAdmin(admin.ModelAdmin):
    list_display = ('model', 'plate_number', 'vehicle_type', 'status')
    list_filter = ('vehicle_type', 'status')
    search_fields = ('plate_number',)

class DriverAdmin(admin.ModelAdmin):
    list_display = ('user', 'license_number', 'rating', 'total_trips', 'is_available')
    list_filter = ('is_available',)
    raw_id_fields = ('user', 'vehicles')

class TripAdmin(admin.ModelAdmin):
    list_display = ('from_location', 'to_location', 'departure_time', 'status', 'driver')
    list_filter = ('status',)
    raw_id_fields = ('driver',)
    readonly_fields = ('route_coordinates',)

class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'status', 'priority', 'created_at')
    list_filter = ('status', 'priority')
    raw_id_fields = ('user', 'assigned_to')

class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('driver', 'plan', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active',)
    raw_id_fields = ('driver',)

class ItemDeliveryAdmin(admin.ModelAdmin):
    list_display = ('delivery_code', 'sender', 'receiver_name', 'status')
    list_filter = ('status',)
    search_fields = ('delivery_code',)
    readonly_fields = ('delivery_code',)

admin.site.register(Client, ClientAdmin)
admin.site.register(Wallet, WalletAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(Transfer, TransferAdmin)
admin.site.register(Vehicle, VehicleAdmin)
admin.site.register(Driver, DriverAdmin)
admin.site.register(Bonus)
admin.site.register(Trip, TripAdmin)
admin.site.register(TripStop)
admin.site.register(Rating)
admin.site.register(SupportTicket, SupportTicketAdmin)
admin.site.register(SubscriptionPlan)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Booking)
admin.site.register(CasheBooking)
admin.site.register(ItemDelivery, ItemDeliveryAdmin)
admin.site.register(CasheItemDelivery)
admin.site.register(Chat)
admin.site.register(Message)