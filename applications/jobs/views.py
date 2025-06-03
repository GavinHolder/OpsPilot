# jobs/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Q
from django.contrib import messages

from .models import (
    Job, JobTask, JobNote, JobAttachment, Location, Team,
    CivilWorker, CivilWorkerAssignment, InventoryUsage, JobStatusUpdate
)
from .forms import (
    JobForm, JobTaskForm, JobNoteForm, JobAttachmentForm,
    CivilWorkerAssignmentForm, InventoryUsageForm, JobFilterForm,
    LocationForm, TeamForm, CivilWorkerForm
)


@method_decorator(login_required, name='dispatch')
class JobListView(ListView):
    """View for listing jobs with filtering"""
    model = Job
    template_name = 'jobs/job_list.html'
    context_object_name = 'jobs'
    paginate_by = 20

    def get_queryset(self):
        queryset = Job.objects.all()

        # Apply filters from form
        form = JobFilterForm(self.request.GET)
        if form.is_valid():
            data = form.cleaned_data

            # Filter by status
            if data.get('status'):
                queryset = queryset.filter(status=data['status'])

            # Filter by job type
            if data.get('job_type'):
                queryset = queryset.filter(job_type=data['job_type'])

            # Filter by priority
            if data.get('priority'):
                queryset = queryset.filter(priority=data['priority'])

            # Filter by team
            if data.get('assigned_team'):
                queryset = queryset.filter(assigned_team=data['assigned_team'])

            # Filter by location
            if data.get('location'):
                queryset = queryset.filter(location=data['location'])

            # Search in title, description, reference_number, tags
            if data.get('search'):
                search_term = data['search']
                queryset = queryset.filter(
                    Q(title__icontains=search_term) |
                    Q(description__icontains=search_term) |
                    Q(reference_number__icontains=search_term) |
                    Q(tags__icontains=search_term)
                )

            # Filter by date range
            if data.get('date_from'):
                queryset = queryset.filter(scheduled_start_date__gte=data['date_from'])

            if data.get('date_to'):
                queryset = queryset.filter(scheduled_start_date__lte=data['date_to'])

            # Filter jobs requiring civil team
            if data.get('requires_civil_team'):
                queryset = queryset.filter(requires_civil_team=True)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = JobFilterForm(self.request.GET)

        # Add counts for different job statuses
        context['pending_count'] = Job.objects.filter(status='pending').count()
        context['scheduled_count'] = Job.objects.filter(status='scheduled').count()
        context['in_progress_count'] = Job.objects.filter(status='in_progress').count()
        context['completed_count'] = Job.objects.filter(status='completed').count()

        # Add today's jobs
        today = timezone.now().date()
        context['today_jobs'] = Job.objects.filter(
            scheduled_start_date__date=today,
            status__in=['pending', 'scheduled', 'in_progress']
        )

        # Add upcoming jobs (next 7 days)
        next_week = today + timezone.timedelta(days=7)
        context['upcoming_jobs'] = Job.objects.filter(
            scheduled_start_date__date__gt=today,
            scheduled_start_date__date__lte=next_week,
            status__in=['pending', 'scheduled']
        )

        return context


@method_decorator(login_required, name='dispatch')
class JobDetailView(DetailView):
    """View for viewing job details"""
    model = Job
    template_name = 'jobs/job_detail.html'
    context_object_name = 'job'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['tasks'] = self.object.tasks.all()
        context['notes'] = self.object.notes.all()
        context['attachments'] = self.object.attachments.all()
        context['civil_workers'] = CivilWorkerAssignment.objects.filter(job=self.object)
        context['inventory_usage'] = self.object.inventory_usage.all()
        context['status_updates'] = self.object.status_updates.all()

        # Forms for adding new elements
        context['note_form'] = JobNoteForm()
        context['attachment_form'] = JobAttachmentForm()
        context['task_form'] = JobTaskForm()
        context['civil_worker_form'] = CivilWorkerAssignmentForm()
        context['inventory_form'] = InventoryUsageForm()

        return context


