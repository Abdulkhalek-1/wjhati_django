from django.contrib import admin
from .models import *

admin.site.register(Client)
admin.site.register(Driver)
admin.site.register(Trip)
admin.site.register(BookingRequest)
admin.site.register(Booking)


