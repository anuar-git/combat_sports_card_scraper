"""eBay Marketplace Account Deletion/Closure notification endpoint.

Required by eBay Developer Program to keep API keysets active.
See: https://developer.ebay.com/marketplace-account-deletion

GET  /ebay/account-deletion  — challenge verification (endpoint ownership proof)
POST /ebay/account-deletion  — account deletion/closure notification handler
"""

from __future__ import annotations

import hashlib
import json
import logging
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)

router = APIRouter()

# Set both in your environment / Railway config.
# EBAY_VERIFICATION_TOKEN: the token you created in the eBay Developer portal
#   (Alerts & Notifications → Notification Preferences → Verification Token)
# EBAY_NOTIFICATION_ENDPOINT_URL: the full public URL of this endpoint,
#   e.g. https://your-app.railway.app/ebay/account-deletion
_VERIFICATION_TOKEN = os.getenv("EBAY_VERIFICATION_TOKEN", "")
_ENDPOINT_URL = os.getenv("EBAY_NOTIFICATION_ENDPOINT_URL", "")


@router.get("/account-deletion")
def ebay_challenge(challenge_code: str) -> JSONResponse:
    """Respond to eBay's endpoint ownership challenge.

    eBay sends challenge_code as a query param; we must return:
        SHA256(challengeCode + verificationToken + endpointUrl)
    with Content-Type: application/json.
    """
    if not _VERIFICATION_TOKEN or not _ENDPOINT_URL:
        raise HTTPException(
            status_code=500,
            detail="EBAY_VERIFICATION_TOKEN or EBAY_NOTIFICATION_ENDPOINT_URL not configured",
        )

    digest = hashlib.sha256(
        (challenge_code + _VERIFICATION_TOKEN + _ENDPOINT_URL).encode()
    ).hexdigest()

    return JSONResponse(content={"challengeResponse": digest})


@router.post("/account-deletion", status_code=200)
async def ebay_account_deletion(request: Request) -> dict:
    """Handle eBay account deletion/closure notifications.

    This app stores only scraped public listing data — no eBay user PII —
    so there is nothing to delete. We log the notification and acknowledge.
    eBay requires a 200 response; any non-2xx causes retries.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    notification = body.get("notification", {})
    data = notification.get("data", {})
    username = data.get("username", "<unknown>")
    user_id = data.get("userId", "<unknown>")

    log.info(
        "ebay_account_deletion_notification",
        extra={"username": username, "userId": user_id},
    )

    return {"ack": "SUCCESS"}
