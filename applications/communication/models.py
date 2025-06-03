from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from datetime import datetime, timedelta
import uuid


class ChatRoom(models.Model):
    """Chat rooms for team communication"""
    ROOM_TYPES = [
        ('GENERAL', 'General Chat'),
        ('DEPARTMENT', 'Department Chat'),
        ('PROJECT', 'Project Chat'),
        ('PRIVATE', 'Private Chat'),
        ('SUPPORT', 'Support Chat'),
        ('EMERGENCY', 'Emergency Chat'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='GENERAL')
    description = models.TextField(blank=True)

    # Participants
    members = models.ManyToManyField(User, through='ChatRoomMembership', related_name='chat_rooms')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_chat_rooms')

    # Room settings
    is_private = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    allow_file_sharing = models.BooleanField(default=True)
    max_members = models.PositiveIntegerField(default=50)

    # Linked items
    linked_task = models.ForeignKey('tasks.Task', on_delete=models.SET_NULL, null=True, blank=True)
    linked_job = models.ForeignKey('jobs.Job', on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey('accounts.Department', on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.name} ({self.get_room_type_display()})"

    def get_absolute_url(self):
        return reverse('communication:chat_room', kwargs={'room_id': self.id})

    @property
    def last_message(self):
        return self.messages.order_by('-created_at').first()

    @property
    def unread_count_for_user(self, user):
        if not hasattr(self, '_unread_count'):
            membership = self.chatroommembership_set.filter(user=user).first()
            if membership:
                return self.messages.filter(
                    created_at__gt=membership.last_read_at or membership.joined_at
                ).count()
        return 0


class ChatRoomMembership(models.Model):
    """Membership details for chat rooms"""
    MEMBER_ROLES = [
        ('MEMBER', 'Member'),
        ('MODERATOR', 'Moderator'),
        ('ADMIN', 'Admin'),
    ]

    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=MEMBER_ROLES, default='MEMBER')

    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)
    is_muted = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)

    class Meta:
        unique_together = ('room', 'user')

    def __str__(self):
        return f"{self.user.username} in {self.room.name}"


class Message(models.Model):
    """Messages in chat rooms"""
    MESSAGE_TYPES = [
        ('TEXT', 'Text Message'),
        ('FILE', 'File Attachment'),
        ('IMAGE', 'Image'),
        ('VOICE', 'Voice Message'),
        ('LOCATION', 'Location Share'),
        ('SYSTEM', 'System Message'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')

    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='TEXT')
    content = models.TextField()

    # File attachments
    file_attachment = models.FileField(upload_to='chat_files/', null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)

    # Message metadata
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)

    # External integration
    whatsapp_message_id = models.CharField(max_length=100, blank=True)
    telegram_message_id = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.username} in {self.room.name}"

    def get_content_preview(self, max_length=50):
        if self.is_deleted:
            return "🗑️ This message was deleted"
        if self.message_type == 'FILE':
            return f"📎 {self.file_name or 'File attachment'}"
        if self.message_type == 'IMAGE':
            return f"🖼️ Image"
        if self.message_type == 'VOICE':
            return f"🎵 Voice message"
        if self.message_type == 'LOCATION':
            return f"📍 Location shared"

        content = self.content[:max_length]
        return content + '...' if len(self.content) > max_length else content

    @property
    def file_size_display(self):
        if self.file_size:
            if self.file_size < 1024:
                return f"{self.file_size} B"
            elif self.file_size < 1024 * 1024:
                return f"{self.file_size / 1024:.1f} KB"
            else:
                return f"{self.file_size / (1024 * 1024):.1f} MB"
        return ""


class MessageReaction(models.Model):
    """Reactions to messages (emoji responses)"""
    REACTION_TYPES = [
        ('👍', 'Thumbs Up'),
        ('👎', 'Thumbs Down'),
        ('❤️', 'Heart'),
        ('😂', 'Laugh'),
        ('😮', 'Wow'),
        ('😢', 'Sad'),
        ('😡', 'Angry'),
        ('🎉', 'Celebrate'),
        ('✅', 'Check'),
        ('❌', 'Cross'),
    ]

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction = models.CharField(max_length=10, choices=REACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user', 'reaction')

    def __str__(self):
        return f"{self.reaction} by {self.user.username}"


class Announcement(models.Model):
    """Company-wide or department announcements"""
    ANNOUNCEMENT_TYPES = [
        ('GENERAL', 'General Announcement'),
        ('URGENT', 'Urgent Notice'),
        ('MAINTENANCE', 'Maintenance Notice'),
        ('POLICY', 'Policy Update'),
        ('EVENT', 'Event Announcement'),
        ('SYSTEM', 'System Update'),
    ]

    PRIORITY_LEVELS = [
        ('LOW', 'Low Priority'),
        ('MEDIUM', 'Medium Priority'),
        ('HIGH', 'High Priority'),
        ('URGENT', 'Urgent'),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    announcement_type = models.CharField(max_length=20, choices=ANNOUNCEMENT_TYPES, default='GENERAL')
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='MEDIUM')

    # Targeting
    target_all_users = models.BooleanField(default=True)
    target_departments = models.ManyToManyField('accounts.Department', blank=True, related_name='announcements')
    target_users = models.ManyToManyField(User, blank=True, related_name='targeted_announcements')

    # Attachments
    attachment = models.FileField(upload_to='announcements/', null=True, blank=True)

    # Publishing
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_announcements')
    is_published = models.BooleanField(default=False)
    publish_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # External sharing
    send_email = models.BooleanField(default=False)
    send_whatsapp = models.BooleanField(default=False)
    send_telegram = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_priority_display()})"

    def get_absolute_url(self):
        return reverse('communication:announcement_detail', kwargs={'pk': self.pk})

    @property
    def is_active(self):
        now = timezone.now()
        if not self.is_published:
            return False
        if self.publish_at and self.publish_at > now:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        return True

    def get_target_users(self):
        """Get all users that should receive this announcement"""
        if self.target_all_users:
            return User.objects.filter(is_active=True)

        users = set()

        # Add specifically targeted users
        users.update(self.target_users.filter(is_active=True))

        # Add users from targeted departments
        for department in self.target_departments.all():
            users.update(department.staff.filter(user__is_active=True).values_list('user', flat=True))

        return User.objects.filter(pk__in=[u.pk if hasattr(u, 'pk') else u for u in users])


