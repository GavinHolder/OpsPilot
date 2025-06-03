from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from applications.accounts.models import UserProfile, Company, Department
from applications.tasks.models import Task
from applications.jobs.models import Job


class EventCategory(models.Model):
    """Categories for different types of events"""
    EVENT_TYPES = [
        ('MEETING', 'Meeting'),
        ('MAINTENANCE', 'Maintenance'),
        ('TASK', 'Task Deadline'),
        ('JOB', 'Job Schedule'),
        ('REMINDER', 'Reminder'),
        ('TRAINING', 'Training'),
        ('HOLIDAY', 'Holiday'),
        ('PERSONAL', 'Personal'),
        ('COMPANY', 'Company Event'),
    ]

    name = models.CharField(max_length=100)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default='MEETING')
    color = models.CharField(max_length=7, default='#3498db', help_text="Hex color code for calendar display")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='event_categories', null=True,
                                blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Event Categories"
        unique_together = ('name', 'company')


class Event(models.Model):
    """Main event model for calendar system"""
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]

    RECURRENCE_TYPES = [
        ('NONE', 'No Recurrence'),
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('YEARLY', 'Yearly'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(EventCategory, on_delete=models.CASCADE, related_name='events')

    # Date and time fields
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    all_day = models.BooleanField(default=False)

    # Location and people
    location = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_events')
    attendees = models.ManyToManyField(User, through='EventAttendee', related_name='events')

    # Priority and visibility
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    is_private = models.BooleanField(default=False)

    # Recurrence
    recurrence_type = models.CharField(max_length=10, choices=RECURRENCE_TYPES, default='NONE')
    recurrence_interval = models.PositiveIntegerField(default=1, help_text="Repeat every X days/weeks/months")
    recurrence_end_date = models.DateField(null=True, blank=True)
    parent_event = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                                     related_name='recurring_events')

    # Linked entities
    linked_task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True,
                                    related_name='calendar_events')
    linked_job = models.ForeignKey(Job, on_delete=models.CASCADE, null=True, blank=True, related_name='calendar_events')

    # Notifications
    send_reminders = models.BooleanField(default=True)
    reminder_minutes = models.PositiveIntegerField(default=30, help_text="Minutes before event to send reminder")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_cancelled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} - {self.start_datetime.strftime('%Y-%m-%d %H:%M')}"

    def clean(self):
        """Validate the event data"""
        if self.end_datetime <= self.start_datetime:
            raise ValidationError('End time must be after start time.')

        if self.recurrence_type != 'NONE' and not self.recurrence_end_date:
            raise ValidationError('Recurrence end date is required for recurring events.')

    def get_absolute_url(self):
        return reverse('calendar_app:event_detail', kwargs={'pk': self.pk})

    @property
    def duration(self):
        """Get event duration in minutes"""
        return int((self.end_datetime - self.start_datetime).total_seconds() / 60)

    @property
    def is_today(self):
        """Check if event is today"""
        return self.start_datetime.date() == timezone.now().date()

    @property
    def is_upcoming(self):
        """Check if event is in the future"""
        return self.start_datetime > timezone.now()

    @property
    def is_overdue(self):
        """Check if event has passed"""
        return self.end_datetime < timezone.now()

    class Meta:
        ordering = ['start_datetime']
        indexes = [
            models.Index(fields=['start_datetime']),
            models.Index(fields=['end_datetime']),
            models.Index(fields=['created_by']),
            models.Index(fields=['category']),
        ]


class EventAttendee(models.Model):
    """Attendee relationship with RSVP status"""
    ATTENDANCE_STATUS = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('DECLINED', 'Declined'),
        ('TENTATIVE', 'Tentative'),
        ('NO_RESPONSE', 'No Response'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=15, choices=ATTENDANCE_STATUS, default='PENDING')
    response_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    is_organizer = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.event.title} ({self.status})"

    class Meta:
        unique_together = ('event', 'user')


class EventReminder(models.Model):
    """Track sent reminders to avoid duplicates"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reminders')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reminder_type = models.CharField(max_length=20, choices=[
        ('EMAIL', 'Email'),
        ('APP', 'In-App'),
        ('TELEGRAM', 'Telegram'),
        ('WHATSAPP', 'WhatsApp'),
    ])
    sent_at = models.DateTimeField(auto_now_add=True)
    is_sent = models.BooleanField(default=True)

    def __str__(self):
        return f"Reminder for {self.user.username} - {self.event.title}"

    class Meta:
        unique_together = ('event', 'user', 'reminder_type')


class Calendar(models.Model):
    """Personal or shared calendars"""
    CALENDAR_TYPES = [
        ('PERSONAL', 'Personal'),
        ('COMPANY', 'Company'),
        ('DEPARTMENT', 'Department'),
        ('PROJECT', 'Project'),
        ('SHARED', 'Shared'),
    ]

    name = models.CharField(max_length=100)
    calendar_type = models.CharField(max_length=15, choices=CALENDAR_TYPES, default='PERSONAL')
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#3498db', help_text="Hex color code")

    # Ownership and access
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_calendars')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name='calendars')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True,
                                   related_name='calendars')
    shared_with = models.ManyToManyField(
        User,
        through='CalendarPermission',
        related_name='shared_calendars',
        through_fields=('calendar', 'user')
    )

    # Settings
    is_default = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    time_zone = models.CharField(max_length=50, default='Africa/Johannesburg')

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.owner.username})"

    class Meta:
        unique_together = ('name', 'owner')


class CalendarPermission(models.Model):
    """Permissions for shared calendars"""
    PERMISSION_TYPES = [
        ('VIEW', 'View Only'),
        ('EDIT', 'Can Edit'),
        ('ADMIN', 'Full Admin'),
    ]

    calendar = models.ForeignKey('Calendar', on_delete=models.CASCADE, related_name='user_permissions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calendar_permissions')
    permission = models.CharField(max_length=10, choices=PERMISSION_TYPES, default='VIEW')

    # Define permission types
    can_edit = models.BooleanField(default=False)
    can_view = models.BooleanField(default=True)

    granted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='granted_permissions')
    granted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.calendar.name} ({self.permission})"

    class Meta:
        unique_together = ('calendar', 'user')


class EventAttachment(models.Model):
    """File attachments for events"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='event_attachments/%Y/%m/')
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.filename} - {self.event.title}"

    def save(self, *args, **kwargs):
        if self.file:
            self.filename = self.file.name
            self.file_size = self.file.size
        super().save(*args, **kwargs)
