from django.urls import path

from . import views

urlpatterns = [
    path("tasks/", views.TaskListCreateView.as_view(), name="task-list"),
    path("tasks/<int:task_id>/", views.TaskDetailView.as_view(), name="task-detail"),
    path("tasks/<int:task_id>/assign/", views.TaskAssignView.as_view(), name="task-assign"),
    path("tasks/<int:task_id>/complete/", views.TaskCompleteView.as_view(), name="task-complete"),
]
