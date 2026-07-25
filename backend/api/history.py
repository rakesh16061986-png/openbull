"""
External API - Historical OHLCV candles endpoint.
Response format follows OpenAlgo standard.
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/history")
async def api_history(request: Request):
    """Get historical OHLCV candles via the external API."""
    from backend.dependencies import get_api_user, get_db
    from backend.services.history_service import get_history_with_auth

    try:
        async for db in get_db():
            api_user = await get_api_user(request, db)
            break
    except HTTPException as e:
        message = e.detail if isinstance(e.detail, str) else str(e.detail)
        return JSONResponse(content={"status": "error", "message": message}, status_code=e.status_code)
    except Exception:
        logger.exception("Unexpected error in history endpoint")
        return JSONResponse(content={"status": "error", "message": "An unexpected error occurred"}, status_code=500)

    user_id, auth_token, broker_name, config = api_user

    try:
        body = await request.json()
    except Exception:
        body = {}

    symbol = body.get("symbol")
    exchange = body.get("exchange")
    interval = body.get("interval")
    start_date = body.get("start_date")
    end_date = body.get("end_date")

    if not all([symbol, exchange, interval, start_date, end_date]):
        return JSONResponse(
            content={"status": "error", "message": "symbol, exchange, interval, start_date, and end_date are required"},
            status_code=400,
        )

    success, response_data, status_code = get_history_with_auth(
        symbol=symbol, exchange=exchange, interval=interval,
        start_date=start_date, end_date=end_date,
        auth_token=auth_token, broker=broker_name, config=config,
    )
    return JSONResponse(content=response_data, status_code=status_code)


async def _resolve_api_user(request: Request):
    """Shared auth resolution for the expired-instrument endpoints below.
    Returns (user_id, auth_token, broker_name, config) or raises via early return."""
    from backend.dependencies import get_api_user, get_db
    async for db in get_db():
        return await get_api_user(request, db)


@router.post("/expired_contracts")
async def api_expired_contracts(request: Request):
    """List expired option/future contracts for an underlying+expiry (Upstox Plus only).

    Backtest-only helper: once a weekly/monthly contract expires it drops out
    of the normal tradable instrument master, so /history can't reach it.
    Body: {apikey, instrument_key, expiry_date (YYYY-MM-DD), kind: "option"|"future"}.
    """
    try:
        api_user = await _resolve_api_user(request)
    except HTTPException as e:
        message = e.detail if isinstance(e.detail, str) else str(e.detail)
        return JSONResponse(content={"status": "error", "message": message}, status_code=e.status_code)
    except Exception:
        logger.exception("Unexpected error resolving api user")
        return JSONResponse(content={"status": "error", "message": "An unexpected error occurred"}, status_code=500)

    user_id, auth_token, broker_name, config = api_user
    if broker_name != "upstox":
        return JSONResponse(content={"status": "error", "message": "expired_contracts only supports the upstox broker"}, status_code=400)

    body = await request.json()
    instrument_key = body.get("instrument_key")
    expiry_date = body.get("expiry_date")
    kind = body.get("kind")
    if not all([instrument_key, expiry_date, kind]):
        return JSONResponse(content={"status": "error", "message": "instrument_key, expiry_date, and kind are required"}, status_code=400)

    try:
        from backend.broker.upstox.api.data import get_expired_contracts
        data = get_expired_contracts(kind, instrument_key, expiry_date, auth_token)
        return JSONResponse(content={"status": "success", "data": data}, status_code=200)
    except ValueError as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Error fetching expired contracts: %s", e)
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@router.post("/expired_history")
async def api_expired_history(request: Request):
    """Historical candles for one already-expired contract (Upstox Plus only).
    Body: {apikey, expired_instrument_key, interval, start_date, end_date}.
    """
    try:
        api_user = await _resolve_api_user(request)
    except HTTPException as e:
        message = e.detail if isinstance(e.detail, str) else str(e.detail)
        return JSONResponse(content={"status": "error", "message": message}, status_code=e.status_code)
    except Exception:
        logger.exception("Unexpected error resolving api user")
        return JSONResponse(content={"status": "error", "message": "An unexpected error occurred"}, status_code=500)

    user_id, auth_token, broker_name, config = api_user
    if broker_name != "upstox":
        return JSONResponse(content={"status": "error", "message": "expired_history only supports the upstox broker"}, status_code=400)

    body = await request.json()
    expired_instrument_key = body.get("expired_instrument_key")
    interval = body.get("interval")
    start_date = body.get("start_date")
    end_date = body.get("end_date")
    if not all([expired_instrument_key, interval, start_date, end_date]):
        return JSONResponse(content={"status": "error", "message": "expired_instrument_key, interval, start_date, and end_date are required"}, status_code=400)

    try:
        from backend.broker.upstox.api.data import get_expired_history
        data = get_expired_history(expired_instrument_key, interval, start_date, end_date, auth_token)
        return JSONResponse(content={"status": "success", "data": data}, status_code=200)
    except ValueError as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Error fetching expired history: %s", e)
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)
