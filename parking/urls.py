from django.urls import path
from .views import (
    dashboard_view,
    generate_receipt,
    history_view,
    qr_scanner_view,
    scanner_receipt_pdf,
    settings_view,
    slot_create_view,
    slot_delete_view,
    slot_list_view,
    slot_status_api,
    slot_update_view,
    vehicle_entry_list_view,
    vehicle_exit_view,
    user_delete_view,
    user_role_update_view,
)

app_name = 'parking'

urlpatterns = [
    path('dashboard/', dashboard_view, name='dashboard'),
    path('slots/', slot_list_view, name='slot_list'),
    path('slots/add/', slot_create_view, name='slot_add'),
    path('slots/<int:pk>/edit/', slot_update_view, name='slot_edit'),
    path('slots/<int:pk>/delete/', slot_delete_view, name='slot_delete'),
    path('vehicles/', vehicle_entry_list_view, name='vehicle_entries'),
    path('vehicles/<int:pk>/exit/', vehicle_exit_view, name='vehicle_exit'),
    path('history/', history_view, name='history'),
    path('settings/', settings_view, name='settings'),
    path('scanner-receipt/<int:vehicle_id>/', scanner_receipt_pdf, name='scanner_receipt_pdf'),
    path('scanner/', qr_scanner_view, name='qr_scanner'),
    path('settings/users/<int:pk>/role/', user_role_update_view, name='user_role_update'),
    path('settings/users/<int:pk>/delete/', user_delete_view, name='user_delete'),
    path('api/slot-status/', slot_status_api, name='slot_status_api'),
]