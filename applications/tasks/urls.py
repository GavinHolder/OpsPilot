from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    # Task list views
    path('', views.TaskListView.as_view(), name='task_list'),
    path('calendar/', views.task_calendar, name='task_calendar'),
    path('board/', views.task_board, name='task_board'),

    # Task CRUD
    path('create/', views.TaskCreateView.as_view(), name='task_create'),
    path('<int:pk>/', views.TaskDetailView.as_view(), name='task_detail'),
    path('<int:pk>/edit/', views.TaskUpdateView.as_view(), name='task_update'),
    path('<int:pk>/delete/', views.TaskDeleteView.as_view(), name='task_delete'),

    # Quick actions
    path('quick-add/', views.quick_add_task, name='quick_add_task'),
    path('voice-to-task/', views.voice_to_task, name='voice_to_task'),

    # Task related actions
    path('<int:pk>/complete/', views.mark_task_completed, name='mark_completed'),
    path('<int:pk>/add-comment/', views.add_comment, name='add_comment'),
    path('<int:pk>/add-attachment/', views.add_attachment, name='add_attachment'),
    path('<int:pk>/add-subtask/', views.add_subtask, name='add_subtask'),
    path('<int:pk>/add-voice-note/', views.add_voice_note, name='add_voice_note'),

    # Subtask actions
    path('subtask/<int:pk>/toggle/', views.toggle_subtask, name='toggle_subtask'),
]