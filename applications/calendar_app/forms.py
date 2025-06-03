from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    Event, EventCategory, EventAttendee, Calendar,
    CalendarPermission, EventAttachment
)
from applications.accounts.models import Company, Department
from applications.tasks.models import Task
from applications.jobs.models import Job


class EventForm(forms.ModelForm):
    """Form for creating and editing events"""

    attendees = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select users to invite to this event"
    )

    class Meta:
        model = Event
        fields = [
            'title', 'description', 'category', 'start_datetime', 'end_datetime',
            'all_day', 'location', 'priority', 'is_private', 'recurrence_type',
            'recurrence_interval', 'recurrence_end_date', 'linked_task', 'linked_job',
            'send_reminders', 'reminder_minutes', 'attendees'
        ]
        widgets = {
            'start_datetime': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                }
            ),
            'end_datetime': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                }
            ),
            'recurrence_end_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            ),
            'description': forms.Textarea(
                attrs={
                    'rows': 4,
                    'class': 'form-control'
                }
            ),
            'title': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter event title'
                }
            ),
            'location': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter location'
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Filter attendees to users in same company or department
        if self.user and hasattr(self.user, 'profile'):
            if self.user.profile.department:
                # Users in same department
                self.fields['attendees'].queryset = User.objects.filter(
                    profile__department=self.user.profile.department,
                    is_active=True
                ).exclude(pk=self.user.pk)
            elif self.user.profile.department and self.user.profile.department.company:
                # Users in same company
                self.fields['attendees'].queryset = User.objects.filter(
                    profile__department__company=self.user.profile.department.company,
                    is_active=True
                ).exclude(pk=self.user.pk)
            else:
                # All active users
                self.fields['attendees'].queryset = User.objects.filter(
                    is_active=True
                ).exclude(pk=self.user.pk)

        # Filter categories by user's company
        if self.user and hasattr(self.user, 'profile') and self.user.profile.department:
            company = self.user.profile.department.company
            self.fields['category'].queryset = EventCategory.objects.filter(
                models.Q(company=company) | models.Q(company__isnull=True),
                is_active=True
            )

        # Filter linked tasks and jobs
        if self.user:
            self.fields['linked_task'].queryset = Task.objects.filter(
                models.Q(assigned_to=self.user) | models.Q(created_by=self.user),
                status__in=['PENDING', 'IN_PROGRESS']
            )
            self.fields['linked_job'].queryset = Job.objects.filter(
                models.Q(assigned_team__members=self.user) | models.Q(created_by=self.user),
                status__in=['PENDING', 'IN_PROGRESS', 'SCHEDULED']
            )

        # Set default start time to next hour
        if not self.instance.pk:
            now = timezone.now()
            next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            self.fields['start_datetime'].initial = next_hour
            self.fields['end_datetime'].initial = next_hour + timedelta(hours=1)

    def clean(self):
        cleaned_data = super().clean()
        start_datetime = cleaned_data.get('start_datetime')
        end_datetime = cleaned_data.get('end_datetime')
        recurrence_type = cleaned_data.get('recurrence_type')
        recurrence_end_date = cleaned_data.get('recurrence_end_date')

        # Validate datetime range
        if start_datetime and end_datetime:
            if end_datetime <= start_datetime:
                raise forms.ValidationError('End time must be after start time.')

        # Validate recurrence
        if recurrence_type and recurrence_type != 'NONE':
            if not recurrence_end_date:
                raise forms.ValidationError('Recurrence end date is required for recurring events.')
            if recurrence_end_date <= start_datetime.date():
                raise forms.ValidationError('Recurrence end date must be after the event start date.')

        return cleaned_data

    def save(self, commit=True):
        event = super().save(commit=commit)

        if commit:
            # Handle attendees
            attendees = self.cleaned_data.get('attendees', [])

            # Remove existing attendees (except organizer)
            EventAttendee.objects.filter(
                event=event,
                is_organizer=False
            ).delete()

            # Add new attendees
            for user in attendees:
                EventAttendee.objects.get_or_create(
                    event=event,
                    user=user,
                    defaults={'status': 'PENDING'}
                )

        return event


