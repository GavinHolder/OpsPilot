# jobs/forms.py
from django import forms
from django.utils import timezone
from .models import (
    Job, JobTask, JobNote, JobAttachment, Location, Team,
    CivilWorker, CivilWorkerAssignment, InventoryUsage
)


class JobForm(forms.ModelForm):
    """Form for creating and editing jobs"""

    # Add fields for creating initial tasks
    tasks = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'One task per line (optional)'}),
        required=False,
        help_text='Enter one task per line'
    )

    # Add date and time pickers for better UX
    scheduled_start_date_field = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label="Scheduled Start Date"
    )
    scheduled_start_time_field = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        required=False,
        label="Scheduled Start Time"
    )

    scheduled_end_date_field = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label="Scheduled End Date"
    )
    scheduled_end_time_field = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        required=False,
        label="Scheduled End Time"
    )

    class Meta:
        model = Job
        fields = [
            'title', 'description', 'job_type', 'priority', 'status',
            'location', 'assigned_team', 'assigned_to', 'requires_civil_team',
            'reference_number', 'tags', 'estimated_cost'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'tags': forms.TextInput(attrs={'placeholder': 'Comma-separated tags'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Make job_type and priority required
        self.fields['job_type'].required = True
        self.fields['priority'].required = True

        # If editing an existing job
        if self.instance.pk:
            # Set initial values for date/time fields
            if self.instance.scheduled_start_date:
                self.fields['scheduled_start_date_field'].initial = self.instance.scheduled_start_date.date()
                self.fields['scheduled_start_time_field'].initial = self.instance.scheduled_start_date.time()

            if self.instance.scheduled_end_date:
                self.fields['scheduled_end_date_field'].initial = self.instance.scheduled_end_date.date()
                self.fields['scheduled_end_time_field'].initial = self.instance.scheduled_end_date.time()

    def clean(self):
        cleaned_data = super().clean()

        # Process scheduled start date/time
        start_date = cleaned_data.get('scheduled_start_date_field')
        start_time = cleaned_data.get('scheduled_start_time_field')

        if start_date:
            if start_time:
                scheduled_start = timezone.datetime.combine(start_date, start_time)
                # Make timezone-aware
                scheduled_start = timezone.make_aware(scheduled_start)
                cleaned_data['scheduled_start_date'] = scheduled_start
            else:
                self.add_error('scheduled_start_time_field', 'Please specify a time for the scheduled start')

        # Process scheduled end date/time
        end_date = cleaned_data.get('scheduled_end_date_field')
        end_time = cleaned_data.get('scheduled_end_time_field')

        if end_date:
            if end_time:
                scheduled_end = timezone.datetime.combine(end_date, end_time)
                # Make timezone-aware
                scheduled_end = timezone.make_aware(scheduled_end)
                cleaned_data['scheduled_end_date'] = scheduled_end
            else:
                self.add_error('scheduled_end_time_field', 'Please specify a time for the scheduled end')

        # Validate that end date is after start date
        if 'scheduled_start_date' in cleaned_data and 'scheduled_end_date' in cleaned_data:
            if cleaned_data['scheduled_end_date'] < cleaned_data['scheduled_start_date']:
                self.add_error('scheduled_end_date_field', 'End date must be after start date')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Set the created_by field if creating a new job
        if not instance.pk and self.user:
            instance.created_by = self.user

        # Set the scheduled dates from the cleaned data
        if 'scheduled_start_date' in self.cleaned_data:
            instance.scheduled_start_date = self.cleaned_data['scheduled_start_date']

        if 'scheduled_end_date' in self.cleaned_data:
            instance.scheduled_end_date = self.cleaned_data['scheduled_end_date']

        if commit:
            instance.save()

            # Handle tasks (if provided)
            if self.cleaned_data.get('tasks'):
                task_lines = self.cleaned_data['tasks'].strip().split('\n')
                for i, task_text in enumerate(task_lines):
                    if task_text.strip():
                        JobTask.objects.create(
                            job=instance,
                            description=task_text.strip(),
                            order=i
                        )

        return instance


class JobTaskForm(forms.ModelForm):
    """Form for creating job tasks"""

    class Meta:
        model = JobTask
        fields = ['description', 'is_completed']


class JobNoteForm(forms.ModelForm):
    """Form for adding notes to a job"""

    class Meta:
        model = JobNote
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Add a note...'}),
        }


class JobAttachmentForm(forms.ModelForm):
    """Form for uploading attachments to a job"""

    class Meta:
        model = JobAttachment
        fields = ['file', 'description']

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


class CivilWorkerAssignmentForm(forms.ModelForm):
    """Form for assigning civil workers to jobs"""

    class Meta:
        model = CivilWorkerAssignment
        fields = ['worker', 'start_date', 'end_date', 'daily_rate', 'notes']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Only show active workers
        self.fields['worker'].queryset = CivilWorker.objects.filter(is_active=True)

        # If this is an existing assignment, set the daily rate from the worker
        if not self.instance.pk and 'worker' in self.data:
            try:
                worker_id = int(self.data.get('worker'))
                worker = CivilWorker.objects.get(pk=worker_id)
                self.fields['daily_rate'].initial = worker.daily_rate
            except (ValueError, CivilWorker.DoesNotExist):
                pass


class InventoryUsageForm(forms.ModelForm):
    """Form for recording inventory usage on a job"""

    class Meta:
        model = InventoryUsage
        fields = ['item_name', 'quantity', 'unit_cost', 'company', 'notes']


class JobFilterForm(forms.Form):
    """Form for filtering jobs"""
    STATUS_CHOICES = [('', 'All Statuses')] + list(Job.STATUS_CHOICES)

    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False)
    job_type = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="All Job Types"
    )
    priority = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="All Priorities"
    )
    assigned_team = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="All Teams"
    )
    location = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="All Locations"
    )
    search = forms.CharField(required=False)
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    requires_civil_team = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import JobType, JobPriority, Team, Location

        # Set querysets for dynamic fields
        self.fields['job_type'].queryset = JobType.objects.all()
        self.fields['priority'].queryset = JobPriority.objects.all()
        self.fields['assigned_team'].queryset = Team.objects.filter(is_active=True)
        self.fields['location'].queryset = Location.objects.all()


class LocationForm(forms.ModelForm):
    """Form for creating and editing locations"""

    class Meta:
        model = Location
        fields = [
            'name', 'address', 'city', 'coordinates', 'location_type', 'notes',
            'tower_height', 'tower_id', 'is_fiber_connected', 'fiber_termination_type'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }


class TeamForm(forms.ModelForm):
    """Form for creating and editing teams"""

    class Meta:
        model = Team
        fields = ['name', 'description', 'team_type', 'team_lead', 'members', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'members': forms.SelectMultiple(attrs={'size': 10}),
        }


class CivilWorkerForm(forms.ModelForm):
    """Form for creating and editing civil workers"""

    class Meta:
        model = CivilWorker
        fields = ['first_name', 'last_name', 'id_number', 'phone_number', 'daily_rate', 'is_active', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
