# jobs/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse


class Location(models.Model):
    """Locations where jobs can be performed (towers, customer sites, etc.)"""
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    coordinates = models.CharField(max_length=100, blank=True, help_text="Latitude, Longitude")
    location_type = models.CharField(max_length=50, choices=[
        ('tower', 'Tower Site'),
        ('customer', 'Customer Premises'),
        ('office', 'Office'),
        ('street_cabinet', 'Street Cabinet'),
        ('other', 'Other'),
    ], default='tower')
    notes = models.TextField(blank=True)

    # Tower-specific fields
    tower_height = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True,
                                       help_text="Height in meters")
    tower_id = models.CharField(max_length=50, blank=True, help_text="Tower identifier")

    # FNO-specific fields
    is_fiber_connected = models.BooleanField(default=False)
    fiber_termination_type = models.CharField(max_length=50, blank=True)

    # Common fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'
        ordering = ['name']
        indexes = [
            models.Index(fields=['location_type']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name

    def get_coordinates_tuple(self):
        """Return coordinates as a tuple of (latitude, longitude)"""
        if self.coordinates:
            try:
                lat, lng = self.coordinates.split(',')
                return (float(lat.strip()), float(lng.strip()))
            except (ValueError, TypeError):
                return None
        return None


class JobType(models.Model):
    """Types of jobs that can be performed (installation, maintenance, repair, etc.)"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    estimated_duration = models.PositiveIntegerField(help_text="Estimated duration in minutes", null=True, blank=True)
    company = models.CharField(max_length=10, choices=[
        ('wisp', 'WISP'),
        ('fno', 'FNO'),
        ('both', 'Both'),
    ], default='both')
    requires_civil_team = models.BooleanField(default=False)
    color = models.CharField(max_length=20, default='#3498db')  # Hex color code
    icon = models.CharField(max_length=50, default='fa-tools')  # FontAwesome icon

    class Meta:
        verbose_name = 'Job Type'
        verbose_name_plural = 'Job Types'
        ordering = ['name']

    def __str__(self):
        return self.name


class JobPriority(models.Model):
    """Priority levels for jobs (e.g., Low, Medium, High, Critical)"""
    name = models.CharField(max_length=50)
    value = models.IntegerField(unique=True)  # Numeric value for sorting (1=low, 4=critical)
    color = models.CharField(max_length=20, default='#3498db')  # Hex color code
    icon = models.CharField(max_length=50, default='fa-flag')  # FontAwesome icon

    class Meta:
        verbose_name = 'Job Priority'
        verbose_name_plural = 'Job Priorities'
        ordering = ['-value']

    def __str__(self):
        return self.name


class Team(models.Model):
    """Teams that can be assigned to jobs"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    team_type = models.CharField(max_length=20, choices=[
        ('tower', 'Tower Team'),
        ('fno', 'FNO Team'),
        ('civil', 'Civil Team'),
        ('support', 'Support Team'),
        ('other', 'Other'),
    ])
    team_lead = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='team_lead_of'
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='team_memberships',
        blank=True
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Team'
        verbose_name_plural = 'Teams'
        ordering = ['name']

    def __str__(self):
        return self.name


class CivilWorker(models.Model):
    """Temporary civil workers who can be assigned to jobs"""
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    id_number = models.CharField(max_length=20, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, help_text="Daily rate in Rand")
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Civil Worker'
        verbose_name_plural = 'Civil Workers'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"


