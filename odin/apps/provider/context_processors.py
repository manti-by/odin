from odin.apps.provider.models import Traffic


def traffic(request):
    latest = Traffic.objects.order_by("-created_at").first()
    return {"traffic": latest}
