import logging

from django.db import DatabaseError, connection
from django.http import HttpRequest, JsonResponse

logger = logging.getLogger(__name__)


def live(request: HttpRequest) -> JsonResponse:
    """Liveness: the process is up. No dependency checks, so an orchestrator
    never restarts a healthy app just because a dependency blipped."""
    return JsonResponse({"status": "ok"})


def ready(request: HttpRequest) -> JsonResponse:
    """Readiness: the app can serve traffic (its database is reachable)."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        logger.exception("Database readiness check failed")
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ready"})
