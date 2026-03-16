from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.test import RequestFactory

from core.views_analytics import accumulation
from core.views_top_exposures import top_exposures
from core.views_net import net_of_treaty
from core.views_scenario import scenario_stress
from core.views_data_quality import portfolio_data_quality
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from core.serializers import ToolExecuteRequestSerializer

TOOLS_SCHEMA = {
    "version": "1.0",
    "tools": [
        {
            "name": "accumulation",
            "description": "Compute accumulation / concentration metrics for a portfolio with optional filters and grouping.",
            "method": "GET",
            "endpoint": "/v1/analytics/accumulation",
            "input_schema": {
                "type": "object",
                "properties": {
                    "portfolio_id": {"type": "integer"},
                    "group_by": {
                        "type": "string",
                        "enum": ["country", "region", "lob", "peril"],
                        "default": "country",
                    },
                    "lob": {"type": "string"},
                    "peril": {"type": "string"},
                    "country": {"type": "string"},
                    "region": {"type": "string"},
                    "top_n": {"type": "integer", "default": 10},
                },
                "required": ["portfolio_id"],
            },
            "output_schema": {"type": "object"},
        },
        {
            "name": "top_exposures",
            "description": "Return the largest exposures in a portfolio ranked by tiv or premium.",
            "method": "GET",
            "endpoint": "/v1/analytics/top-exposures",
            "input_schema": {
                "type": "object",
                "properties": {
                    "portfolio_id": {"type": "integer"},
                    "by": {"type": "string", "enum": ["tiv", "premium"], "default": "tiv"},
                    "limit": {"type": "integer", "default": 50},
                    "country": {"type": "string"},
                    "lob": {"type": "string"},
                    "peril": {"type": "string"},
                },
                "required": ["portfolio_id"],
            },
            "output_schema": {"type": "object"},
        },
        {
            "name": "net_of_treaty",
            "description": "Compute gross, ceded, and net exposure for a portfolio under a selected treaty (QS or XOL).",
            "method": "GET",
            "endpoint": "/v1/analytics/net",
            "input_schema": {
                "type": "object",
                "properties": {
                    "portfolio_id": {"type": "integer"},
                    "treaty_id": {"type": "integer"},
                    "group_by": {
                        "type": "string",
                        "enum": ["country", "region", "lob", "peril"],
                    },
                },
                "required": ["portfolio_id", "treaty_id"],
            },
            "output_schema": {"type": "object"},
        },
        {
            "name": "scenario_stress",
            "description": "Apply one or more stress scenarios to portfolio exposures and compare baseline vs stressed gross/net values.",
            "method": "POST",
            "endpoint": "/v1/analytics/scenario",
            "input_schema": {
                "type": "object",
                "properties": {
                    "portfolio_id": {"type": "integer"},
                    "treaty_id": {"type": "integer"},
                    "base_filters": {"type": "object"},
                    "group_by": {
                        "type": "string",
                        "enum": ["country", "region", "lob", "peril"],
                    },
                    "stresses": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "filters": {"type": "object"},
                                "tiv_factor": {"type": "number"},
                            },
                            "required": ["name", "tiv_factor"],
                        },
                    },
                },
                "required": ["portfolio_id", "stresses"],
            },
            "output_schema": {"type": "object"},
        },
        {
            "name": "data_quality",
            "description": "Return a data quality summary for a portfolio including missing fields, duplicates, outliers, and distributions.",
            "method": "GET",
            "endpoint": "/v1/portfolios/{portfolio_id}/data-quality",
            "input_schema": {
                "type": "object",
                "properties": {
                    "portfolio_id": {"type": "integer"},
                },
                "required": ["portfolio_id"],
            },
            "output_schema": {"type": "object"},
        },
    ],
}


def _tool_bad_request(message: str, details: dict | None = None):
    payload = {"error": {"code": "bad_request", "message": message}}
    if details:
        payload["error"]["details"] = details
    return Response(payload, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    tags=["Tools"],
    operation_id="tools_schema",
    summary="List available tools",
    description=(
        "Return the list of agent-callable tools with their method, endpoint, "
        "input schema, and output schema."
    ),
    responses={
        200: OpenApiResponse(
            description="Tool schema returned successfully.",
            examples=[
                OpenApiExample(
                    "Tools schema example",
                    value={
                        "version": "1.0",
                        "tools": [
                            {
                                "name": "accumulation",
                                "description": "Compute accumulation / concentration metrics for a portfolio.",
                                "method": "GET",
                                "endpoint": "/v1/analytics/accumulation",
                                "input_schema": {"type": "object"},
                                "output_schema": {"type": "object"},
                            }
                        ],
                    },
                )
            ],
        )
    },
)

@api_view(["GET"])
def tools_schema(request):
    return Response(TOOLS_SCHEMA)

@extend_schema(
    tags=["Tools"],
    operation_id="tools_execute",
    summary="Execute a tool",
    description=(
        "Execute one of the registered tools through a uniform interface. "
        "This is intended for agent or orchestration use-cases."
    ),
    request=ToolExecuteRequestSerializer,
    examples=[
        OpenApiExample(
            "Execute accumulation tool",
            request_only=True,
            value={
                "tool": "accumulation",
                "input": {
                    "portfolio_id": 1,
                    "group_by": "country"
                },
            },
        )
    ],
    responses={
        200: OpenApiResponse(description="Tool executed successfully."),
        400: OpenApiResponse(description="Invalid tool request."),
        404: OpenApiResponse(description="Unknown tool."),
    },
)

@api_view(["POST"])
def tools_execute(request):
    body = request.data or {}
    tool = body.get("tool")
    tool_input = body.get("input") or {}

    if not tool:
        return _tool_bad_request("Missing 'tool'")
    if not isinstance(tool_input, dict):
        return _tool_bad_request("'input' must be an object")

    def make_get_request(params):
        factory = RequestFactory()
        fake = factory.get("/", params)
        fake.META["HTTP_X_API_KEY"] = request.META.get("HTTP_X_API_KEY", "")
        return fake

    if tool == "accumulation":
        return accumulation(make_get_request(tool_input))

    if tool == "top_exposures":
        return top_exposures(make_get_request(tool_input))

    if tool == "net_of_treaty":
        return net_of_treaty(make_get_request(tool_input))

    if tool == "scenario_stress":
        request._full_data = tool_input
        return scenario_stress(request)

    if tool == "data_quality":
        portfolio_id = tool_input.get("portfolio_id")
        if portfolio_id is None:
            return _tool_bad_request("data_quality requires portfolio_id")
        fake = make_get_request({})
        return portfolio_data_quality(fake, int(portfolio_id))

    return Response(
        {"error": {"code": "unknown_tool", "message": f"Unknown tool '{tool}'"}},
        status=status.HTTP_404_NOT_FOUND,
    )
