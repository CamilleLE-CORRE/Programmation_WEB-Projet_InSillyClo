"""
Function realization:
- User: 
    - User can pull a publication request. 
    - Check it's result (Approved;Rejected by cheffe/admin;Pending).
- Cheffe: 
    - Cheffe can view all publication requests pending her validation for her team.
    - Cheffe can approve or reject publication requests with comments if needed.
    - A mail is sent to cheffe when a new publication request is created for her team.
- Admin: 
    - Admin can view all publication requests pending admin validation.
    - Admin can approve or reject publication requests with comments if needed.
    - A mail is sent to all admins when a new publication request is created.
"""

from django.utils import timezone
from urllib import request
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail

from apps.accounts.models import User, Team
from .models import Publication


#-----------------
# Permmision helpers
#-----------------  
def is_cheffe_user(user) -> bool:
    return user.is_authenticated and Team.objects.filter(owner=user).exists()

def is_admin_user(user) -> bool:
    return user.is_authenticated and (user.is_superuser or user.is_staff or user.role == "administratrice")

def _target_team_owner_id(pub: Publication):
    """
    Safely get team.owner_id for the target object.
    Returns None if target/team is missing.
    """
    target = pub.target
    if not target:
        return None
    team = getattr(target, "team", None)
    if not team:
        return None
    return getattr(team, "owner_id", None)


#-----------------
# User Views
#----------------
@login_required
@require_http_methods(["POST"])
def request_publication(request, target_kind:str, target_id:int):
    """
    Allow a user to request publication of a target object.
    - target_kind: collection or correspondence
    - target_id: ID of the target object.(PK)
    """
    kind_to_ct = {  # Map target kinds to ContentType (app_label, model name)
        "collection":("plasmids","plasmidcollection"),
        "correspondence":("correspondences","correspondence"),
    }

    if target_kind not in kind_to_ct:
        raise Http404("Invalid target kind.")
    
    app_label, model = kind_to_ct[target_kind]
    ct = get_object_or_404(ContentType, app_label=app_label, model=model)

    # Ensure target object exists
    model_cls = ct.model_class()
    if model_cls is None:
        raise Http404("Target model does not exist.")
    target_obj = get_object_or_404(model_cls, pk=target_id)

    # Create publication request
    try:
        # Decide initial status based on target ownership
        initial_status = (
            Publication.Status.PENDING_CHEFFE
            if getattr(target_obj, "team_id", None) is not None
            else Publication.Status.PENDING_ADMIN
        )
        team = getattr(target_obj, "team", None)

        pub = Publication(
            requested_by=request.user,
            target_content_type=ct,
            target_object_id=target_obj.pk,
            status=initial_status,
            team = team
        )
        pub.full_clean()
        pub.save()
        
        # Send email to cheffe or admins
        if pub.status == Publication.Status.PENDING_CHEFFE:
            notify_cheffe_new_publication(pub, request)   
        else:
            notify_admins_new_publication(pub, request)

        messages.success(request, "Publication request submitted successfully.")
    except Exception as e:
        messages.error(request, f"Failed to submit publication request: {str(e)}")
    
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
@require_http_methods(["GET"])
def my_publication_requests(request):
    """
    List of publication requests made by the logged-in user.
    """
    pubs = Publication.objects.filter(requested_by=request.user).select_related('target_content_type').order_by('-created_at')
    return render(request, 'publications/my_requests.html', {'publications': pubs})


# -----------------
# Cheffe Views
# -----------------
@user_passes_test(is_cheffe_user)
@require_http_methods(["GET"])
def cheffe_publication_requests(request):
    qs = (
        Publication.objects
        .filter(
            status=Publication.Status.PENDING_CHEFFE,
            team__owner=request.user,          # SOURCE DE VÉRITÉ
        )
        .select_related("requested_by", "cheffe_reviewed_by", "target_content_type", "team")
        .order_by("-created_at")
    )
    return render(request, "publications/cheffe_requests.html", {"publications": qs})

