from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('applications.dashboard.urls')),
    path('tasks/', include('applications.tasks.urls')),
    path('jobs/', include('applications.jobs.urls')),
    path('inventory/', include('applications.inventory.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
