from .models import BusinessRule


def pending_count(request):
    """
    Makes pending_count available in every template.
    This is used to show the badge count on the Approvals link in the navbar.
    """
    if request.user.is_authenticated and request.user.is_superuser:
        count = BusinessRule.objects.filter(status='pending').count()
        return {'pending_count': count}
    return {'pending_count': 0}
