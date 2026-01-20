# apps/publications/services.py
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from .models import PublicationRequest, PublicationStatus

def create_request(*, target, user, team=None, require_team_lead=False) -> PublicationRequest:
    ct = ContentType.objects.get_for_model(target.__class__)
    status = PublicationStatus.PENDING_TEAM_LEAD if require_team_lead else PublicationStatus.PENDING_ADMIN
    return PublicationRequest.objects.create(
        content_type=ct,
        object_id=target.pk,
        requested_by=user,
        team=team,
        status=status,
    )

def team_validate(*, req: PublicationRequest, user):
    req.status = PublicationStatus.PENDING_ADMIN
    req.team_validated_by = user
    req.team_validated_at = timezone.now()
    req.save(update_fields=["status","team_validated_by","team_validated_at","updated_at"])

def approve(*, req: PublicationRequest, user):
    target = req.target
    target.is_public = True
    target.save(update_fields=["is_public"])
    req.status = PublicationStatus.APPROVED
    req.decided_by = user
    req.decided_at = timezone.now()
    req.rejection_reason = ""
    req.save(update_fields=["status","decided_by","decided_at","rejection_reason","updated_at"])

def reject(*, req: PublicationRequest, user, reason: str):
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Rejection reason is required")
    req.status = PublicationStatus.REJECTED
    req.decided_by = user
    req.decided_at = timezone.now()
    req.rejection_reason = reason
    req.save(update_fields=["status","decided_by","decided_at","rejection_reason","updated_at"])
