# jobs/admin.py
from django.contrib import admin
from .models import (
    Location, JobType, JobPriority, Team, CivilWorker, Job,
    CivilWorkerAssignment, JobTask, JobNote, JobAttachment,
    InventoryUsage, JobStatusUpdate
)


class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'location_type', 'city', 'coordinates')
    list_filter = ('location_type', 'city', 'is_fiber_connected')
    search_fields = ('name', 'address', 'city', 'tower_id')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'address', 'city', 'coordinates', 'location_type', 'notes')
        }),
        ('Tower Details', {
            'fields': ('tower_height', 'tower_id'),
            'classes': ('collapse',)
        }),
        ('Fiber Details', {
            'fields': ('is_fiber_connected', 'fiber_termination_type'),
            'classes': ('collapse',)
        }),
    )


class JobTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'estimated_duration', 'requires_civil_team')
    list_filter = ('company', 'requires_civil_team')
    search_fields = ('name', 'description')


class JobPriorityAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'color')
    ordering = ('-value',)


class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'team_type', 'team_lead', 'is_active')
    list_filter = ('team_type', 'is_active')
    search_fields = ('name', 'description')
    filter_horizontal = ('members',)


class CivilWorkerAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'id_number', 'phone_number', 'daily_rate', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('first_name', 'last_name', 'id_number')


class CivilWorkerAssignmentInline(admin.TabularInline):
    model = CivilWorkerAssignment
    extra = 1


class JobTaskInline(admin.TabularInline):
    model = JobTask
    extra = 3


class JobNoteInline(admin.TabularInline):
    model = JobNote
    extra = 1


class JobAttachmentInline(admin.TabularInline):
    model = JobAttachment
    extra = 1
    readonly_fields = ('file_size', 'file_type', 'uploaded_at', 'uploaded_by')


class InventoryUsageInline(admin.TabularInline):
    model = InventoryUsage
    extra = 1


class JobStatusUpdateInline(admin.TabularInline):
    model = JobStatusUpdate
    extra = 0
    readonly_fields = ('old_status', 'new_status', 'updated_at', 'updated_by')


class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'job_type', 'status', 'priority', 'location', 'assigned_team', 'scheduled_start_date')
    list_filter = ('status', 'job_type', 'priority', 'assigned_team', 'requires_civil_team')
    search_fields = ('title', 'description', 'reference_number', 'tags')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'job_type', 'priority', 'status')
        }),
        ('Location', {
            'fields': ('location',)
        }),
        ('Scheduling', {
            'fields': ('scheduled_start_date', 'scheduled_end_date', 'actual_start_date', 'actual_end_date')
        }),
        ('Assignment', {
            'fields': ('created_by', 'assigned_team', 'assigned_to')
        }),
        ('Civil Team', {
            'fields': ('requires_civil_team',),
            'classes': ('collapse',)
        }),
        ('Financial', {
            'fields': ('estimated_cost', 'actual_cost'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('reference_number', 'tags', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [
        JobTaskInline,
        CivilWorkerAssignmentInline,
        JobNoteInline,
        JobAttachmentInline,
        InventoryUsageInline,
        JobStatusUpdateInline,
    ]


admin.site.register(Location, LocationAdmin)
admin.site.register(JobType, JobTypeAdmin)
admin.site.register(JobPriority, JobPriorityAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(CivilWorker, CivilWorkerAdmin)
admin.site.register(Job, JobAdmin)