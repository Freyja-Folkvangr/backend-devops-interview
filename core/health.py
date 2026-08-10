from django.db import connection
from django.http import HttpRequest, JsonResponse


def live(request: HttpRequest) -> JsonResponse:
    """Liveness: the process is up. No dependency checks, so an orchestrator
    never restarts a healthy app just because a dependency blipped."""
    return JsonResponse({"status": "ok"})


def ready(request: HttpRequest) -> JsonResponse:
    """Readiness: the app can serve traffic (its database is reachable)."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ready"})
