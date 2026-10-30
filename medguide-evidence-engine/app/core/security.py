from __future__ import annotations

import hmac
import json
import os
from enum import StrEnum

from fastapi import Header, HTTPException
from pydantic import BaseModel


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    expected = os.getenv("MEDGUIDE_ADMIN_TOKEN")
    environment = os.getenv("MEDGUIDE_ENV", "development")
    if not expected:
        message = (
            "admin token is not configured"
            if environment == "development"
            else "deployment configuration is invalid: admin token is required"
        )
        raise HTTPException(status_code=503, detail={"code": "ADMIN_AUTH_UNAVAILABLE", "message": message})
    if x_admin_token is None or not hmac.compare_digest(x_admin_token, expected):
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "valid admin token required"},
        )


class ReviewerRole(StrEnum):
    SOURCE_REVIEWER = "source_reviewer"
    CLINICAL_REVIEWER = "clinical_reviewer"
    ADMIN = "admin"


class ReviewerPrincipal(BaseModel):
    reviewer_id: str
    display_name: str
    roles: set[ReviewerRole]


def require_reviewer(authorization: str | None = Header(default=None)) -> ReviewerPrincipal:
    environment = os.getenv("MEDGUIDE_ENV", "development").lower()
    dev_bypass = os.getenv("MEDGUIDE_REVIEW_DEV_BYPASS", "").lower() == "true"
    if dev_bypass and environment == "development":
        return ReviewerPrincipal(
            reviewer_id="local-reviewer",
            display_name="Local Development Reviewer",
            roles={ReviewerRole.ADMIN},
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "reviewer session required"})
    supplied = authorization.removeprefix("Bearer ").strip()
    raw = os.getenv("MEDGUIDE_REVIEWER_TOKENS", "")
    if not raw:
        raise HTTPException(status_code=503, detail={"code": "REVIEW_AUTH_UNAVAILABLE", "message": "reviewer authentication is not configured"})
    try:
        configured = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=503, detail={"code": "REVIEW_AUTH_INVALID", "message": "reviewer authentication configuration is invalid"}) from exc
    match = next(
        (value for token, value in configured.items() if hmac.compare_digest(str(token), supplied)),
        None,
    )
    if not isinstance(match, dict):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "invalid reviewer session"})
    try:
        return ReviewerPrincipal(
            reviewer_id=str(match["reviewer_id"]),
            display_name=str(match.get("display_name") or match["reviewer_id"]),
            roles={ReviewerRole(role) for role in match.get("roles", [])},
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail={"code": "REVIEW_AUTH_INVALID", "message": "reviewer identity configuration is invalid"}) from exc


def require_role(principal: ReviewerPrincipal, *allowed: ReviewerRole) -> None:
    if ReviewerRole.ADMIN not in principal.roles and principal.roles.isdisjoint(allowed):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "reviewer role is not permitted for this transition"})

