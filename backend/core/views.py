from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response

@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})