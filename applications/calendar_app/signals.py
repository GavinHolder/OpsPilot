from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from datetime import timedelta
import threading

from .models import Event, EventAttendee, EventReminder, Calendar
from applications.notifications.models import Notification


class EmailThread(threading.Thread):
    """Send emails in separate thread to avoid blocking main thread"""

    def __init__(self, subject, message, recipient_list, html_message=None):
        self.subject = subject
        self.message = message
        self.recipient_list = recipient_list
        self.html_message = html_message
        threading.Thread.__init__(self)

    def run(self):
        try:
            send_mail(
                self.subject,
                self.message,
                settings.DEFAULT_FROM_EMAIL,
                self.recipient_list,
                html_message=self.html_message,
                fail_silently=True
            )
        except Exception as e:
            print(f"Failed to send email: {e}")


@receiver(post_save, sender=Event)
def event_created_notification(sender, instance, created, **kwargs):
    """Send notifications when event is created or updated"""
    if not created:
        return

    # Create in-app notifications for attendees
    attendees = EventAttendee.objects.filter(event=instance).select_related('user')

    for attendee in attendees:
        if attendee.user != instance.created_by:  # Don't notify creator
            # Create in-app notification
            Notification.objects.create(
                user=attendee.user,
                title=f"New Event Invitation: {instance.title}",
                message=f"You've been invited to '{instance.title}' on {instance.start_datetime.strftime('%Y-%m-%d %H:%M')}",
                notification_type='EVENT_INVITATION',
                related_object_type='event',
                related_object_id=instance.id,
                priority='MEDIUM'
            )

            # Send email notification if user has email notifications enabled
            if hasattr(attendee.user, 'profile') and attendee.user.profile.email_notifications:
                context = {
                    'event': instance,
                    'attendee': attendee,
                    'user': attendee.user,
                }

                html_message = render_to_string('calendar_app/emails/event_invitation.html', context)
                plain_message = render_to_string('calendar_app/emails/event_invitation.txt', context)

                EmailThread(
                    subject=f"Event Invitation: {instance.title}",
                    message=plain_message,
                    recipient_list=[attendee.user.email],
                    html_message=html_message
                ).start()


@receiver(post_save, sender=EventAttendee)
def attendee_rsvp_notification(sender, instance, created, **kwargs):
    """Notify event creator when attendee responds to invitation"""
    if not created and instance.status != 'PENDING':
        # Notify event creator about RSVP response
        if instance.event.created_by != instance.user:
            Notification.objects.create(
                user=instance.event.created_by,
                title=f"RSVP Response: {instance.event.title}",
                message=f"{instance.user.get_full_name() or instance.user.username} {instance.get_status_display().lower()} your event invitation",
                notification_type='EVENT_RSVP',
                related_object_type='event',
                related_object_id=instance.event.id,
                priority='LOW'
            )


@receiver(pre_save, sender=Event)
def event_update_notification(sender, instance, **kwargs):
    """Send notifications when event is updated"""
    if instance.pk:  # Only for existing events
        try:
            old_instance = Event.objects.get(pk=instance.pk)

            # Check if important details changed
            important_changes = []
            if old_instance.start_datetime != instance.start_datetime:
                important_changes.append(
                    f"Start time changed from {old_instance.start_datetime.strftime('%Y-%m-%d %H:%M')} to {instance.start_datetime.strftime('%Y-%m-%d %H:%M')}")

            if old_instance.location != instance.location:
                important_changes.append(f"Location changed from '{old_instance.location}' to '{instance.location}'")

            if old_instance.title != instance.title:
                important_changes.append(f"Title changed from '{old_instance.title}' to '{instance.title}'")

            # If there are important changes, notify attendees
            if important_changes:
                attendees = EventAttendee.objects.filter(event=instance).select_related('user')
                changes_text = "; ".join(important_changes)

                for attendee in attendees:
                    if attendee.user != instance.created_by:  # Don't notify creator
                        Notification.objects.create(
                            user=attendee.user,
                            title=f"Event Updated: {instance.title}",
                            message=f"Event details have been updated: {changes_text}",
                            notification_type='EVENT_UPDATE',
                            related_object_type='event',
                            related_object_id=instance.id,
                            priority='MEDIUM'
                        )

                        # Send email if enabled
                        if hasattr(attendee.user, 'profile') and attendee.user.profile.email_notifications:
                            context = {
                                'event': instance,
                                'changes': important_changes,
                                'user': attendee.user,
                            }

                            html_message = render_to_string('calendar_app/emails/event_update.html', context)
                            plain_message = render_to_string('calendar_app/emails/event_update.txt', context)

                            EmailThread(
                                subject=f"Event Updated: {instance.title}",
                                message=plain_message,
                                recipient_list=[attendee.user.email],
                                html_message=html_message
                            ).start()

        except Event.DoesNotExist:
            pass


