from django.urls import path
from . import views

app_name = 'calendar_app'

urlpatterns = [
    # Main calendar views
    path('', views.calendar_dashboard, name='calendar_dashboard'),
    path('view/', views.calendar_view, name='calendar_view'),
    path('api/events/', views.events_api, name='events_api'),

    # Event management
    path('event/create/', views.event_create, name='event_create'),
    path('event/<int:pk>/', views.event_detail, name='event_detail'),
    path('event/<int:pk>/edit/', views.event_edit, name='event_edit'),
    path('event/<int:pk>/delete/', views.event_delete, name='event_delete'),
    path('event/<int:pk>/rsvp/', views.event_rsvp, name='event_rsvp'),

    # Quick actions
    path('quick-create/', views.quick_event_create, name='quick_event_create'),

    # Calendar management
    path('calendars/', views.calendar_management, name='calendar_management'),
    path('calendars/create/', views.calendar_create, name='calendar_create'),
]