class Job(models.Model):
    """Main job model for tracking field work"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    # Basic job information
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    job_type = models.ForeignKey(JobType, on_delete=models.PROTECT)
    priority = models.ForeignKey(JobPriority, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Location information
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)

    # Dates and timing
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    scheduled_start_date = models.DateTimeField(null=True, blank=True)
    scheduled_end_date = models.DateTimeField(null=True, blank=True)
    actual_start_date = models.DateTimeField(null=True, blank=True)
    actual_end_date = models.DateTimeField(null=True, blank=True)

    # Assignment and ownership
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_jobs'
    )
    assigned_team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_jobs'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_jobs'
    )

    # Civil team assignment
    requires_civil_team = models.BooleanField(default=False)
    civil_workers = models.ManyToManyField(
        CivilWorker,
        through='CivilWorkerAssignment',
        related_name='jobs',
        blank=True
    )

    # Financial tracking
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Metadata
    reference_number = models.CharField(max_length=50, blank=True, help_text="External reference number")
    tags = models.CharField(max_length=255, blank=True)  # Comma-separated tags

    class Meta:
        verbose_name = 'Job'
        verbose_name_plural = 'Jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['scheduled_start_date']),
            models.Index(fields=['job_type']),
            models.Index(fields=['assigned_team']),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('jobs:job_detail', kwargs={'pk': self.pk})

    def mark_started(self):
        """Mark a job as started and record the start time"""
        self.status = 'in_progress'
        self.actual_start_date = timezone.now()
        self.save()

    def mark_completed(self):
        """Mark a job as completed and record the completion time"""
        self.status = 'completed'
        self.actual_end_date = timezone.now()
        self.save()

    def get_duration(self):
        """Calculate job duration in hours"""
        if self.actual_start_date and self.actual_end_date:
            delta = self.actual_end_date - self.actual_start_date
            return round(delta.total_seconds() / 3600, 2)  # Convert to hours
        return None

    def is_overdue(self):
        """Check if job is past its scheduled end date"""
        if self.scheduled_end_date and self.status not in ['completed', 'cancelled']:
            return timezone.now() > self.scheduled_end_date
        return False

    def get_progress_percentage(self):
        """Calculate progress percentage based on completed tasks"""
        total_tasks = self.tasks.count()
        if total_tasks == 0:
            return 0
        completed_tasks = self.tasks.filter(is_completed=True).count()
        return int((completed_tasks / total_tasks) * 100)

    def get_tags_list(self):
        """Return tags as a list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',')]
        return []


class CivilWorkerAssignment(models.Model):
    """Assignment of civil workers to jobs with time tracking"""
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    worker = models.ForeignKey(CivilWorker, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, help_text="Daily rate in Rand")
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Civil Worker Assignment'
        verbose_name_plural = 'Civil Worker Assignments'
        ordering = ['job', 'worker', 'start_date']
        unique_together = ['job', 'worker']

    def __str__(self):
        return f"{self.worker} - {self.job}"

    def get_days_worked(self):
        """Calculate the number of days worked"""
        if not self.end_date:
            # If still active, calculate days up to today
            today = timezone.now().date()
            return (today - self.start_date).days + 1
        return (self.end_date - self.start_date).days + 1

    def get_total_cost(self):
        """Calculate the total cost for this worker"""
        return self.get_days_worked() * self.daily_rate


class JobTask(models.Model):
    """Tasks that need to be completed as part of a job"""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='tasks')
    description = models.CharField(max_length=255)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_job_tasks'
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Job Task'
        verbose_name_plural = 'Job Tasks'
        ordering = ['order']

    def __str__(self):
        return self.description

    def mark_completed(self, user=None):
        """Mark a task as completed and record who completed it"""
        self.is_completed = True
        self.completed_at = timezone.now()
        if user:
            self.completed_by = user
        self.save()


class JobNote(models.Model):
    """Notes added to jobs"""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Job Note'
        verbose_name_plural = 'Job Notes'
        ordering = ['-created_at']

    def __str__(self):
        return f"Note on {self.job} by {self.author}"


class JobAttachment(models.Model):
    """File attachments for jobs"""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='job_attachments/%Y/%m/')
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()  # Size in bytes
    file_type = models.CharField(max_length=100)  # MIME type
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Job Attachment'
        verbose_name_plural = 'Job Attachments'
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.file_name


class InventoryUsage(models.Model):
    """Tracking of inventory items used in jobs"""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='inventory_usage')
    item_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    company = models.CharField(max_length=10, choices=[
        ('wisp', 'WISP'),
        ('fno', 'FNO'),
    ], default='wisp')
    used_at = models.DateTimeField(auto_now_add=True)
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Inventory Usage'
        verbose_name_plural = 'Inventory Usage'
        ordering = ['-used_at']

    def __str__(self):
        return f"{self.quantity} x {self.item_name} for {self.job}"

    def get_total_cost(self):
        """Calculate the total cost for this inventory usage"""
        if self.unit_cost:
            return self.quantity * self.unit_cost
        return None


class JobStatusUpdate(models.Model):
    """Status updates and history tracking for jobs"""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='status_updates')
    old_status = models.CharField(max_length=20, choices=Job.STATUS_CHOICES)
    new_status = models.CharField(max_length=20, choices=Job.STATUS_CHOICES)
    updated_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Job Status Update'
        verbose_name_plural = 'Job Status Updates'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.job} - {self.old_status} to {self.new_status}"