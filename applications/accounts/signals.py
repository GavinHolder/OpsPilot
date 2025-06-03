from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from .models import UserProfile
import threading


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile when a new User is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile when the User is saved"""
    instance.profile.save()


@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    """Send a welcome email when a new user is created"""
    if created and instance.email:
        # Run email sending in a separate thread to avoid blocking
        email_thread = threading.Thread(
            target=send_welcome_email_task,
            args=(instance.email, instance.first_name or instance.username)
        )
        email_thread.daemon = True
        email_thread.start()


def send_welcome_email_task(email, name):
    """Task to send welcome email (runs in a separate thread)"""
    try:
        subject = "Welcome to OpsPilot"
        message = f"""
        Hi {name},
        
        Welcome to OpsPilot - Your personal WISP/FNO task, job & ops brain!
        
        Get started by completing your profile and exploring the dashboard.
        
        Best regards,
        The OpsPilot Team
        """
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@opspilot.com')
        send_mail(subject, message, from_email, [email], fail_silently=True)
    except Exception as e:
        # Log the error but don't crash the application
        print(f"Error sending welcome email: {str(e)}")