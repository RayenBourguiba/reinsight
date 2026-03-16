from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([AllowAny])
@renderer_classes([JSONRenderer])
def health(request):
    return Response(
        {
            "status": "ok",
            "service": "reinsight-api",
            "version": "1.0.0",
        }
    )