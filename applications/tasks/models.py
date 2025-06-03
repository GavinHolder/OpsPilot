from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse


class TaskCategory(models.Model):
    """Categories for tasks (e.g., WISP, FNO, Personal, Meeting)"""
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=20, default='#3498db')  # Hex color code
    icon = models.CharField(max_length=50, default='fa-tasks')  # FontAwesome icon

    class Meta:
        verbose_name = 'Task Category'
        verbose_name_plural = 'Task Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class TaskPriority(models.Model):
    """Priority levels for tasks (e.g., Low, Medium, High, Urgent)"""
    name = models.CharField(max_length=50)
    value = models.IntegerField(unique=True)  # Numeric value for sorting (1=low, 4=urgent)
    color = models.CharField(max_length=20, default='#3498db')  # Hex color code
    icon = models.CharField(max_length=50, default='fa-flag')  # FontAwesome icon

    class Meta:
        verbose_name = 'Task Priority'
        verbose_name_plural = 'Task Priorities'
        ordering = ['-value']

    def __str__(self):
        return self.name


class Task(models.Model):
    """Main task model for tracking todos, assignments, and action items"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('deferred', 'Deferred'),
        ('cancelled', 'Cancelled'),
    )

    COMPANY_CHOICES = (
        ('wisp', 'WISP'),
        ('fno', 'FNO'),
        ('both', 'Both'),
        ('other', 'Other'),
    )

    # Basic task information
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.ForeignKey(TaskPriority, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey(TaskCategory, on_delete=models.SET_NULL, null=True, blank=True)
    company = models.CharField(max_length=10, choices=COMPANY_CHOICES, default='both')

    # Dates and deadlines
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deadline = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Assignment and ownership
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_tasks'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks'
    )

    # Related entities (will be defined as generic relations later)
    # For now, we'll use simple text fields as placeholders
    related_job = models.CharField(max_length=255, blank=True)
    related_tower = models.CharField(max_length=255, blank=True)

    # Reminder settings
    reminder_enabled = models.BooleanField(default=False)
    reminder_datetime = models.DateTimeField(null=True, blank=True)
    reminder_sent = models.BooleanField(default=False)

    # Task specific flags
    is_recurring = models.BooleanField(default=False)
    recurrence_pattern = models.CharField(max_length=255, blank=True)  # JSON field in the future

    # Task indexing for grouping and search
    tags = models.CharField(max_length=255, blank=True)  # Comma-separated tags

    class Meta:
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['deadline']),
            models.Index(fields=['created_by']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['company']),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('tasks:task_detail', kwargs={'pk': self.pk})

    def mark_completed(self):
        """Mark a task as completed and record the completion time"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()

    def is_overdue(self):
        """Check if task is past its deadline"""
        if self.deadline and self.status != 'completed':
            return timezone.now() > self.deadline
        return False

    def days_until_deadline(self):
        """Calculate days remaining until deadline"""
        if self.deadline:
            now = timezone.now()
            return (self.deadline - now).days
        return None

    def get_tags_list(self):
        """Return tags as a list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',')]
        return []


class Subtask(models.Model):
    """Subtasks/checklist items for the main task"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='subtasks')
    description = models.CharField(max_length=255)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Subtask'
        verbose_name_plural = 'Subtasks'
        ordering = ['order']

    def __str__(self):
        return self.description

    def mark_completed(self):
        """Mark a subtask as completed and record the completion time"""
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save()


class TaskAttachment(models.Model):
    """File attachments for tasks"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_attachments/%Y/%m/')
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()  # Size in bytes
    file_type = models.CharField(max_length=100)  # MIME type
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'Task Attachment'
        verbose_name_plural = 'Task Attachments'
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.file_name


class TaskComment(models.Model):
    """Comments on tasks for discussion"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Task Comment'
        verbose_name_plural = 'Task Comments'
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author} on {self.task}'


class TaskVoiceNote(models.Model):
    """Voice notes attached to tasks"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='voice_notes')
    audio_file = models.FileField(upload_to='task_voice_notes/%Y/%m/')
    duration = models.PositiveIntegerField(help_text='Duration in seconds')
    transcription = models.TextField(blank=True, help_text='Automatic transcription of the voice note')
    recorded_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'Task Voice Note'
        verbose_name_plural = 'Task Voice Notes'
        ordering = ['-recorded_at']

    def __str__(self):
        return f'Voice note by {self.recorded_by} on {self.task}'