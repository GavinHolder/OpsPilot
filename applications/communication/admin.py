from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    ChatRoom, ChatRoomMembership, Message, MessageReaction,
    Announcement, AnnouncementRead, ExternalIntegration,
    ExternalMessage, MessageTemplate, CommunicationLog
)

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'room_type', 'created_by', 'is_private', 'member_count', 'is_archived', 'created_at']
    list_filter = ['room_type', 'is_private', 'is_archived', 'created_at']
    search_fields = ['name', 'description', 'created_by__username']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'room_type')
        }),
        ('Settings', {
            'fields': ('is_private', 'is_archived', 'allow_file_sharing', 'max_members')
        }),
        ('Linked Items', {
            'fields': ('linked_task', 'linked_job', 'department'),
            'classes': ('collapse',)
        }),
        ('Creation Info', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_by', 'created_at', 'updated_at']

    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Members'

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new chat room
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class ChatRoomMembershipInline(admin.TabularInline):
    model = ChatRoomMembership
    extra = 0
    fields = ['user', 'role', 'joined_at', 'last_read_at', 'is_muted', 'is_pinned']
    readonly_fields = ['joined_at', 'last_read_at']


@admin.register(ChatRoomMembership)
class ChatRoomMembershipAdmin(admin.ModelAdmin):
    list_display = ['room', 'user', 'role', 'joined_at', 'last_read_at', 'is_muted', 'is_pinned']
    list_filter = ['role', 'is_muted', 'is_pinned', 'joined_at']
    search_fields = ['room__name', 'user__username', 'user__email']
    date_hierarchy = 'joined_at'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'room', 'sender', 'message_type', 'short_content', 'has_attachment', 'created_at']
    list_filter = ['message_type', 'is_edited', 'is_deleted', 'is_pinned', 'created_at']
    search_fields = ['content', 'room__name', 'sender__username']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Message Content', {
            'fields': ('room', 'sender', 'message_type', 'content', 'reply_to')
        }),
        ('Attachments', {
            'fields': ('file_attachment', 'file_name', 'file_size'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_edited', 'is_deleted', 'is_pinned')
        }),
        ('External Integration', {
            'fields': ('whatsapp_message_id', 'telegram_message_id'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    def short_content(self, obj):
        if len(obj.content) > 50:
            return f"{obj.content[:50]}..."
        return obj.content
    short_content.short_description = 'Content'

    def has_attachment(self, obj):
        return bool(obj.file_attachment)
    has_attachment.boolean = True
    has_attachment.short_description = 'Attachment'


@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ['message', 'user', 'reaction', 'created_at']
    list_filter = ['reaction', 'created_at']
    search_fields = ['message__content', 'user__username']
    date_hierarchy = 'created_at'


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'announcement_type', 'priority', 'created_by', 'is_published', 'read_count', 'created_at']
    list_filter = ['announcement_type', 'priority', 'is_published', 'created_at']
    search_fields = ['title', 'content', 'created_by__username']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Announcement Content', {
            'fields': ('title', 'content', 'announcement_type', 'priority')
        }),
        ('Targeting', {
            'fields': ('target_all_users', 'target_departments', 'target_users')
        }),
        ('Attachments', {
            'fields': ('attachment',),
            'classes': ('collapse',)
        }),
        ('Publishing', {
            'fields': ('is_published', 'publish_at', 'expires_at')
        }),
        ('External Sharing', {
            'fields': ('send_email', 'send_whatsapp', 'send_telegram'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_by', 'created_at', 'updated_at']

    def read_count(self, obj):
        return obj.read_by.count()
    read_count.short_description = 'Read By'

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new announcement
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ExternalIntegration)
class ExternalIntegrationAdmin(admin.ModelAdmin):
    list_display = ['name', 'platform_type', 'is_active', 'auto_sync', 'last_sync', 'created_by', 'created_at']
    list_filter = ['platform_type', 'is_active', 'auto_sync', 'created_at']
    search_fields = ['name', 'webhook_url', 'bot_username', 'created_by__username']

    fieldsets = (
        ('Integration Info', {
            'fields': ('name', 'platform_type')
        }),
        ('Configuration', {
            'fields': ('api_token', 'webhook_url', 'bot_username'),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('is_active', 'auto_sync', 'rate_limit_per_minute')
        }),
    )

    readonly_fields = ['created_by', 'last_sync', 'created_at', 'updated_at']

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new integration
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ExternalMessage)
class ExternalMessageAdmin(admin.ModelAdmin):
    list_display = ['integration', 'sender_identifier', 'sender_name', 'short_content', 'is_processed', 'response_sent', 'received_at']
    list_filter = ['integration', 'message_type', 'is_processed', 'response_sent', 'received_at']
    search_fields = ['sender_identifier', 'sender_name', 'content', 'external_id']

    fieldsets = (
        ('Message Info', {
            'fields': ('integration', 'external_id', 'sender_identifier', 'sender_name', 'content', 'message_type')
        }),
        ('Linking', {
            'fields': ('linked_user', 'linked_chat_room')
        }),
        ('Processing', {
            'fields': ('is_processed', 'response_sent', 'received_at', 'processed_at')
        }),
    )

    readonly_fields = ['received_at', 'processed_at']

    def short_content(self, obj):
        if len(obj.content) > 50:
            return f"{obj.content[:50]}..."
        return obj.content
    short_content.short_description = 'Content'


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'subject', 'short_content', 'usage_count', 'is_active', 'created_at']
    list_filter = ['template_type', 'is_active', 'created_at']
    search_fields = ['name', 'subject', 'content', 'created_by__username']

    fieldsets = (
        ('Template Info', {
            'fields': ('name', 'template_type', 'subject', 'content')
        }),
        ('Variables', {
            'fields': ('variables',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'usage_count')
        }),
    )

    readonly_fields = ['usage_count', 'created_by', 'created_at', 'updated_at']

    def short_content(self, obj):
        if len(obj.content) > 50:
            return f"{obj.content[:50]}..."
        return obj.content
    short_content.short_description = 'Content'

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new template
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CommunicationLog)
class CommunicationLogAdmin(admin.ModelAdmin):
    list_display = ['log_type', 'user', 'description', 'chat_room', 'created_at']
    list_filter = ['log_type', 'created_at']
    search_fields = ['description', 'user__username', 'chat_room__name']
    readonly_fields = ['log_type', 'user', 'description', 'chat_room', 'message', 'announcement', 'metadata', 'created_at']
    date_hierarchy = 'created_at'