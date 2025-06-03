from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save


class Company(models.Model):
    """Company model to differentiate between WISP and FNO operations"""
    COMPANY_TYPES = [
        ('WISP', 'Wireless Internet Service Provider'),
        ('FNO', 'Fiber Network Operator'),
    ]

    name = models.CharField(max_length=100)
    company_type = models.CharField(max_length=4, choices=COMPANY_TYPES)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.company_type})"

    class Meta:
        verbose_name_plural = "Companies"


class Department(models.Model):
    """Department within a company"""
    name = models.CharField(max_length=100)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='departments')
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.company.name}"


class UserProfile(models.Model):
    """Extended user profile with additional information"""
    USER_ROLES = [
        ('ADMIN', 'Administrator'),
        ('MANAGER', 'Manager'),
        ('TECHNICIAN', 'Technician'),
        ('CIVIL', 'Civil Worker'),
        ('OFFICE', 'Office Staff'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff')
    role = models.CharField(max_length=20, choices=USER_ROLES, default='TECHNICIAN')
    phone_number = models.CharField(max_length=20, blank=True)
    telegram_id = models.CharField(max_length=50, blank=True, help_text="Telegram ID for notifications")
    whatsapp_number = models.CharField(max_length=20, blank=True, help_text="WhatsApp number for notifications")
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    bio = models.TextField(blank=True)

    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    app_notifications = models.BooleanField(default=True)
    telegram_notifications = models.BooleanField(default=False)
    whatsapp_notifications = models.BooleanField(default=False)

    # Daily summary time (for personalized notification timing)
    daily_summary_time = models.TimeField(default='07:00')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

    class Meta:
        permissions = [
            ("view_dashboard", "Can view the dashboard"),
            ("manage_teams", "Can manage teams"),
            ("approve_jobs", "Can approve jobs"),
        ]


class UserSkill(models.Model):
    """Skills that users can have"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class UserSkillAssignment(models.Model):
    """Many-to-many relationship between users and skills with proficiency level"""
    PROFICIENCY_LEVELS = [
        (1, 'Beginner'),
        (2, 'Intermediate'),
        (3, 'Advanced'),
        (4, 'Expert'),
        (5, 'Master'),
    ]

    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='skills')
    skill = models.ForeignKey(UserSkill, on_delete=models.CASCADE, related_name='users')
    proficiency_level = models.IntegerField(choices=PROFICIENCY_LEVELS, default=1)
    years_experience = models.DecimalField(max_digits=4, decimal_places=1, default=0)

    def __str__(self):
        return f"{self.user_profile.user.username} - {self.skill.name} ({self.get_proficiency_level_display()})"

    class Meta:
        unique_together = ('user_profile', 'skill')


class UserLoginLog(models.Model):
    """Track user login activity for security and analytics"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_logs')
    login_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.login_time}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile instance when a User is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile instance when the User is saved"""
    instance.profile.save()