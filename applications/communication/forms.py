from django import forms
from django.contrib.auth.models import User
from .models import (
    ChatRoom, Message, MessageReaction, Announcement,
    ExternalIntegration, MessageTemplate
)
from applications.accounts.models import Department

class ChatRoomForm(forms.ModelForm):
    class Meta:
        model = ChatRoom
        fields = ['name', 'room_type', 'description', 'is_private', 'allow_file_sharing', 'department']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # If user has a department, pre-select it
        if self.user and hasattr(self.user, 'userprofile') and self.user.userprofile.department:
            self.fields['department'].initial = self.user.userprofile.department

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content', 'file_attachment', 'message_type']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Type your message...',
                'class': 'message-input'
            }),
            'message_type': forms.HiddenInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content')
        file_attachment = cleaned_data.get('file_attachment')

        # Require either content or file attachment
        if not content and not file_attachment:
            raise forms.ValidationError("Please provide either a message or an attachment.")

        # Set message type based on presence of file attachment
        if file_attachment and not content:
            cleaned_data['message_type'] = 'FILE'

        return cleaned_data

class ReactionForm(forms.ModelForm):
    class Meta:
        model = MessageReaction
        fields = ['reaction']
        widgets = {
            'reaction': forms.Select(attrs={'class': 'reaction-selector'}),
        }

class AnnouncementForm(forms.ModelForm):
    target_all_departments = forms.BooleanField(required=False, initial=False)

    class Meta:
        model = Announcement
        fields = [
            'title', 'content', 'announcement_type', 'priority',
            'target_all_users', 'target_departments', 'target_users',
            'attachment', 'is_published', 'publish_at', 'expires_at',
            'send_email', 'send_whatsapp', 'send_telegram'
        ]
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5}),
            'publish_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'expires_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'target_departments': forms.SelectMultiple(attrs={'class': 'select2 form-control'}),
            'target_users': forms.SelectMultiple(attrs={'class': 'select2 form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # If user has company access, show all departments
        if self.user and hasattr(self.user, 'userprofile') and self.user.userprofile.company:
            company = self.user.userprofile.company
            self.fields['target_departments'].queryset = Department.objects.filter(company=company)
            self.fields['target_users'].queryset = User.objects.filter(
                userprofile__company=company
            ).order_by('username')
        else:
            # Limit to user's department
            if self.user and hasattr(self.user, 'userprofile') and self.user.userprofile.department:
                dept = self.user.userprofile.department
                self.fields['target_departments'].queryset = Department.objects.filter(id=dept.id)
                self.fields['target_users'].queryset = User.objects.filter(
                    userprofile__department=dept
                ).order_by('username')

    def clean(self):
        cleaned_data = super().clean()
        target_all_users = cleaned_data.get('target_all_users')
        target_departments = cleaned_data.get('target_departments')
        target_users = cleaned_data.get('target_users')
        target_all_departments = cleaned_data.get('target_all_departments')

        # If targeting all users, no need to select departments or users
        if target_all_users:
            cleaned_data['target_departments'] = Department.objects.none()
            cleaned_data['target_users'] = User.objects.none()
        # If targeting all departments, select all departments
        elif target_all_departments:
            if self.user and hasattr(self.user, 'userprofile') and self.user.userprofile.company:
                company = self.user.userprofile.company
                cleaned_data['target_departments'] = Department.objects.filter(company=company)
        # Otherwise, require either departments or users
        elif not target_departments and not target_users:
            raise forms.ValidationError(
                "Please select target departments, users, or choose to target all users."
            )

        return cleaned_data

class ExternalIntegrationForm(forms.ModelForm):
    class Meta:
        model = ExternalIntegration
        fields = [
            'name', 'platform_type', 'api_token', 'webhook_url',
            'bot_username', 'is_active', 'auto_sync', 'rate_limit_per_minute'
        ]
        widgets = {
            'api_token': forms.PasswordInput(render_value=True),
        }

class MessageTemplateForm(forms.ModelForm):
    class Meta:
        model = MessageTemplate
        fields = ['name', 'template_type', 'subject', 'content', 'variables', 'is_active']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5}),
            'variables': forms.Textarea(attrs={'rows': 3}),
        }