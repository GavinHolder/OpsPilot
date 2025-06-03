from django import forms
from django.utils import timezone
from .models import Task, Subtask, TaskComment, TaskAttachment, TaskVoiceNote


class TaskForm(forms.ModelForm):
    """Form for creating and editing tasks"""

    # Add a field for creating initial subtasks
    subtasks = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'One subtask per line (optional)'}),
        required=False,
        help_text='Enter one subtask per line'
    )

    # Add date picker and time picker for better UX
    deadline_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    deadline_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        required=False
    )

    class Meta:
        model = Task
        fields = [
            'title', 'description', 'priority', 'category',
            'company', 'assigned_to', 'tags',
            'related_job', 'related_tower',
            'reminder_enabled'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'tags': forms.TextInput(attrs={'placeholder': 'Comma-separated tags'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # If editing an existing task with a deadline
        if self.instance.pk and self.instance.deadline:
            self.fields['deadline_date'].initial = self.instance.deadline.date()
            self.fields['deadline_time'].initial = self.instance.deadline.time()

    def clean(self):
        cleaned_data = super().clean()
        deadline_date = cleaned_data.get('deadline_date')
        deadline_time = cleaned_data.get('deadline_time')

        # If either date or time is provided, make sure both are provided
        if deadline_date and not deadline_time:
            # Default to end of day if no time specified
            deadline_time = forms.TimeField().clean('23:59')
            cleaned_data['deadline_time'] = deadline_time

        # Combine date and time into deadline datetime
        if deadline_date:
            if deadline_time:
                deadline = timezone.datetime.combine(deadline_date, deadline_time)
                # Make timezone-aware
                deadline = timezone.make_aware(deadline)
                cleaned_data['deadline'] = deadline
            else:
                self.add_error('deadline_time', 'Please specify a time for the deadline')

        # Set reminder datetime to 1 day before deadline by default
        if cleaned_data.get('reminder_enabled') and cleaned_data.get('deadline'):
            reminder_datetime = cleaned_data['deadline'] - timezone.timedelta(days=1)
            cleaned_data['reminder_datetime'] = reminder_datetime

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Set the created_by field if creating a new task
        if not instance.pk and self.user:
            instance.created_by = self.user

        # Set the deadline from the cleaned data
        if 'deadline' in self.cleaned_data:
            instance.deadline = self.cleaned_data['deadline']

        # Set the reminder datetime
        if instance.reminder_enabled and instance.deadline:
            instance.reminder_datetime = instance.deadline - timezone.timedelta(days=1)

        if commit:
            instance.save()

            # Handle subtasks (if provided)
            if self.cleaned_data.get('subtasks'):
                subtask_lines = self.cleaned_data['subtasks'].strip().split('\n')
                for i, subtask_text in enumerate(subtask_lines):
                    if subtask_text.strip():
                        Subtask.objects.create(
                            task=instance,
                            description=subtask_text.strip(),
                            order=i
                        )

        return instance


class SubtaskForm(forms.ModelForm):
    """Form for creating subtasks"""

    class Meta:
        model = Subtask
        fields = ['description', 'is_completed']


class TaskCommentForm(forms.ModelForm):
    """Form for adding comments to a task"""

    class Meta:
        model = TaskComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Add a comment...'}),
        }


class TaskAttachmentForm(forms.ModelForm):
    """Form for uploading attachments to a task"""

    class Meta:
        model = TaskAttachment
        fields = ['file']

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Set file metadata
        if instance.file:
            instance.file_name = instance.file.name
            instance.file_size = instance.file.size
            instance.file_type = instance.file.content_type

        if commit:
            instance.save()

        return instance


class TaskFilterForm(forms.Form):
    """Form for filtering tasks"""
    STATUS_CHOICES = [('', 'All Statuses')] + list(Task.STATUS_CHOICES)
    COMPANY_CHOICES = [('', 'All Companies')] + list(Task.COMPANY_CHOICES)

    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False)
    priority = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="All Priorities"
    )
    category = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="All Categories"
    )
    company = forms.ChoiceField(choices=COMPANY_CHOICES, required=False)
    search = forms.CharField(required=False)
    overdue = forms.BooleanField(required=False)
    due_today = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import TaskPriority, TaskCategory

        # Set querysets for dynamic fields
        self.fields['priority'].queryset = TaskPriority.objects.all()
        self.fields['category'].queryset = TaskCategory.objects.all()


class VoiceNoteForm(forms.ModelForm):
    """Form for uploading voice notes"""

    class Meta:
        model = TaskVoiceNote
        fields = ['audio_file', 'duration']