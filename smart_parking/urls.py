from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('accounts.urls')),
    path('parking/', include('parking.urls')),
    path('booking/', include('booking.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)