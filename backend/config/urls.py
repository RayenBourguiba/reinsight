from django.contrib import admin
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from core.views import health
from core.views_analytics import accumulation
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.permissions import AllowAny
from core.views_ingestion import (
    canonical_schema,
    upload_file,
    upload_status,
    upload_preview,
    suggest_mapping
)
from core.views_ingestion import apply_mapping
from core.views_exposures import bulk_create_exposures
from core.views_net import net_of_treaty
from core.views_top_exposures import top_exposures
from core.views_scenario import scenario_stress
from core.views_data_quality import portfolio_data_quality
from core.views_tools import tools_schema, tools_execute
from core.views_exposures import bulk_create_exposures, list_exposures, get_exposure

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health),

    path(
        "schema/",
        SpectacularAPIView.as_view(permission_classes=[AllowAny], authentication_classes=[]),
        name="schema",
    ),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[AllowAny], authentication_classes=[]),
        name="swagger-ui",
    ),

    path("v1/analytics/accumulation", accumulation),

    # Schema
    path("v1/schema/canonical", canonical_schema),

    # Ingestion
    path("v1/ingestion/uploads", upload_file),
    path("v1/ingestion/uploads/<uuid:upload_id>", upload_status),
    path("v1/ingestion/uploads/<uuid:upload_id>/preview", upload_preview),
    path("v1/ingestion/uploads/<uuid:upload_id>/suggest-mapping", suggest_mapping),
    path("v1/ingestion/uploads/<uuid:upload_id>/apply-mapping", apply_mapping),

    path("v1/exposures/bulk", bulk_create_exposures),

    path("v1/analytics/net", net_of_treaty),

    path("v1/analytics/top-exposures", top_exposures),

    path("v1/analytics/scenario", scenario_stress),

    path("v1/portfolios/<int:portfolio_id>/data-quality", portfolio_data_quality),

    path("v1/tools/schema", tools_schema),
    path("v1/tools/execute", tools_execute),

    path("v1/exposures", list_exposures),
    path("v1/exposures/<int:exposure_id>", get_exposure),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
