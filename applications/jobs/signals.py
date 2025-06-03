from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from threading import Thread
from .models import Job, JobNote, JobAttachment, JobStatusUpdate, CivilWorkerAssignment


def send_email_async(subject, message, from_email, recipient_list):
    """Send email asynchronously in a separate thread"""
    thread = Thread(
        target=send_mail,
        args=(subject, message, from_email, recipient_list),
        kwargs={'fail_silently': False}
    )
    thread.daemon = True  # Thread will close when main thread closes
    thread.start()


@receiver(post_save, sender=Job)
def job_created_or_updated(sender, instance, created, **kwargs):
    """Handle job creation and updates"""
    if created:
        # Job was just created
        subject = f'New Job: {instance.title}'
        message = f"""
        A new job has been created:

        Title: {instance.title}
        Type: {instance.job_type}
        Priority: {instance.priority}
        Location: {instance.location}
        Scheduled: {instance.scheduled_start_date}

        Click here to view the job: {settings.SITE_URL}{instance.get_absolute_url()}
        """

        # If assigned to a team, notify team lead
        if instance.assigned_team and instance.assigned_team.team_lead:
            if instance.assigned_team.team_lead.email:
                send_email_async(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [instance.assigned_team.team_lead.email]
                )

        # If assigned to an individual, notify them
        if instance.assigned_to and instance.assigned_to.email:
            send_email_async(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [instance.assigned_to.email]
            )
    else:
        # Job was updated
        # Check if assigned_team or assigned_to was changed
        if kwargs.get('update_fields'):
            if 'assigned_team' in kwargs['update_fields']:
                # Notify new team lead
                if instance.assigned_team and instance.assigned_team.team_lead:
                    if instance.assigned_team.team_lead.email:
                        subject = f'Job Assigned: {instance.title}'
                        message = f"""
                        A job has been assigned to your team:

                        Title: {instance.title}
                        Type: {instance.job_type}
                        Priority: {instance.priority}
                        Location: {instance.location}
                        Scheduled: {instance.scheduled_start_date}

                        Click here to view the job: {settings.SITE_URL}{instance.get_absolute_url()}
                        """

                        send_email_async(
                            subject,
                            message,
                            settings.DEFAULT_FROM_EMAIL,
                            [instance.assigned_team.team_lead.email]
                        )

            if 'assigned_to' in kwargs['update_fields']:
                # Notify the newly assigned user
                if instance.assigned_to and instance.assigned_to.email:
                    subject = f'Job Assigned: {instance.title}'
                    message = f"""
                    A job has been assigned to you:

                    Title: {instance.title}
                    Type: {instance.job_type}
                    Priority: {instance.priority}
                    Location: {instance.location}
                    Scheduled: {instance.scheduled_start_date}

                    Click here to view the job: {settings.SITE_URL}{instance.get_absolute_url()}
                    """

                    send_email_async(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [instance.assigned_to.email]
                    )


@receiver(post_save, sender=JobNote)
def job_note_added(sender, instance, created, **kwargs):
    """Notify when a note is added to a job"""
    if created:
        job = instance.job

        # Notify job creator and assignees if they're different from the note author
        recipients = set()

        if job.created_by and job.created_by.email and job.created_by != instance.author:
            recipients.add(job.created_by.email)

        if job.assigned_to and job.assigned_to.email and job.assigned_to != instance.author:
            recipients.add(job.assigned_to.email)

        # Also notify team lead if different from author
        if job.assigned_team and job.assigned_team.team_lead and job.assigned_team.team_lead != instance.author:
            if job.assigned_team.team_lead.email:
                recipients.add(job.assigned_team.team_lead.email)

        if recipients:
            subject = f'New Note on Job: {job.title}'
            message = f"""
            {instance.author} added a note to a job:

            Job: {job.title}
            Note: {instance.content}

            Click here to view the job: {settings.SITE_URL}{job.get_absolute_url()}
            """

            send_email_async(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                list(recipients)
            )


@receiver(post_save, sender=JobAttachment)
def job_attachment_added(sender, instance, created, **kwargs):
    """Notify when an attachment is added to a job"""
    if created:
        job = instance.job

        # Notify job creator and assignees if they're different from the uploader
        recipients = set()

        if job.created_by and job.created_by.email and job.created_by != instance.uploaded_by:
            recipients.add(job.created_by.email)

        if job.assigned_to and job.assigned_to.email and job.assigned_to != instance.uploaded_by:
            recipients.add(job.assigned_to.email)

        # Also notify team lead if different from uploader
        if job.assigned_team and job.assigned_team.team_lead and job.assigned_team.team_lead != instance.uploaded_by:
            if job.assigned_team.team_lead.email:
                recipients.add(job.assigned_team.team_lead.email)

        if recipients:
            subject = f'New Attachment on Job: {job.title}'
            message = f"""
            {instance.uploaded_by} added an attachment to a job:

            Job: {job.title}
            File: {instance.file_name} ({instance.file_size} bytes)
            Description: {instance.description or "No description provided"}

            Click here to view the job: {settings.SITE_URL}{job.get_absolute_url()}
            """

            send_email_async(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                list(recipients)
            )


@receiver(post_save, sender=JobStatusUpdate)
def job_status_changed(sender, instance, created, **kwargs):
    """Notify when a job status changes"""
    if created:
        job = instance.job

        # Notify job creator, assigned team lead, and assigned individual
        recipients = set()

        if job.created_by and job.created_by.email and job.created_by != instance.updated_by:
            recipients.add(job.created_by.email)

        if job.assigned_to and job.assigned_to.email and job.assigned_to != instance.updated_by:
            recipients.add(job.assigned_to.email)

        # Also notify team lead if different from updater
        if job.assigned_team and job.assigned_team.team_lead and job.assigned_team.team_lead != instance.updated_by:
            if job.assigned_team.team_lead.email:
                recipients.add(job.assigned_team.team_lead.email)

        if recipients:
            subject = f'Job Status Change: {job.title}'
            message = f"""
            The status of a job has been updated:

            Job: {job.title}
            Old Status: {instance.get_old_status_display()}
            New Status: {instance.get_new_status_display()}
            Updated By: {instance.updated_by}
            Notes: {instance.notes or "No notes provided"}

            Click here to view the job: {settings.SITE_URL}{job.get_absolute_url()}
            """

            send_email_async(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                list(recipients)
            )


@receiver(post_save, sender=CivilWorkerAssignment)
def civil_worker_assigned(sender, instance, created, **kwargs):
    """Notify when a civil worker is assigned to a job"""
    if created:
        job = instance.job

        # Notify job creator, assigned team lead, and assigned individual
        recipients = set()

        if job.created_by and job.created_by.email:
            recipients.add(job.created_by.email)

        if job.assigned_to and job.assigned_to.email:
            recipients.add(job.assigned_to.email)

        # Also notify team lead
        if job.assigned_team and job.assigned_team.team_lead and job.assigned_team.team_lead.email:
            recipients.add(job.assigned_team.team_lead.email)

        if recipients:
            subject = f'Civil Worker Assigned: {job.title}'
            message = f"""
            A civil worker has been assigned to a job:

            Job: {job.title}
            Worker: {instance.worker}
            Start Date: {instance.start_date}
            Daily Rate: R{instance.daily_rate}

            Click here to view the job: {settings.SITE_URL}{job.get_absolute_url()}
            """

            send_email_async(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                list(recipients)
            )