from django.urls import path

from .views import checkin_booking_view, create_booking_view, my_bookings_view, user_home_view

app_name = 'booking'

urlpatterns = [
    path('home/', user_home_view, name='user_home'),
    path('my-bookings/', my_bookings_view, name='my_bookings'),
    path('new/', create_booking_view, name='book_slot'),
    path('<int:pk>/checkin/', checkin_booking_view, name='checkin_booking'),
]
