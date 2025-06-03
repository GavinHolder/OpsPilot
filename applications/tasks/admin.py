from django.contrib import admin
from .models import (
    Task, Subtask, TaskCategory, TaskPriority, 
    TaskAttachment, TaskComment, TaskVoiceNote
)


class SubtaskInline(admin.TabularInline):
    model = Subtask
    extra = 1


class TaskAttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 1
    readonly_fields = ('file_size', 'file_type', 'uploaded_at', 'uploaded_by')


class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'priority', 'company', 'deadline', 'created_by', 'assigned_to')
    list_filter = ('status', 'priority', 'company', 'category', 'created_at', 'deadline')
    search_fields = ('title', 'description', 'tags')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'status', 'priority', 'category', 'company')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at', 'deadline', 'completed_at')
        }),
        ('Assignment', {
            'fields': ('created_by', 'assigned_to')
        }),
        ('Related Items', {
            'fields': ('related_job', 'related_tower')
        }),
        ('Reminders', {
            'fields': ('reminder_enabled', 'reminder_datetime', 'reminder_sent')
        }),
        ('Recurrence', {
            'fields': ('is_recurring', 'recurrence_pattern')
        }),
        ('Metadata', {
            'fields': ('tags',)
        }),
    )
    inlines = [SubtaskInline, TaskAttachmentInline, TaskCommentInline]


@admin.register(TaskCategory)
class TaskCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'icon')
    search_fields = ('name',)


@admin.register(TaskPriority)
class TaskPriorityAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'color', 'icon')
    ordering = ('-value',)


@admin.register(TaskVoiceNote)
class TaskVoiceNoteAdmin(admin.ModelAdmin):
    list_display = ('task', 'duration', 'recorded_at', 'recorded_by')
    readonly_fields = ('recorded_at',)
    search_fields = ('task__title', 'transcription')