@method_decorator(login_required, name='dispatch')
class JobCreateView(CreateView):
    """View for creating new jobs"""
    model = Job
    form_class = JobForm
    template_name = 'jobs/job_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        # Create job status update for the initial status
        job = form.save()
        JobStatusUpdate.objects.create(
            job=job,
            old_status='',
            new_status=job.status,
            updated_by=self.request.user
        )

        messages.success(self.request, 'Job created successfully!')
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class JobUpdateView(UpdateView):
    """View for updating jobs"""
    model = Job
    form_class = JobForm
    template_name = 'jobs/job_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        # Check if status has changed
        if self.object.status != form.cleaned_data.get('status'):
            # Create job status update
            JobStatusUpdate.objects.create(
                job=self.object,
                old_status=self.object.status,
                new_status=form.cleaned_data.get('status'),
                updated_by=self.request.user
            )

        messages.success(self.request, 'Job updated successfully!')
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class JobDeleteView(DeleteView):
    """View for deleting jobs"""
    model = Job
    template_name = 'jobs/job_confirm_delete.html'
    success_url = reverse_lazy('jobs:job_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Job deleted successfully!')
        return super().delete(request, *args, **kwargs)


@login_required
@require_POST
def add_job_note(request, pk):
    """Add a note to a job"""
    job = get_object_or_404(Job, pk=pk)
    form = JobNoteForm(request.POST)

    if form.is_valid():
        note = form.save(commit=False)
        note.job = job
        note.author = request.user
        note.save()

        if request.headers.get('HX-Request'):
            # Return HTML for HTMX to update the notes section
            return render(
                request,
                'jobs/partials/note_item.html',
                {'note': note}
            )

        messages.success(request, 'Note added successfully!')
        return redirect('jobs:job_detail', pk=job.pk)

    # If form invalid
    if request.headers.get('HX-Request'):
        return HttpResponse(status=400)

    messages.error(request, 'Error adding note!')
    return redirect('jobs:job_detail', pk=job.pk)


@login_required
@require_POST
def add_job_attachment(request, pk):
    """Add an attachment to a job"""
    job = get_object_or_404(Job, pk=pk)
    form = JobAttachmentForm(request.POST, request.FILES)

    if form.is_valid():
        attachment = form.save(commit=False)
        attachment.job = job
        attachment.uploaded_by = request.user
        attachment.save()

        if request.headers.get('HX-Request'):
            # Return HTML for HTMX to update the attachments section
            return render(
                request,
                'jobs/partials/attachment_item.html',
                {'attachment': attachment}
            )

        messages.success(request, 'Attachment added successfully!')
        return redirect('jobs:job_detail', pk=job.pk)

    # If form invalid
    if request.headers.get('HX-Request'):
        return HttpResponse(status=400)

    messages.error(request, 'Error adding attachment!')
    return redirect('jobs:job_detail', pk=job.pk)


@login_required
@require_POST
def add_job_task(request, pk):
    """Add a task to a job"""
    job = get_object_or_404(Job, pk=pk)
    form = JobTaskForm(request.POST)

    if form.is_valid():
        task = form.save(commit=False)
        task.job = job
        # Set order to be after the last task
        max_order = job.tasks.aggregate(models.Max('order'))['order__max'] or 0
        task.order = max_order + 1
        task.save()

        if request.headers.get('HX-Request'):
            # Return HTML for HTMX to update the tasks section
            return render(
                request,
                'jobs/partials/task_item.html',
                {'task': task}
            )

        messages.success(request, 'Task added successfully!')
        return redirect('jobs:job_detail', pk=job.pk)

    # If form invalid
    if request.headers.get('HX-Request'):
        return HttpResponse(status=400)

    messages.error(request, 'Error adding task!')
    return redirect('jobs:job_detail', pk=job.pk)


@login_required
@require_POST
def toggle_job_task(request, task_pk):
    """Toggle the completion status of a job task"""
    task = get_object_or_404(JobTask, pk=task_pk)

    # Toggle completion status
    task.is_completed = not task.is_completed

    if task.is_completed:
        task.completed_at = timezone.now()
        task.completed_by = request.user
    else:
        task.completed_at = None
        task.completed_by = None

    task.save()

    if request.headers.get('HX-Request'):
        # Return updated HTML for HTMX
        return render(
            request,
            'jobs/partials/task_item.html',
            {'task': task}
        )

    return redirect('jobs:job_detail', pk=task.job.pk)


@login_required
@require_POST
def add_civil_worker(request, pk):
    """Add a civil worker to a job"""
    job = get_object_or_404(Job, pk=pk)
    form = CivilWorkerAssignmentForm(request.POST)

    if form.is_valid():
        assignment = form.save(commit=False)
        assignment.job = job
        assignment.save()

        # Update job to require civil team
        if not job.requires_civil_team:
            job.requires_civil_team = True
            job.save()

        if request.headers.get('HX-Request'):
            # Return HTML for HTMX to update the civil workers section
            return render(
                request,
                'jobs/partials/civil_worker_item.html',
                {'assignment': assignment}
            )

        messages.success(request, 'Civil worker assigned successfully!')
        return redirect('jobs:job_detail', pk=job.pk)

    # If form invalid
    if request.headers.get('HX-Request'):
        return HttpResponse(status=400)

    messages.error(request, 'Error assigning civil worker!')
    return redirect('jobs:job_detail', pk=job.pk)


@login_required
@require_POST
def end_civil_worker_assignment(request, assignment_pk):
    """End a civil worker assignment"""
    assignment = get_object_or_404(CivilWorkerAssignment, pk=assignment_pk)

    # Set end date to today if not already set
    if not assignment.end_date:
        assignment.end_date = timezone.now().date()
        assignment.is_active = False
        assignment.save()

    if request.headers.get('HX-Request'):
        # Return updated HTML for HTMX
        return render(
            request,
            'jobs/partials/civil_worker_item.html',
            {'assignment': assignment}
        )

    messages.success(request, 'Civil worker assignment ended!')
    return redirect('jobs:job_detail', pk=assignment.job.pk)


@login_required
@require_POST
def add_inventory_usage(request, pk):
    """Add inventory usage to a job"""
    job = get_object_or_404(Job, pk=pk)
    form = InventoryUsageForm(request.POST)

    if form.is_valid():
        usage = form.save(commit=False)
        usage.job = job
        usage.used_by = request.user
        usage.save()

        if request.headers.get('HX-Request'):
            # Return HTML for HTMX to update the inventory usage section
            return render(
                request,
                'jobs/partials/inventory_item.html',
                {'usage': usage}
            )

        messages.success(request, 'Inventory usage added successfully!')
        return redirect('jobs:job_detail', pk=job.pk)

    # If form invalid
    if request.headers.get('HX-Request'):
        return HttpResponse(status=400)

    messages.error(request, 'Error adding inventory usage!')
    return redirect('jobs:job_detail', pk=job.pk)


@login_required
@require_POST
def mark_job_started(request, pk):
    """Mark a job as started"""
    job = get_object_or_404(Job, pk=pk)

    old_status = job.status
    job.mark_started()

    # Create job status update
    JobStatusUpdate.objects.create(
        job=job,
        old_status=old_status,
        new_status='in_progress',
        updated_by=request.user
    )

    if request.headers.get('HX-Request'):
        # Return updated HTML for HTMX
        return render(
            request,
            'jobs/partials/job_status.html',
            {'job': job}
        )

    messages.success(request, 'Job marked as started!')
    return redirect('jobs:job_detail', pk=job.pk)


