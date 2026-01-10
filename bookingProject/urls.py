from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import handler404, handler500, handler400

handler404 = 'bookingApp.views.error_404'
handler500 = 'bookingApp.views.error_500'

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("bookingApp.urls")),
    path('accounts/', include('allauth.urls')),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # This allows the URL to be generated even when DEBUG is False
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