@receiver(post_delete, sender=Event)
def event_deleted_notification(sender, instance, **kwargs):
    """Send notifications when event is deleted"""
    attendees = EventAttendee.objects.filter(event=instance).select_related('user')

    for attendee in attendees:
        if attendee.user != instance.created_by:  # Don't notify creator
            Notification.objects.create(
                user=attendee.user,
                title=f"Event Cancelled: {instance.title}",
                message=f"The event '{instance.title}' scheduled for {instance.start_datetime.strftime('%Y-%m-%d %H:%M')} has been cancelled",
                notification_type='EVENT_CANCELLED',
                priority='MEDIUM'
            )

            # Send email if enabled
            if hasattr(attendee.user, 'profile') and attendee.user.profile.email_notifications:
                context = {
                    'event': instance,
                    'user': attendee.user,
                }

                html_message = render_to_string('calendar_app/emails/event_cancelled.html', context)
                plain_message = render_to_string('calendar_app/emails/event_cancelled.txt', context)

                EmailThread(
                    subject=f"Event Cancelled: {instance.title}",
                    message=plain_message,
                    recipient_list=[attendee.user.email],
                    html_message=html_message
                ).start()


@receiver(post_save, sender=User)
def create_default_calendar(sender, instance, created, **kwargs):
    """Create default personal calendar for new users"""
    if created:
        Calendar.objects.create(
            name=f"{instance.username}'s Calendar",
            calendar_type='PERSONAL',
            owner=instance,
            is_default=True,
            color='#3498db',
            description='Personal calendar'
        )


def send_event_reminders():
    """
    Celery task to send event reminders
    This function should be called by Celery beat scheduler
    """
    from celery import shared_task

    @shared_task
    def process_reminders():
        now = timezone.now()

        # Get events that need reminders in the next hour
        upcoming_events = Event.objects.filter(
            start_datetime__gte=now,
            start_datetime__lte=now + timedelta(hours=1),
            send_reminders=True,
            is_cancelled=False
        ).select_related('category', 'created_by')

        for event in upcoming_events:
            reminder_time = event.start_datetime - timedelta(minutes=event.reminder_minutes)

            # Check if it's time to send reminder (within 5 minutes window)
            if abs((now - reminder_time).total_seconds()) <= 300:  # 5 minutes window
                attendees = EventAttendee.objects.filter(
                    event=event,
                    status__in=['ACCEPTED', 'TENTATIVE']
                ).select_related('user')

                for attendee in attendees:
                    # Check if reminder already sent
                    if not EventReminder.objects.filter(
                            event=event,
                            user=attendee.user,
                            reminder_type='EMAIL'
                    ).exists():

                        # Create in-app notification
                        Notification.objects.create(
                            user=attendee.user,
                            title=f"Event Reminder: {event.title}",
                            message=f"Event starting in {event.reminder_minutes} minutes at {event.location}",
                            notification_type='EVENT_REMINDER',
                            related_object_type='event',
                            related_object_id=event.id,
                            priority='HIGH'
                        )

                        # Send email reminder if enabled
                        if hasattr(attendee.user, 'profile') and attendee.user.profile.email_notifications:
                            context = {
                                'event': event,
                                'user': attendee.user,
                                'reminder_minutes': event.reminder_minutes,
                            }

                            html_message = render_to_string('calendar_app/emails/event_reminder.html', context)
                            plain_message = render_to_string('calendar_app/emails/event_reminder.txt', context)

                            EmailThread(
                                subject=f"Reminder: {event.title}",
                                message=plain_message,
                                recipient_list=[attendee.user.email],
                                html_message=html_message
                            ).start()

                            # Mark reminder as sent
                            EventReminder.objects.create(
                                event=event,
                                user=attendee.user,
                                reminder_type='EMAIL'
                            )

    return process_reminders
