import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict
from fractions import Fraction

from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.services.calculator import format_result, safe_eval

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS: allow origins controlled via ALLOW_ORIGINS env (comma-separated).
# Default to http://localhost:8000 for development.
_allow_origins = os.getenv("ALLOW_ORIGINS")
if _allow_origins:
    allow_origins = [o.strip() for o in _allow_origins.split(",") if o.strip()]
else:
    allow_origins = ["http://localhost:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
# Disable Jinja2 internal template caching to avoid unhashable globals issues in some environments
# (In production, consider configuring a proper cache or ensuring template globals are hashable.)
templates.env.cache = {}

# Simple in-memory rate limiting for API endpoints. Configurable via RATE_LIMIT_PER_MIN env var.
# This is intentionally simple and suitable for single-process deployments or dev/test harnesses.

_RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))
_RATE_LIMIT_WINDOW = 60  # seconds
_rate_lock = threading.Lock()
_rate_store: Dict[str, Dict[str, float | int]] = {}


@app.middleware("http")
async def rate_limit_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    # Apply only to API endpoints to avoid interfering with template loads
    if request.url.path.startswith("/api/"):
        client_host = "unknown"
        if request.client and request.client.host:
            client_host = request.client.host
        now = time.time()
        with _rate_lock:
            entry = _rate_store.get(client_host)
            if entry is None or now - entry["start"] >= _RATE_LIMIT_WINDOW:
                _rate_store[client_host] = {"count": 1, "start": now}
                # Sweep expired entries to prevent unbounded memory growth.
                # Runs at most once per window per active client, so overhead is low.
                expired = [
                    k for k, v in _rate_store.items() if now - v["start"] >= _RATE_LIMIT_WINDOW
                ]
                for k in expired:
                    del _rate_store[k]
            else:
                if entry["count"] >= _RATE_LIMIT_PER_MIN:
                    return JSONResponse(status_code=429, content={"error": "Too many requests"})
                entry["count"] += 1
    response = await call_next(request)
    return response


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Response:
    return templates.TemplateResponse(request, "index.html", {"result": None, "expression": ""})


@app.post("/calculate")
async def calculate(
    request: Request, expression: str = Form(...), show_fraction: str | None = Form(None)
) -> Response:
    try:
        value = safe_eval(expression)
        # Keep the display always numeric (decimal) for the main display
        result = format_result(value, bool(show_fraction))
        context: Dict[str, Any] = {
            "value": value,
            "result": result,
            "is_error": False,
            "expression": expression,
        }
        # Always provide fraction parts for numeric results (including Fractions)
        from app.services.calculator import mixed_fraction_parts
        if isinstance(value, (int, float, Fraction)):
            context["fraction_parts"] = mixed_fraction_parts(value)

        return templates.TemplateResponse(
            request,
            "result.html",
            context,
        )
    except ZeroDivisionError:
        logger.warning(f"Division by zero: {expression}")
        return templates.TemplateResponse(
            request,
            "result.html",
            {"result": "0で割ることはできません", "is_error": True, "expression": expression},
        )
    except (SyntaxError, ValueError) as e:
        logger.warning(f"Invalid expression: {expression} - {e}")
        return templates.TemplateResponse(
            request,
            "result.html",
            {"result": "計算式が正しくありません", "is_error": True, "expression": expression},
        )
    except Exception as e:
        logger.error(f"Unexpected error calculating {expression}: {e}", exc_info=True)
        # Re-raise so the error is not silently swallowed and is visible in logs/tracebacks
        raise


class CalcRequest(BaseModel):
    expression: str
    show_fraction: bool = False


@app.post("/api/calculate")
async def api_calculate(request: Request, body: CalcRequest) -> JSONResponse:
    try:
        result = format_result(safe_eval(body.expression), body.show_fraction)
        return JSONResponse(content={"result": result, "expression": body.expression})
    except ZeroDivisionError:
        logger.warning(f"Division by zero: {body.expression}")
        return JSONResponse(
            content={"error": "0で割ることはできません", "expression": body.expression},
            status_code=400,
        )
    except (SyntaxError, ValueError) as e:
        logger.warning(f"Invalid expression: {body.expression} - {e}")
        return JSONResponse(
            content={"error": "計算式が正しくありません", "expression": body.expression},
            status_code=400,
        )
    except Exception as e:
        logger.error(f"Unexpected error calculating {body.expression}: {e}", exc_info=True)
        return JSONResponse(
            content={"error": "システムエラーが発生しました", "expression": body.expression},
            status_code=500,
        )
