from django.urls import path
from . import views

app_name = 'communication'

urlpatterns = [
    # Chat Room URLs
    path('chat/', views.chat_rooms_list, name='chat_rooms_list'),
    path('chat/room/create/', views.chat_room_create, name='chat_room_create'),
    path('chat/room/<uuid:room_id>/', views.chat_room_detail, name='chat_room_detail'),
    path('chat/room/<uuid:room_id>/edit/', views.chat_room_edit, name='chat_room_edit'),
    path('chat/room/<uuid:room_id>/members/', views.chat_room_members, name='chat_room_members'),
    path('chat/room/<uuid:room_id>/add-member/', views.chat_room_add_member, name='chat_room_add_member'),
    path('chat/room/<uuid:room_id>/remove-member/<int:user_id>/', views.chat_room_remove_member, name='chat_room_remove_member'),
    path('chat/room/<uuid:room_id>/update-role/<int:user_id>/', views.chat_room_update_role, name='chat_room_update_role'),
    path('chat/room/<uuid:room_id>/archive/', views.chat_room_archive, name='chat_room_archive'),

    # Message URLs
    path('chat/room/<uuid:room_id>/messages/load/', views.load_messages, name='load_messages'),
    path('chat/room/<uuid:room_id>/send-message/', views.send_message, name='send_message'),
    path('chat/room/<uuid:room_id>/message/<uuid:message_id>/edit/', views.edit_message, name='edit_message'),
    path('chat/room/<uuid:room_id>/message/<uuid:message_id>/delete/', views.delete_message, name='delete_message'),
    path('chat/room/<uuid:room_id>/message/<uuid:message_id>/pin/', views.pin_message, name='pin_message'),
    path('chat/room/<uuid:room_id>/message/<uuid:message_id>/react/', views.react_to_message, name='react_to_message'),

    # Announcement URLs
    path('announcements/', views.announcements_list, name='announcements_list'),
    path('announcements/create/', views.announcement_create, name='announcement_create'),
    path('announcements/<int:announcement_id>/', views.announcement_detail, name='announcement_detail'),
    path('announcements/<int:announcement_id>/edit/', views.announcement_edit, name='announcement_edit'),
    path('announcements/<int:announcement_id>/delete/', views.announcement_delete, name='announcement_delete'),
    path('announcements/<int:announcement_id>/publish/', views.announcement_publish, name='announcement_publish'),
    path('announcements/<int:announcement_id>/mark-read/', views.announcement_mark_read, name='announcement_mark_read'),

    # External Integration URLs
    path('integrations/', views.integrations_list, name='integrations_list'),
    path('integrations/create/', views.integration_create, name='integration_create'),
    path('integrations/<int:integration_id>/', views.integration_detail, name='integration_detail'),
    path('integrations/<int:integration_id>/edit/', views.integration_edit, name='integration_edit'),
    path('integrations/<int:integration_id>/toggle-active/', views.integration_toggle_active, name='integration_toggle_active'),
    path('integrations/<int:integration_id>/sync/', views.integration_sync, name='integration_sync'),

    # Message Template URLs
    path('templates/', views.templates_list, name='templates_list'),
    path('templates/create/', views.template_create, name='template_create'),
    path('templates/<int:template_id>/', views.template_detail, name='template_detail'),
    path('templates/<int:template_id>/edit/', views.template_edit, name='template_edit'),
    path('templates/<int:template_id>/delete/', views.template_delete, name='template_delete'),

    # API endpoints for HTMX
    path('api/unread-counts/', views.api_unread_counts, name='api_unread_counts'),
    path('api/mark-as-read/<uuid:room_id>/', views.api_mark_as_read, name='api_mark_as_read'),
]