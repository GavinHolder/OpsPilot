from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from threading import Thread


# Define a function to send emails in a separate thread
def send_email_async(subject, message, from_email, recipient_list):
    """Send email asynchronously in a separate thread"""
    thread = Thread(
        target=send_mail,
        args=(subject, message, from_email, recipient_list),
        kwargs={'fail_silently': False}
    )
    thread.daemon = True  # Thread will close when main thread closes
    thread.start()


# Example signal for user registration
@receiver(post_save, sender=User)
def user_created(sender, instance, created, **kwargs):
    """Send welcome email when a new user is created"""
    if created:
        subject = 'Welcome to OpsPilot'
        message = f'Hi {instance.username},\n\nWelcome to OpsPilot - your personal WISP/FNO operations management system!\n\nRegards,\nOpsPilot Team'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [instance.email]

        # Send email asynchronously
        send_email_async(subject, message, from_email, recipient_list)