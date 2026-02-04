"""
Function realization:
- User: User can pull a publication request. And check it's result (Approved/Rejected/Pending).
- Admin: Admin can approve or reject publication requests with comments if needed.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .models import Publication

#-----------------
# Permmision helpers
#-----------------  
def is_admin_user(user) -> bool:
    """
    Check if the user has admin privileges.
    """
    return user.is_authenticated and (user.is_staff or user.is_superuser)


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
        pub = Publication(
            requested_by=request.user,
            target_content_type=ct,
            target_object_id=target_obj.pk,
        )
        pub.full_clean()
        pub.save()
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



#-----------------
# Admin Views
#-----------------
@user_passes_test(is_admin_user)
@require_http_methods(["GET"])
def admin_publication_requests(request):
    """
    Admin view to list all publication requests.
    """
    status = request.GET.get('status')
    qs = Publication.objects.all().select_related(
        'requested_by', 'decided_by', 'target_content_type'
    )
    if status:
        qs = qs.filter(status=status)
    
    qs = qs.order_by('-created_at')
    return render(request, 'publications/admin_requests.html', {'publications': qs, "status":status})


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

    if pub.status != Publication.Status.PENDING:
        messages.warning(request, "This publication request has already been reviewed.")
        return redirect("publications:admin_requests")
    
    if action == "approve":
        pub.approve(request.user)
        target = pub.target
        if hasattr(target, 'is_public'):
            target.is_public = True
            target.save()
        messages.success(request, "Publication request approved.")
    else:  # reject
        if not comment:
            messages.error(request, "Comment is required when rejecting a publication request.")
            return redirect("publications:admin_requests")
        pub.reject(request.user, comment)
        messages.success(request, "Publication request rejected.")
    
    return redirect("publications:admin_requests")