class QuickEventForm(forms.Form):
    """Quick event creation form for mobile/HTMX"""
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Event title',
                'autofocus': True
            }
        )
    )
    start_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control'
            }
        ),
        initial=lambda: timezone.now().date()
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(
            attrs={
                'type': 'time',
                'class': 'form-control'
            }
        ),
        initial=lambda: (timezone.now() + timedelta(hours=1)).time()
    )
    duration = forms.ChoiceField(
        choices=[
            (30, '30 minutes'),
            (60, '1 hour'),
            (90, '1.5 hours'),
            (120, '2 hours'),
            (180, '3 hours'),
            (240, '4 hours'),
        ],
        initial=60,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class EventCategoryForm(forms.ModelForm):
    """Form for managing event categories"""

    class Meta:
        model = EventCategory
        fields = ['name', 'event_type', 'color', 'company', 'description']
        widgets = {
            'color': forms.TextInput(
                attrs={
                    'type': 'color',
                    'class': 'form-control form-control-color'
                }
            ),
            'description': forms.Textarea(
                attrs={
                    'rows': 3,
                    'class': 'form-control'
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Filter companies based on user's access
        if self.user and hasattr(self.user, 'profile'):
            if self.user.profile.department:
                self.fields['company'].queryset = Company.objects.filter(
                    pk=self.user.profile.department.company.pk
                )


class CalendarForm(forms.ModelForm):
    """Form for creating and editing calendars"""

    shared_with = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select users to share this calendar with"
    )

    class Meta:
        model = Calendar
        fields = [
            'name', 'calendar_type', 'description', 'color',
            'company', 'department', 'is_public', 'shared_with'
        ]
        widgets = {
            'color': forms.TextInput(
                attrs={
                    'type': 'color',
                    'class': 'form-control form-control-color'
                }
            ),
            'description': forms.Textarea(
                attrs={
                    'rows': 3,
                    'class': 'form-control'
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Filter shared_with users
        if self.user:
            self.fields['shared_with'].queryset = User.objects.filter(
                is_active=True
            ).exclude(pk=self.user.pk)

        # Filter company and department
        if self.user and hasattr(self.user, 'profile'):
            if self.user.profile.department:
                company = self.user.profile.department.company
                self.fields['company'].queryset = Company.objects.filter(pk=company.pk)
                self.fields['department'].queryset = Department.objects.filter(company=company)


class EventAttendeeForm(forms.ModelForm):
    """Form for RSVP responses"""

    class Meta:
        model = EventAttendee
        fields = ['status', 'notes']
        widgets = {
            'notes': forms.Textarea(
                attrs={
                    'rows': 3,
                    'class': 'form-control',
                    'placeholder': 'Optional notes about your attendance'
                }
            ),
        }


class EventAttachmentForm(forms.ModelForm):
    """Form for uploading event attachments"""

    class Meta:
        model = EventAttachment
        fields = ['file', 'description']
        widgets = {
            'description': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'File description (optional)'
                }
            ),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Limit file size to 10MB
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File size cannot exceed 10MB.')

            # Check file extension
            allowed_extensions = [
                '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                '.jpg', '.jpeg', '.png', '.gif', '.txt', '.zip', '.rar'
            ]
            if not any(file.name.lower().endswith(ext) for ext in allowed_extensions):
                raise forms.ValidationError(
                    f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}'
                )

        return file


class CalendarFilterForm(forms.Form):
    """Form for filtering calendar events"""

    category = forms.ModelChoiceField(
        queryset=EventCategory.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    priority = forms.ChoiceField(
        choices=[('', 'All Priorities')] + Event.PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control'
            }
        )
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control'
            }
        )
    )
    my_events_only = forms.BooleanField(
        required=False,
        label="My Events Only",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )