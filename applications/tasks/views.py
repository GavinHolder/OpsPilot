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
    Task, Subtask, TaskCategory, TaskPriority,
    TaskAttachment, TaskComment, TaskVoiceNote
)
from .forms import (
    TaskForm, SubtaskForm, TaskCommentForm,
    TaskAttachmentForm, TaskFilterForm, VoiceNoteForm
)


@method_decorator(login_required, name='dispatch')
class TaskListView(ListView):
    """View for listing tasks with filtering"""
    model = Task
    template_name = 'tasks/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 20

    def get_queryset(self):
        queryset = Task.objects.all()

        # Apply filters from form
        form = TaskFilterForm(self.request.GET)
        if form.is_valid():
            data = form.cleaned_data

            # Filter by status
            if data.get('status'):
                queryset = queryset.filter(status=data['status'])

            # Filter by priority
            if data.get('priority'):
                queryset = queryset.filter(priority=data['priority'])

            # Filter by category
            if data.get('category'):
                queryset = queryset.filter(category=data['category'])

            # Filter by company
            if data.get('company'):
                queryset = queryset.filter(company=data['company'])

            # Search in title, description, tags
            if data.get('search'):
                search_term = data['search']
                queryset = queryset.filter(
                    Q(title__icontains=search_term) |
                    Q(description__icontains=search_term) |
                    Q(tags__icontains=search_term)
                )

            # Filter overdue tasks
            if data.get('overdue'):
                today = timezone.now().date()
                queryset = queryset.filter(
                    deadline__date__lt=today,
                    status__in=['pending', 'in_progress']
                )

            # Filter tasks due today
            if data.get('due_today'):
                today = timezone.now().date()
                queryset = queryset.filter(deadline__date=today)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = TaskFilterForm(self.request.GET)

        # Add counts for different task statuses
        context['pending_count'] = Task.objects.filter(status='pending').count()
        context['in_progress_count'] = Task.objects.filter(status='in_progress').count()
        context['completed_count'] = Task.objects.filter(status='completed').count()

        # Add today's tasks
        today = timezone.now().date()
        context['today_tasks'] = Task.objects.filter(
            deadline__date=today,
            status__in=['pending', 'in_progress']
        )

        # Add overdue tasks
        context['overdue_tasks'] = Task.objects.filter(
            deadline__date__lt=today,
            status__in=['pending', 'in_progress']
        )

        return context


@method_decorator(login_required, name='dispatch')
class TaskDetailView(DetailView):
    """View for viewing task details"""
    model = Task
    template_name = 'tasks/task_detail.html'
    context_object_name = 'task'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['subtasks'] = self.object.subtasks.all()
        context['attachments'] = self.object.attachments.all()
        context['comments'] = self.object.comments.all()
        context['voice_notes'] = self.object.voice_notes.all()

        # Forms for adding new elements
        context['comment_form'] = TaskCommentForm()
        context['attachment_form'] = TaskAttachmentForm()
        context['subtask_form'] = SubtaskForm()
        context['voice_note_form'] = VoiceNoteForm()

        return context


@method_decorator(login_required, name='dispatch')
class TaskCreateView(CreateView):
    """View for creating new tasks"""
    model = Task
    form_class = TaskForm
    template_name = 'tasks/task_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Task created successfully!')
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class TaskUpdateView(UpdateView):
    """View for updating tasks"""
    model = Task
    form_class = TaskForm
    template_name = 'tasks/task_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Task updated successfully!')
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class TaskDeleteView(DeleteView):
    """View for deleting tasks"""
    model = Task
    template_name = 'tasks/task_confirm_delete.html'
    success_url = reverse_lazy('tasks:task_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Task deleted successfully!')
        return super().delete(request, *args, **kwargs)


@login_required
@require_POST
def add_comment(request, pk):
    """Add a comment to a task"""
    task = get_object_or_404(Task, pk=pk)
    form = TaskCommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.task = task
        comment.author = request.user
        comment.save()

        if request.headers.get('HX-Request'):
            # Return HTML for HTMX to update the comments section
            return render(
                request,
                'tasks/partials/comment_item.html',
                {'comment': comment}
            )

        messages.success(request, 'Comment added successfully!')
        return redirect('tasks:task_detail', pk=task.pk)

    # If form invalid
    if request.headers.get('HX-Request'):
        return HttpResponse(status=400)

    messages.error(request, 'Error adding comment!')
    return redirect('tasks:task_detail', pk=task.pk)


@login_required
@require_POST
def add_attachment(request, pk):
    """Add an attachment to a task"""
    task = get_object_or_404(Task, pk=pk)
    form = TaskAttachmentForm(request.POST, request.FILES)

    if form.is_valid():
        attachment = form.save(commit=False)
        attachment.task = task
        attachment.uploaded_by = request.user
        attachment.save()

        if request.headers.get('HX-Request'):
            # Return HTML for HTMX to update the attachments section
            return render(
                request,
                'tasks/partials/attachment_item.html',
                {'attachment': attachment}
            )

        messages.success(request, 'Attachment added successfully!')
        return redirect('tasks:task_detail', pk=task.pk)

    # If form invalid
    if request.headers.get('HX-Request'):
        return HttpResponse(status=400)

    messages.error(request, 'Error adding attachment!')
    return redirect('tasks:task_detail', pk=task.pk)


@login_required
@require_POST
def add_subtask(request, pk):
    """Add a subtask to a task"""
    task = get_object_or_404(Task, pk=pk)
    form = SubtaskForm(request.POST)

    if form.is_valid():
        subtask = form.save(commit=False)
        subtask.task = task
        # Set order to be after the last subtask
        max_order = task.subtasks.aggregate(models.Max('order'))['order__max'] or 0
        subtask.order = max_order + 1
        subtask.save()

        if request.headers.get('HX-Request'):
            # Return HTML for HTMX to update the subtasks section
            return render(
                request,
                'tasks/partials/subtask_item.html',
                {'subtask': subtask}
            )

        messages.success(request, 'Subtask added successfully!')
        return redirect('tasks:task_detail', pk=task.pk)

    # If form invalid
    if request.headers.get('HX-Request'):
        return HttpResponse(status=400)

    messages.error(request, 'Error adding subtask!')
    return redirect('tasks:task_detail', pk=task.pk)


@login_required
@require_POST
def toggle_subtask(request, pk):
    """Toggle the completion status of a subtask"""
    subtask = get_object_or_404(Subtask, pk=pk)

    # Toggle completion status
    subtask.is_completed = not subtask.is_completed

    if subtask.is_completed:
        subtask.completed_at = timezone.now()
    else:
        subtask.completed_at = None

    subtask.save()

    if request.headers.get('HX-Request'):
        # Return updated HTML for HTMX
        return render(
            request,
            'tasks/partials/subtask_item.html',
            {'subtask': subtask}
        )

    return redirect('tasks:task_detail', pk=subtask.task.pk)


@login_required
@require_POST
def mark_task_completed(request, pk):
    """Mark a task as completed"""
    task = get_object_or_404(Task, pk=pk)
    task.mark_completed()

    if request.headers.get('HX-Request'):
        # Return updated HTML for HTMX
        return render(
            request,
            'tasks/partials/task_status.html',
            {'task': task}
        )

    messages.success(request, 'Task marked as completed!')
    return redirect('tasks:task_detail', pk=task.pk)


@login_required
@require_POST
def add_voice_note(request, pk):
    """Add a voice note to a task"""
    task = get_object_or_404(Task, pk=pk)
    form = VoiceNoteForm(request.POST, request.FILES)

    if form.is_valid():
        voice_note = form.save(commit=False)
        voice_note.task = task
        voice_note.recorded_by = request.user
        voice_note.save()

        # Here you would typically process the voice note for transcription
        # This would be handled by a background task using Celery

        if request.headers.get('HX-Request'):
            # Return HTML for HTMX to update the voice notes section
            return render(
                request,
                'tasks/partials/voice_note_item.html',
                {'voice_note': voice_note}
            )

        messages.success(request, 'Voice note added successfully!')
        return redirect('tasks:task_detail', pk=task.pk)

    # If form invalid
    if request.headers.get('HX-Request'):
        return HttpResponse(status=400)

    messages.error(request, 'Error adding voice note!')
    return redirect('tasks:task_detail', pk=task.pk)


@login_required
def task_calendar(request):
    """View tasks in a calendar format"""
    # This view will show tasks with deadlines in a calendar
    return render(request, 'tasks/task_calendar.html')


@login_required
def task_board(request):
    """View tasks in a kanban board format"""
    # Group tasks by status in a kanban-style board
    pending_tasks = Task.objects.filter(status='pending')
    in_progress_tasks = Task.objects.filter(status='in_progress')
    completed_tasks = Task.objects.filter(
        status='completed',
        completed_at__gte=timezone.now() - timezone.timedelta(days=7)
    )

    context = {
        'pending_tasks': pending_tasks,
        'in_progress_tasks': in_progress_tasks,
        'completed_tasks': completed_tasks,
    }

    return render(request, 'tasks/task_board.html', context)


@login_required
def quick_add_task(request):
    """Add a task quickly via modal or mobile UI"""
    if request.method == 'POST':
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            task = form.save()

            if request.headers.get('HX-Request'):
                # Return JSON for HTMX
                return JsonResponse({
                    'success': True,
                    'task_id': task.pk,
                    'message': 'Task created successfully!'
                })

            messages.success(request, 'Task created successfully!')
            return redirect('tasks:task_detail', pk=task.pk)
    else:
        form = TaskForm(user=request.user)

    context = {
        'form': form,
        'is_quick_add': True
    }

    if request.headers.get('HX-Request'):
        return render(request, 'tasks/partials/quick_add_form.html', context)

    return render(request, 'tasks/quick_add.html', context)


@login_required
def voice_to_task(request):
    """Convert voice note to task using speech-to-text"""
    # This would be implemented with JS for recording and then 
    # processing the audio on the server
    return render(request, 'tasks/voice_to_task.html')
