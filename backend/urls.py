from django.contrib import admin
from django.urls import path
from django.urls import path, include
from apis.views import *
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/token/", TokenObtainPairView.as_view(), name="get_token"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path('api/save-fcm-token/', SaveFCMTokenView.as_view(), name='save-fcm-token'),
    path("api-auth/", include("rest_framework.urls")),
    path('api/register/', RegisterView.as_view(), name='register'),
    path("",include('apis.urls')),

] + static ( settings.MEDIA_URL, document_root= settings.MEDIA_ROOT)
urlpatterns += staticfiles_urlpatterns()