from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    EventCategory, Event, EventAttendee, EventReminder,
    Calendar, CalendarPermission, EventAttachment
)


@admin.register(EventCategory)
class EventCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'event_type', 'color_display', 'company', 'is_active']
    list_filter = ['event_type', 'company', 'is_active']
    search_fields = ['name', 'description']
    list_editable = ['is_active']

    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.color,
            obj.color
        )
    color_display.short_description = 'Color'


class EventAttendeeInline(admin.TabularInline):
    model = EventAttendee
    extra = 0
    fields = ['user', 'status', 'is_organizer', 'response_date', 'notes']
    readonly_fields = ['response_date']


class EventAttachmentInline(admin.TabularInline):
    model = EventAttachment
    extra = 0
    fields = ['file', 'description', 'uploaded_by', 'uploaded_at']
    readonly_fields = ['uploaded_by', 'uploaded_at', 'filename', 'file_size']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'category', 'start_datetime', 'end_datetime',
        'created_by', 'priority', 'attendee_count', 'is_cancelled'
    ]
    list_filter = [
        'category', 'priority', 'is_cancelled', 'all_day',
        'recurrence_type', 'start_datetime', 'created_at'
    ]
    search_fields = ['title', 'description', 'location', 'created_by__username']
    date_hierarchy = 'start_datetime'
    ordering = ['-start_datetime']

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'category', 'priority')
        }),
        ('Date & Time', {
            'fields': ('start_datetime', 'end_datetime', 'all_day')
        }),
        ('Location & Attendees', {
            'fields': ('location', 'is_private')
        }),
        ('Recurrence', {
            'fields': ('recurrence_type', 'recurrence_interval', 'recurrence_end_date', 'parent_event'),
            'classes': ('collapse',)
        }),
        ('Linked Items', {
            'fields': ('linked_task', 'linked_job'),
            'classes': ('collapse',)
        }),
        ('Notifications', {
            'fields': ('send_reminders', 'reminder_minutes')
        }),
        ('Status', {
            'fields': ('is_cancelled', 'created_by'),
            'classes': ('collapse',)
        })
    )

    readonly_fields = ['created_by']
    inlines = [EventAttendeeInline, EventAttachmentInline]

    def attendee_count(self, obj):
        return obj.attendees.count()
    attendee_count.short_description = 'Attendees'

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new event
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EventAttendee)
class EventAttendeeAdmin(admin.ModelAdmin):
    list_display = ['event', 'user', 'status', 'is_organizer', 'response_date']
    list_filter = ['status', 'is_organizer', 'response_date']
    search_fields = ['event__title', 'user__username', 'user__email']
    raw_id_fields = ['event', 'user']


@admin.register(EventReminder)
class EventReminderAdmin(admin.ModelAdmin):
    list_display = ['event', 'user', 'reminder_type', 'sent_at', 'is_sent']
    list_filter = ['reminder_type', 'is_sent', 'sent_at']
    search_fields = ['event__title', 'user__username']
    raw_id_fields = ['event', 'user']


class CalendarPermissionInline(admin.TabularInline):
    model = CalendarPermission
    extra = 0
    fields = ['user', 'permission', 'granted_by', 'granted_at']
    readonly_fields = ['granted_by', 'granted_at']


@admin.register(Calendar)
class CalendarAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'calendar_type', 'owner', 'company', 'department',
        'color_display', 'is_default', 'is_public', 'is_active'
    ]
    list_filter = ['calendar_type', 'company', 'is_default', 'is_public', 'is_active']
    search_fields = ['name', 'description', 'owner__username']
    list_editable = ['is_default', 'is_public', 'is_active']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'calendar_type', 'color')
        }),
        ('Ownership', {
            'fields': ('owner', 'company', 'department')
        }),
        ('Settings', {
            'fields': ('is_default', 'is_public', 'time_zone', 'is_active')
        })
    )

    inlines = [CalendarPermissionInline]

    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.color,
            obj.color
        )
    color_display.short_description = 'Color'


@admin.register(CalendarPermission)
class CalendarPermissionAdmin(admin.ModelAdmin):
    list_display = ['calendar', 'user', 'permission', 'granted_by', 'granted_at']
    list_filter = ['permission', 'granted_at']
    search_fields = ['calendar__name', 'user__username', 'granted_by__username']
    raw_id_fields = ['calendar', 'user', 'granted_by']


@admin.register(EventAttachment)
class EventAttachmentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'event', 'uploaded_by', 'file_size_display', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['filename', 'event__title', 'uploaded_by__username']
    readonly_fields = ['filename', 'file_size', 'uploaded_at']
    raw_id_fields = ['event', 'uploaded_by']

    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "Unknown"
    file_size_display.short_description = 'File Size'