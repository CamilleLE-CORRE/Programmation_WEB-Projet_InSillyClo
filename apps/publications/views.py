from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.contenttypes.models import ContentType
from .models import PublicationRequest, PublicationStatus
from .services import approve, reject

@login_required
def admin_requests_list(request):
    # gate: role admin/superuser
    qs = (PublicationRequest.objects
          .select_related("requested_by","team","decided_by","team_validated_by","content_type")
          .filter(status=PublicationStatus.PENDING_ADMIN)
          .order_by("-created_at"))
    return render(request, "publications/admin_requests_list.html", {"requests": qs})

@login_required
def admin_request_detail(request, pk: int):
    req = get_object_or_404(
        PublicationRequest.objects.select_related("requested_by","team","content_type"),
        pk=pk
    )
    target = req.target

    # enrichissement spécifique plasmides : afficher plasmides de la collection
    plasmids = None
    if req.content_type.model == "plasmidcollection":
        # adapte selon votre relation réelle
        plasmids = target.plasmids.all().order_by("id")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "approve":
            approve(req=req, user=request.user)
            return redirect("publications:admin_requests_list")
        if action == "reject":
            reason = request.POST.get("reason", "")
            reject(req=req, user=request.user, reason=reason)
            return redirect("publications:admin_requests_list")

    return render(request, "publications/admin_request_detail.html", {
        "req": req, "target": target, "plasmids": plasmids
    })

# apps/publications/views_user.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib.contenttypes.models import ContentType

from .models import PublicationRequest
from .services import create_request
from apps.plasmids.models import PlasmidCollection

@login_required
def request_publication_collection(request, pk):
    collection = get_object_or_404(PlasmidCollection, pk=pk)

    if collection.is_public:
        return redirect("plasmids:collection_detail", pk=pk)

    ct = ContentType.objects.get_for_model(collection)
    exists = PublicationRequest.objects.filter(
        content_type=ct,
        object_id=collection.pk,
        status__in=["PENDING_TEAM_LEAD", "PENDING_ADMIN"]
    ).exists()

    if not exists:
        create_request(
            target=collection,
            user=request.user,
            team=getattr(collection, "team", None),
            require_team_lead=True,  # ou False selon règles
        )

    return redirect("plasmids:collection_detail", pk=pk)