@user_passes_test(is_cheffe_user)
@require_http_methods(["POST"])
def cheffe_review_publication_request(request, publication_id: int):
    action = (request.POST.get("action") or "").lower()
    comment = (request.POST.get("comment") or "").strip()

    if action not in ("approve", "reject"):
        messages.error(request, "Invalid action.")
        return redirect("publications:cheffe_requests")

    pub = get_object_or_404(Publication, pk=publication_id)

    # Status must be pending cheffe
    if pub.status != Publication.Status.PENDING_CHEFFE:
        messages.warning(request, "This request is not awaiting cheffe validation.")
        return redirect("publications:cheffe_requests")

    # Authorization: only team owner can review
    if pub.team_id is None or pub.team.owner_id != request.user.id:
        messages.error(request, "You are not allowed to review this request.")
        return redirect("publications:cheffe_requests")


    if action == "approve":
        pub.status = Publication.Status.PENDING_ADMIN
        pub.cheffe_reviewed_by = request.user
        pub.cheffe_review_comment = ""
        pub.cheffe_reviewed_at = timezone.now()
        pub.full_clean()
        pub.save()

        # Once cheffe approved, notify admins
        notify_admins_new_publication(pub, request)

        messages.success(request, "Validated by cheffe and sent to administratrices.")
    else:
        if not comment:
            messages.error(request, "Comment is required when rejecting.")
            return redirect("publications:cheffe_requests")

        pub.status = Publication.Status.REJECTED_BY_CHEFFE
        pub.cheffe_reviewed_by = request.user
        pub.cheffe_review_comment = comment
        pub.cheffe_reviewed_at = timezone.now()
        pub.full_clean()
        pub.save()

        messages.success(request, "Request rejected by cheffe.")
    return redirect("publications:cheffe_requests")


def notify_cheffe_new_publication(pub: Publication, request):
    """
    Send email to cheffe when new publication request is created
    """
    target = pub.target
    if not target:
        return
    team = getattr(target, "team", None)
    if not team or not team.owner or not team.owner.email:
        return

    cheffe_email = team.owner.email
    cheffe_url = request.build_absolute_uri(
        reverse("publications:cheffe_requests") 
    )

    subject = f"[InSillyClo] Publication request #{pub.id} needs cheffe validation"
    message = (
        f"A new publication request requires your validation.\n\n"
        f"Request ID: {pub.id}\n"
        f"Requested by: {pub.requested_by.email}\n"
        f"Target: {pub.target_content_type.app_label}/{pub.target_content_type.model} "
        f"(id={pub.target_object_id})\n"
        f"Status: {pub.status}\n"
        f"Created at: {pub.created_at}\n\n"
        f"Review it here:\n{cheffe_url}\n"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[cheffe_email],
        fail_silently=True,
    )


@user_passes_test(is_cheffe_user)
def cheffe_detail(request, pk):
    pub = get_object_or_404(Publication, pk=pk)

    target = pub.target  


    context = {
        "pub": pub,
        "target": target,
        "target_ct": pub.target_content_type,  
    }

    if pub.target_content_type.app_label == "plasmids" and pub.target_content_type.model in ("plasmidcollection", "collection"):
        context["entries"] = getattr(target, "entries", None).all() if hasattr(target, "entries") else None

    return render(request, "publications/cheffe_detail.html", context)




#-----------------
# Admin Views
#-----------------
@user_passes_test(is_admin_user)
@require_http_methods(["GET"])
def admin_publication_requests(request):
    """
    Admin view to list all publication requests with filtering options.
    Shows all requests: pending, approved, rejected.
    """
    Status = Publication.Status  # raccourci

    # 1) base queryset
    qs = Publication.objects.select_related(
        "requested_by",
        "admin_reviewed_by",
        "cheffe_reviewed_by",
        "target_content_type",
        "team",
    ).order_by("-created_at")

    # 2) mapping URL -> valeur DB (évite le mismatch)
    status_param = (request.GET.get("status") or "").strip()

    status_map = {
        "": None,
        "all": None,

        # accepte plusieurs écritures côté URL
        "pending_admin": Status.PENDING_ADMIN,
        "PENDING_ADMIN": Status.PENDING_ADMIN,

        "pending_cheffe": Status.PENDING_CHEFFE,
        "PENDING_CHEFFE": Status.PENDING_CHEFFE,

        "approved": Status.APPROVED,
        "APPROVED": Status.APPROVED,

        "rejected_by_cheffe": Status.REJECTED_BY_CHEFFE,
        "REJECTED_BY_CHEFFE": Status.REJECTED_BY_CHEFFE,

        "rejected_by_admin": Status.REJECTED_BY_ADMIN,
        "REJECTED_BY_ADMIN": Status.REJECTED_BY_ADMIN,
    }

    status_value = status_map.get(status_param, None)

    # 3) applique le filtre seulement si reconnu
    if status_param and status_value is None:
        # param inconnu -> on n’applique pas de filtre (ou tu peux afficher une erreur)
        status_filter = ""
    else:
        status_filter = status_param
        if status_value is not None:
            qs = qs.filter(status=status_value)

    # 4) compteurs (même table, pas besoin de refaire Publication.objects...)
    base = Publication.objects
    status_counts = {
        "total": base.count(),
        "pending_admin": base.filter(status=Status.PENDING_ADMIN).count(),
        "pending_cheffe": base.filter(status=Status.PENDING_CHEFFE).count(),
        "approved": base.filter(status=Status.APPROVED).count(),
        "rejected_cheffe": base.filter(status=Status.REJECTED_BY_CHEFFE).count(),
        "rejected_admin": base.filter(status=Status.REJECTED_BY_ADMIN).count(),
    }

    return render(request, "publications/admin_requests.html", {
        "publications": qs,
        "status_filter": status_filter,
        "status_counts": status_counts,
    })

