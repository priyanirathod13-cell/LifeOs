from django.http import JsonResponse


def health_check(request):
    """
    Health-check endpoint confirming the LifeOS application is operational.

    Returns:
        JsonResponse with service health status and application identifier.
    """
    return JsonResponse({
        "status": "ok",
        "application": "LifeOS"
    })
