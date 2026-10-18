from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="TaskFlow API",
        default_version="v1",
        description="Task management API. Authenticate via /api/auth/token/ and click "
        "'Authorize' with `Bearer <access>`.",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.tasks.presentation.urls")),
    path("api/docs/", schema_view.with_ui("swagger", cache_timeout=0), name="swagger"),
    path("api/redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="redoc"),
]