@user_passes_test(is_admin_user)
@require_http_methods(["POST"])
def admin_review_publication_request(request, publication_id:int):
    """
    Admin view to approve or reject a publication request.
    Comments: required if rejecting.
    """
    action = (request.POST.get('action') or '').lower()
    comment = request.POST.get('comment', '').strip()

    if action not in ('approve', 'reject'):
        messages.error(request, "Invalid action.")
        return redirect("publications:admin_requests")
    pub = get_object_or_404(Publication, pk=publication_id)

    if pub.status != Publication.Status.PENDING_ADMIN:
        messages.warning(request, "This publication request has already been reviewed.")
        return redirect("publications:admin_requests")
    
    if action == "approve":
        pub.status = Publication.Status.APPROVED
        pub.admin_reviewed_by = request.user
        pub.admin_review_comment = ""
        pub.admin_reviewed_at = timezone.now()
        pub.full_clean()
        pub.save()

        target = pub.target
        if target and hasattr(target, 'is_public'):
            target.is_public = True
            target.save()
        messages.success(request, "Publication request approved.")
    # Reject:
    else:
        if not comment:
            messages.error(request, "Comment is required when rejecting a publication request.")
            return redirect("publications:admin_requests")

        pub.status = Publication.Status.REJECTED_BY_ADMIN
        pub.admin_reviewed_by = request.user
        pub.admin_review_comment = comment
        pub.admin_reviewed_at = timezone.now()
        pub.full_clean()
        pub.save()
        messages.success(request, "Publication request rejected.")
    
    return redirect("publications:admin_requests")


@user_passes_test(is_admin_user)
def admin_detail(request, pk):
    pub = get_object_or_404(Publication, pk=pk)

    target = pub.target  


    context = {
        "pub": pub,
        "target": target,
        "target_ct": pub.target_content_type,  
    }

    if pub.target_content_type.app_label == "plasmids" and pub.target_content_type.model in ("plasmidcollection", "collection"):
        context["entries"] = getattr(target, "entries", None).all() if hasattr(target, "entries") else None

    return render(request, "publications/admin_detail.html", context)


def notify_admins_new_publication(pub: Publication, request):
    # 1) Search for admin emails
    admin_emails = list(
        User.objects.filter(role="administratrice").values_list("email", flat=True) 
    )
    admin_emails = [e for e in admin_emails if e] 

    if not admin_emails:
        return  
    # 2) Send email notification
    admin_url = request.build_absolute_uri(
        reverse("publications:admin_detail", args=[pub.id])  
    )

    subject = f"[InSillyClo] New publication request #{pub.id}"

    message = (
        f"A new publication request has been submitted.\n\n"
        f"Request ID: {pub.id}\n"
        f"Requested by: {pub.requested_by.email}\n"
        f"Target: {pub.target_content_type.app_label}/{pub.target_content_type.model} "
        f"(id={pub.target_object_id})\n"
        f"Status: {pub.status}\n"
        f"Created at: {pub.created_at}\n\n"
        f"Review it here:\n{admin_url}\n"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=admin_emails,
        fail_silently=True,  
    )