class AnnouncementRead(models.Model):
    """Track which users have read announcements"""
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='read_by')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('announcement', 'user')

    def __str__(self):
        return f"{self.user.username} read {self.announcement.title}"


class ExternalIntegration(models.Model):
    """External communication platform integrations"""
    PLATFORM_TYPES = [
        ('WHATSAPP', 'WhatsApp Business'),
        ('TELEGRAM', 'Telegram Bot'),
        ('SLACK', 'Slack'),
        ('TEAMS', 'Microsoft Teams'),
        ('EMAIL', 'Email Service'),
    ]

    name = models.CharField(max_length=100)
    platform_type = models.CharField(max_length=20, choices=PLATFORM_TYPES)

    # Configuration
    api_token = models.CharField(max_length=500, blank=True)
    webhook_url = models.URLField(blank=True)
    bot_username = models.CharField(max_length=100, blank=True)

    # Settings
    is_active = models.BooleanField(default=False)
    auto_sync = models.BooleanField(default=False)

    # Rate limiting
    rate_limit_per_minute = models.PositiveIntegerField(default=60)
    last_sync = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_platform_type_display()})"


class ExternalMessage(models.Model):
    """Messages received from external platforms"""
    integration = models.ForeignKey(ExternalIntegration, on_delete=models.CASCADE, related_name='messages')
    external_id = models.CharField(max_length=100)
    sender_identifier = models.CharField(max_length=100)  # Phone number, username, etc.
    sender_name = models.CharField(max_length=100, blank=True)

    content = models.TextField()
    message_type = models.CharField(max_length=20, default='TEXT')

    # Linking to internal system
    linked_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    linked_chat_room = models.ForeignKey(ChatRoom, on_delete=models.SET_NULL, null=True, blank=True)

    # Processing status
    is_processed = models.BooleanField(default=False)
    response_sent = models.BooleanField(default=False)

    received_at = models.DateTimeField()
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-received_at']
        unique_together = ('integration', 'external_id')

    def __str__(self):
        return f"Message from {self.sender_name or self.sender_identifier}"


class MessageTemplate(models.Model):
    """Reusable message templates"""
    TEMPLATE_TYPES = [
        ('WELCOME', 'Welcome Message'),
        ('NOTIFICATION', 'Notification Template'),
        ('REMINDER', 'Reminder Template'),
        ('ANNOUNCEMENT', 'Announcement Template'),
        ('SUPPORT', 'Support Response'),
        ('EMERGENCY', 'Emergency Alert'),
    ]

    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    subject = models.CharField(max_length=200, blank=True)
    content = models.TextField()

    # Template variables (JSON format)
    variables = models.JSONField(default=dict, blank=True)

    # Usage tracking
    usage_count = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"

    def render_content(self, context=None):
        """Render template with context variables"""
        if not context:
            context = {}

        content = self.content
        for key, value in context.items():
            content = content.replace(f"{{{key}}}", str(value))

        return content


class CommunicationLog(models.Model):
    """Log of all communication activities"""
    LOG_TYPES = [
        ('MESSAGE_SENT', 'Message Sent'),
        ('MESSAGE_RECEIVED', 'Message Received'),
        ('ANNOUNCEMENT_PUBLISHED', 'Announcement Published'),
        ('EXTERNAL_SYNC', 'External Platform Sync'),
        ('TEMPLATE_USED', 'Template Used'),
        ('USER_JOINED', 'User Joined Room'),
        ('USER_LEFT', 'User Left Room'),
    ]

    log_type = models.CharField(max_length=30, choices=LOG_TYPES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=500)

    # Related objects
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.ForeignKey(Message, on_delete=models.SET_NULL, null=True, blank=True)
    announcement = models.ForeignKey(Announcement, on_delete=models.SET_NULL, null=True, blank=True)

    # Additional data
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_log_type_display()} - {self.description}"