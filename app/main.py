import logging
import os
from pathlib import Path
import threading
import time
from typing import Awaitable, Callable, Dict

from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.services.calculator import safe_eval, float_to_mixed_fraction

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
        result = safe_eval(expression)
        # If the user requested fraction display (checkbox present), format numeric results
        if show_fraction and isinstance(result, (int, float)):
            result = float_to_mixed_fraction(float(result))
        return templates.TemplateResponse(
            request, "result.html", {"result": result, "expression": expression}
        )
    except ZeroDivisionError:
        logger.warning(f"Division by zero: {expression}")
        return templates.TemplateResponse(
            request, "result.html", {"result": "0で割ることはできません", "expression": expression}
        )
    except (SyntaxError, ValueError) as e:
        logger.warning(f"Invalid expression: {expression} - {e}")
        return templates.TemplateResponse(
            request, "result.html", {"result": "計算式が正しくありません", "expression": expression}
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
        result = safe_eval(body.expression)
        # If client requested fraction formatting, convert numeric result to mixed-fraction string
        if body.show_fraction and isinstance(result, (int, float)):
            result = float_to_mixed_fraction(float(result))
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
