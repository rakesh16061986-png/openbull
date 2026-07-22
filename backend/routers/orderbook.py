"""
Orderbook router - GET /web/orderbook
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies import get_broker_context, BrokerContext
from backend.services.orderbook_service import get_orderbook_with_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/web", tags=["orderbook"])


@router.get("/orderbook")
async def orderbook(all_history: bool = False, ctx: BrokerContext = Depends(get_broker_context)):
    """Get order book data from the broker.

    all_history=true bypasses the session-boundary filter (default is the
    current IST session only, so the view rolls over cleanly each day) -
    lets the UI look back at a prior session's fills instead of only ever
    showing an empty book right after midnight IST.
    """
    success, response_data, status_code = get_orderbook_with_auth(
        auth_token=ctx.auth_token,
        broker=ctx.broker_name,
        config=ctx.broker_config,
        user_id=ctx.user.id,
        all_history=all_history,
    )

    if not success:
        raise HTTPException(status_code=status_code, detail=response_data.get("message", "Failed to fetch orderbook"))

    return response_data