@login_required
@require_POST
def mark_job_completed(request, pk):
    """Mark a job as completed"""
    job = get_object_or_404(Job, pk=pk)

    old_status = job.status
    job.mark_completed()

    # Create job status update
    JobStatusUpdate.objects.create(
        job=job,
        old_status=old_status,
        new_status='completed',
        updated_by=request.user,
        notes=f'Job completed by {request.user}'
    )

    if request.headers.get('HX-Request'):
        # Return updated HTML for HTMX
        return render(
            request,
            'jobs/partials/job_status.html',
            {'job': job}
        )

    messages.success(request, 'Job marked as completed!')
    return redirect('jobs:job_detail', pk=job.pk)


@login_required
def job_calendar(request):
    """View jobs in a calendar format"""
    return render(request, 'jobs/job_calendar.html')


@login_required
def job_board(request):
    """View jobs in a kanban board format"""
    pending_jobs = Job.objects.filter(status='pending')
    scheduled_jobs = Job.objects.filter(status='scheduled')
    in_progress_jobs = Job.objects.filter(status='in_progress')
    completed_jobs = Job.objects.filter(
        status='completed',
        actual_end_date__gte=timezone.now() - timezone.timedelta(days=7)
    )

    context = {
        'pending_jobs': pending_jobs,
        'scheduled_jobs': scheduled_jobs,
        'in_progress_jobs': in_progress_jobs,
        'completed_jobs': completed_jobs,
    }

    return render(request, 'jobs/job_board.html', context)


@login_required
def job_map(request):
    """View jobs on a map based on their location coordinates"""
    # Query jobs with valid location data
    jobs = Job.objects.filter(
        Q(location__isnull=False) & ~Q(location__coordinates='')
    ).select_related('location', 'job_type', 'priority', 'assigned_team', 'assigned_to', 'created_by')

    # Count jobs for each status
    job_counts = {
        'total': jobs.count(),
        'pending': jobs.filter(status='pending').count(),
        'scheduled': jobs.filter(status='scheduled').count(),
        'in_progress': jobs.filter(status='in_progress').count(),
        'completed': jobs.filter(status='completed').count(),
    }

    context = {
        'jobs': jobs,
        'job_counts': job_counts,
    }

    return render(request, 'jobs/job_map.html', context)


@login_required
def job_calendar_events(request):
    """API endpoint to provide job events for the calendar"""
    # Get start and end date from query parameters if provided
    start_date = request.GET.get('start', None)
    end_date = request.GET.get('end', None)

    # Query jobs based on date range if provided
    jobs = Job.objects.all()
    if start_date:
        jobs = jobs.filter(scheduled_start_date__gte=start_date)
    if end_date:
        jobs = jobs.filter(scheduled_start_date__lte=end_date)

    # Format jobs as calendar events
    events = []
    for job in jobs:
        # Determine event color based on job status
        events.append({
            'id': job.pk,
            'title': job.title,
            'start': job.scheduled_start_date.isoformat() if job.scheduled_start_date else None,
            'end': job.scheduled_end_date.isoformat() if job.scheduled_end_date else None,
            'extendedProps': {
                'status': job.status,
                'job_type': job.job_type.name if job.job_type else '',
                'priority': job.priority.name if job.priority else '',
                'location': job.location.name if job.location else 'No Location',
                'reference': job.reference_number or ''
            }
        })

    return JsonResponse(events, safe=False)


@login_required
def job_detail_api(request, pk):
    """API endpoint to provide job details for the calendar modal"""
    try:
        job = Job.objects.get(pk=pk)
        data = {
            'title': job.title,
            'status': job.get_status_display(),
            'status_class': job.status,
            'job_type': job.job_type.name if job.job_type else 'N/A',
            'reference_number': job.reference_number or 'N/A',
            'location': job.location.name if job.location else 'No location assigned',
            'priority': job.priority.name if job.priority else 'N/A',
            'team': job.assigned_team.name if job.assigned_team else 'Unassigned',
            'scheduled_date': job.scheduled_start_date.strftime('%Y-%m-%d %H:%M') if job.scheduled_start_date else 'Not scheduled',
            'created_by': job.created_by.get_full_name() if job.created_by else 'Unknown',
            'description': job.description or 'No description provided'
        }
        return JsonResponse(data)
    except Job.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)


