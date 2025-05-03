from django.contrib import admin
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _
from .models import (
    Client, Wallet, Transaction, Vehicle, Driver, Trip, Booking,
    Rating, Chat, Message, SupportTicket, Notification, Transfer,
    SubscriptionPlan, Subscription, Bonus, TripStop, CasheBooking,
    CasheItemDelivery
)

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'status', 'status_del', 'device_id', 'created_at')
    search_fields = ('user__username', 'city', 'device_id')
    list_filter = ('status', 'city')


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'currency', 'is_locked', 'created_at')
    search_fields = ('user__username',)
    list_filter = ('currency', 'is_locked')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'transaction_type', 'amount', 'status', 'reference_number', 'created_at')
    search_fields = ('wallet__user__username', 'transaction_type')
    list_filter = ('transaction_type', 'status')
    readonly_fields = ('reference_number',)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('model', 'plate_number', 'color', 'capacity', 'vehicle_type', 'manufacture_year', 'status')
    search_fields = ('plate_number', 'model')
    list_filter = ('vehicle_type', 'status')


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('user', 'license_number', 'rating', 'total_trips', 'is_available', 'where_location')
    search_fields = ('user__username', 'license_number')
    list_filter = ('is_available',)


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('from_location', 'to_location', 'departure_time', 'estimated_duration', 'available_seats', 'status', 'driver')
    search_fields = ('from_location', 'to_location', 'driver__user__username')
    list_filter = ('departure_time', 'status')
    readonly_fields = ('route_coordinates',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('trip', 'customer', 'seats', 'total_price', 'status')
    search_fields = ('customer__user__username', 'trip__from_location', 'trip__to_location')
    list_filter = ('status',)


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('trip', 'rated_by', 'driver', 'rating', 'comment')
    search_fields = ('rated_by__user__username', 'driver__user__username')
    list_filter = ('rating',)


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'is_group', 'created_at', 'updated_at')
    search_fields = ('title', 'participants__username')
    list_filter = ('is_group',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('chat', 'sender', 'content', 'is_read', 'created_at')
    search_fields = ('sender__username', 'content')
    list_filter = ('is_read',)


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'status', 'priority', 'created_at')
    search_fields = ('user__username', 'subject')
    list_filter = ('status', 'priority')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'is_read', 'notification_type', 'created_at')
    search_fields = ('user__username', 'title')
    list_filter = ('notification_type', 'is_read')


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('from_wallet', 'to_wallet', 'amount', 'status', 'transfer_code', 'created_at')
    search_fields = ('from_wallet__user__username', 'to_wallet__user__username', 'transfer_code')
    list_filter = ('status',)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days', 'max_trips', 'is_active', 'created_at')
    search_fields = ('name',)
    list_filter = ('is_active',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('driver', 'plan', 'start_date', 'end_date', 'is_active', 'remaining_trips')
    search_fields = ('driver__user__username', 'plan__name')
    list_filter = ('is_active', 'end_date')


@admin.register(Bonus)
class BonusAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'reason', 'expiration_date', 'created_at')
    search_fields = ('user__username', 'reason')
    list_filter = ('expiration_date',)


@admin.register(TripStop)
class TripStopAdmin(admin.ModelAdmin):
    list_display = ('trip', 'location', 'order', 'arrival_time')
    search_fields = ('trip__from_location', 'location')
    list_filter = ('order',)


@admin.register(CasheBooking)
class CasheBookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'from_location', 'to_location', 'departure_time', 'passengers', 'status')
    search_fields = ('user__user__username', 'from_location', 'to_location')
    list_filter = ('departure_time', 'status')


@admin.register(CasheItemDelivery)
class CasheItemDeliveryAdmin(admin.ModelAdmin):
    list_display = ('user', 'from_location', 'to_location', 'item_description', 'weight', 'urgent', 'status', 'created_at')
    search_fields = ('user__user__username', 'from_location', 'to_location')
    list_filter = ('urgent', 'status')