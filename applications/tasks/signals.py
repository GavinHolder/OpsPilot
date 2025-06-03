from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from threading import Thread
from .models import Task, TaskComment, TaskAttachment, TaskVoiceNote


def send_email_async(subject, message, from_email, recipient_list):
    """Send email asynchronously in a separate thread"""
    thread = Thread(
        target=send_mail,
        args=(subject, message, from_email, recipient_list),
        kwargs={'fail_silently': False}
    )
    thread.daemon = True  # Thread will close when main thread closes
    thread.start()


@receiver(post_save, sender=Task)
def task_created_or_updated(sender, instance, created, **kwargs):
    """Handle task creation and updates"""
    if created:
        # Task was just created
        subject = f'New Task: {instance.title}'
        message = f"""
        A new task has been assigned to you:

        Title: {instance.title}
        Description: {instance.description}
        Priority: {instance.priority}
        Deadline: {instance.deadline}

        Click here to view the task: {settings.SITE_URL}{instance.get_absolute_url()}
        """

        # If assigned to someone, notify them
        if instance.assigned_to and instance.assigned_to.email:
            send_email_async(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [instance.assigned_to.email]
            )
    else:
        # Task was updated
        # Check if the assigned_to field was changed
        if kwargs.get('update_fields') and 'assigned_to' in kwargs['update_fields']:
            # Notify the newly assigned user
            if instance.assigned_to and instance.assigned_to.email:
                subject = f'Task Assigned: {instance.title}'
                message = f"""
                A task has been assigned to you:

                Title: {instance.title}
                Description: {instance.description}
                Priority: {instance.priority}
                Deadline: {instance.deadline}

                Click here to view the task: {settings.SITE_URL}{instance.get_absolute_url()}
                """

                send_email_async(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [instance.assigned_to.email]
                )


@receiver(post_save, sender=TaskComment)
def task_comment_added(sender, instance, created, **kwargs):
    """Notify when a comment is added to a task"""
    if created:
        task = instance.task

        # Notify task owner and assignee if they're different from the commenter
        recipients = set()

        if task.created_by and task.created_by.email and task.created_by != instance.author:
            recipients.add(task.created_by.email)

        if task.assigned_to and task.assigned_to.email and task.assigned_to != instance.author:
            recipients.add(task.assigned_to.email)

        if recipients:
            subject = f'New Comment on Task: {task.title}'
            message = f"""
            {instance.author} commented on a task:

            Task: {task.title}
            Comment: {instance.content}

            Click here to view the task: {settings.SITE_URL}{task.get_absolute_url()}
            """

            send_email_async(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                list(recipients)
            )


@receiver(post_save, sender=TaskAttachment)
def task_attachment_added(sender, instance, created, **kwargs):
    """Notify when an attachment is added to a task"""
    if created:
        task = instance.task

        # Notify task owner and assignee if they're different from the uploader
        recipients = set()

        if task.created_by and task.created_by.email and task.created_by != instance.uploaded_by:
            recipients.add(task.created_by.email)

        if task.assigned_to and task.assigned_to.email and task.assigned_to != instance.uploaded_by:
            recipients.add(task.assigned_to.email)

        if recipients:
            subject = f'New Attachment on Task: {task.title}'
            message = f"""
            {instance.uploaded_by} added an attachment to a task:

            Task: {task.title}
            File: {instance.file_name} ({instance.file_size} bytes)

            Click here to view the task: {settings.SITE_URL}{task.get_absolute_url()}
            """

            send_email_async(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                list(recipients)
            )


# Celery task for checking upcoming task deadlines (to be added)
def check_task_deadlines():
    """Check for upcoming deadlines and send reminders"""
    # Find tasks with reminders enabled that haven't been sent yet
    tasks_to_remind = Task.objects.filter(
        reminder_enabled=True,
        reminder_sent=False,
        status__in=['pending', 'in_progress'],
        reminder_datetime__lte=timezone.now()
    )

    for task in tasks_to_remind:
        # Send reminder
        if task.assigned_to and task.assigned_to.email:
            subject = f'Reminder: Task "{task.title}" is due soon'
            message = f"""
            This is a reminder that the following task is due soon:

            Title: {task.title}
            Deadline: {task.deadline}

            Click here to view the task: {settings.SITE_URL}{task.get_absolute_url()}
            """

            send_email_async(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [task.assigned_to.email]
            )

        # Mark reminder as sent
        task.reminder_sent = True
        task.save(update_fields=['reminder_sent'])