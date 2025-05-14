from django.contrib import admin
from django.urls import path
from django.urls import path, include
from apis.views import *
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/token/", TokenObtainPairView.as_view(), name="get_token"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path('api/save-fcm-token/', SaveFCMTokenView.as_view(), name='save-fcm-token'),
        path('client/trips/', ClientTripsView.as_view(), name='client-trips'),
    path("api-auth/", include("rest_framework.urls")),
    path('api/register/', RegisterView.as_view(), name='register'),
    path("",include('apis.urls')),

] + static ( settings.MEDIA_URL, document_root= settings.MEDIA_ROOT)