# Location Management Views
@method_decorator(login_required, name='dispatch')
class LocationListView(ListView):
    """View for listing locations"""
    model = Location
    template_name = 'jobs/location_list.html'
    context_object_name = 'locations'
    paginate_by = 20


@method_decorator(login_required, name='dispatch')
class LocationDetailView(DetailView):
    """View for viewing location details"""
    model = Location
    template_name = 'jobs/location_detail.html'
    context_object_name = 'location'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get jobs at this location
        context['jobs'] = Job.objects.filter(location=self.object)

        return context


@method_decorator(login_required, name='dispatch')
class LocationCreateView(CreateView):
    """View for creating new locations"""
    model = Location
    form_class = LocationForm
    template_name = 'jobs/location_form.html'
    success_url = reverse_lazy('jobs:location_list')

    def form_valid(self, form):
        messages.success(self.request, 'Location created successfully!')
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class LocationUpdateView(UpdateView):
    """View for updating locations"""
    model = Location
    form_class = LocationForm
    template_name = 'jobs/location_form.html'

    def get_success_url(self):
        return reverse('jobs:location_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Location updated successfully!')
        return super().form_valid(form)


# Team Management Views
@method_decorator(login_required, name='dispatch')
class TeamListView(ListView):
    """View for listing teams"""
    model = Team
    template_name = 'jobs/team_list.html'
    context_object_name = 'teams'


@method_decorator(login_required, name='dispatch')
class TeamDetailView(DetailView):
    """View for viewing team details"""
    model = Team
    template_name = 'jobs/team_detail.html'
    context_object_name = 'team'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get jobs assigned to this team
        context['jobs'] = Job.objects.filter(assigned_team=self.object)

        return context


@method_decorator(login_required, name='dispatch')
class TeamCreateView(CreateView):
    """View for creating new teams"""
    model = Team
    form_class = TeamForm
    template_name = 'jobs/team_form.html'
    success_url = reverse_lazy('jobs:team_list')

    def form_valid(self, form):
        messages.success(self.request, 'Team created successfully!')
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class TeamUpdateView(UpdateView):
    """View for updating teams"""
    model = Team
    form_class = TeamForm
    template_name = 'jobs/team_form.html'

    def get_success_url(self):
        return reverse('jobs:team_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Team updated successfully!')
        return super().form_valid(form)


# Civil Worker Management Views
@method_decorator(login_required, name='dispatch')
class CivilWorkerListView(ListView):
    """View for listing civil workers"""
    model = CivilWorker
    template_name = 'jobs/civil_worker_list.html'
    context_object_name = 'workers'


@method_decorator(login_required, name='dispatch')
class CivilWorkerDetailView(DetailView):
    """View for viewing civil worker details"""
    model = CivilWorker
    template_name = 'jobs/civil_worker_detail.html'
    context_object_name = 'worker'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get assignments for this worker
        context['assignments'] = CivilWorkerAssignment.objects.filter(worker=self.object)

        return context


@method_decorator(login_required, name='dispatch')
class CivilWorkerCreateView(CreateView):
    """View for creating new civil workers"""
    model = CivilWorker
    form_class = CivilWorkerForm
    template_name = 'jobs/civil_worker_form.html'
    success_url = reverse_lazy('jobs:civil_worker_list')

    def form_valid(self, form):
        messages.success(self.request, 'Civil worker created successfully!')
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class CivilWorkerUpdateView(UpdateView):
    """View for updating civil workers"""
    model = CivilWorker
    form_class = CivilWorkerForm
    template_name = 'jobs/civil_worker_form.html'

    def get_success_url(self):
        return reverse('jobs:civil_worker_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Civil worker updated successfully!')
        return super().form_valid(form)
