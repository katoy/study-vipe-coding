import logging
import os
import threading
import time
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional, Union

from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.services.calculator import Calculator, Number

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
_allow_origins = os.getenv("ALLOW_ORIGINS")
if _allow_origins:
    allow_origins = [o.strip() for o in _allow_origins.split(",") if o.strip()]
else:
    allow_origins = ["http://localhost:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
templates.env.cache = {}

_SECURITY_HEADERS_ENABLED = os.getenv("SECURITY_HEADERS_ENABLED", "1").lower() in (
    "1",
    "true",
    "yes",
)
_DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "font-src 'self'; "
    "frame-ancestors 'none'; "
    "form-action 'self'; "
    "base-uri 'self'; "
    "object-src 'none'"
)
_CSP_POLICY = os.getenv("CSP_POLICY", _DEFAULT_CSP)
_HSTS_VALUE = os.getenv("HSTS_VALUE", "max-age=31536000; includeSubDomains")


def _request_is_https(request: Request) -> bool:
    if request.url.scheme == "https":
        return True
    return request.headers.get("x-forwarded-proto", "").lower() == "https"


_RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))
_RATE_LIMIT_WINDOW_NS = 60 * 1_000_000_000
_RATE_LIMIT_MAX_KEYS = int(os.getenv("RATE_LIMIT_MAX_KEYS", "10000"))
_RATE_LIMIT_TRUST_FORWARDED = os.getenv("RATE_LIMIT_TRUST_FORWARDED", "0").lower() in (
    "1",
    "true",
    "yes",
)
_rate_lock = threading.Lock()
_rate_store: Dict[str, Dict[str, int]] = {}
_rate_last_sweep_ns: int = 0


def _client_key(request: Request) -> str:
    if _RATE_LIMIT_TRUST_FORWARDED:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            first = forwarded.split(",", 1)[0].strip()
            if first:
                return first
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _sweep_expired(now: int) -> None:
    expired = [k for k, v in _rate_store.items() if now - v["start"] >= _RATE_LIMIT_WINDOW_NS]
    for k in expired:
        del _rate_store[k]


@app.middleware("http")
async def rate_limit_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    global _rate_last_sweep_ns
    if request.url.path.startswith("/api/"):
        client_host = _client_key(request)
        now = time.monotonic_ns()
        with _rate_lock:
            if now - _rate_last_sweep_ns >= _RATE_LIMIT_WINDOW_NS:
                _sweep_expired(now)
                _rate_last_sweep_ns = now

            entry = _rate_store.get(client_host)
            if entry is None or now - entry["start"] >= _RATE_LIMIT_WINDOW_NS:
                if client_host not in _rate_store and len(_rate_store) >= _RATE_LIMIT_MAX_KEYS:
                    oldest = min(_rate_store.items(), key=lambda kv: kv[1]["start"])[0]
                    del _rate_store[oldest]
                _rate_store[client_host] = {"count": 1, "start": now}
            else:
                if entry["count"] >= _RATE_LIMIT_PER_MIN:
                    return JSONResponse(status_code=429, content={"error": "Too many requests"})
                entry["count"] += 1
    response = await call_next(request)
    return response


@app.middleware("http")
async def security_headers_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    if not _SECURITY_HEADERS_ENABLED:
        return response
    headers = response.headers
    headers.setdefault("X-Content-Type-Options", "nosniff")
    headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    headers.setdefault("X-Frame-Options", "DENY")
    headers.setdefault("Content-Security-Policy", _CSP_POLICY)
    if _request_is_https(request):
        headers.setdefault("Strict-Transport-Security", _HSTS_VALUE)
    return response


# Create a module-level calculator instance with default settings
calc = Calculator()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Response:
    return templates.TemplateResponse(request, "index.html", {"result": None, "expression": ""})


_DIV_BY_ZERO_MSG = "0で割ることはできません"
_INVALID_EXPR_MSG = "計算式が正しくありません"
_SYSTEM_ERROR_MSG = "システムエラーが発生しました"


@dataclass(frozen=True)
class _CalculationOutcome:
    expression: str
    is_error: bool
    status_code: int
    value: Optional[Number] = None
    result: Optional[Union[Number, str]] = None
    fraction_parts: Optional[dict[str, int | str]] = None
    error_message: Optional[str] = None


def _compute_calculation(expression: str, show_fraction: bool) -> _CalculationOutcome:
    try:
        value = calc.safe_eval(expression)
    except ZeroDivisionError:
        logger.warning("Division by zero: %s", expression)
        return _CalculationOutcome(
            expression=expression, is_error=True, status_code=400, error_message=_DIV_BY_ZERO_MSG
        )
    except (SyntaxError, ValueError) as e:
        logger.warning("Invalid expression: %s - %s", expression, e)
        return _CalculationOutcome(
            expression=expression, is_error=True, status_code=400, error_message=_INVALID_EXPR_MSG
        )
    except Exception as e:
        logger.error("Unexpected error calculating %s: %s", expression, e, exc_info=True)
        return _CalculationOutcome(
            expression=expression, is_error=True, status_code=500, error_message=_SYSTEM_ERROR_MSG
        )

    result = calc.format_result(value, show_fraction)
    fraction_parts = (
        calc.mixed_fraction_parts(value) if isinstance(value, (int, Fraction)) else None
    )
    return _CalculationOutcome(
        expression=expression,
        is_error=False,
        status_code=200,
        value=value,
        result=result,
        fraction_parts=fraction_parts,
    )


@app.post("/calculate")
async def calculate(
    request: Request, expression: str = Form(...), show_fraction: str | None = Form(None)
) -> Response:
    outcome = _compute_calculation(expression, bool(show_fraction))
    if outcome.is_error:
        # Soft validation errors render inline at HTTP 200 so the form re-displays
        # the message; only system errors surface as 5xx.
        status = outcome.status_code if outcome.status_code >= 500 else 200
        return templates.TemplateResponse(
            request,
            "result.html",
            {
                "result": outcome.error_message,
                "is_error": True,
                "expression": outcome.expression,
            },
            status_code=status,
        )
    context: Dict[str, Any] = {
        "value": outcome.value,
        "result": outcome.result,
        "is_error": False,
        "expression": outcome.expression,
    }
    if outcome.fraction_parts is not None:
        context["fraction_parts"] = outcome.fraction_parts
    return templates.TemplateResponse(request, "result.html", context)


class CalcRequest(BaseModel):
    expression: str
    show_fraction: bool = False


@app.post("/api/calculate")
async def api_calculate(request: Request, body: CalcRequest) -> JSONResponse:
    outcome = _compute_calculation(body.expression, body.show_fraction)
    if outcome.is_error:
        return JSONResponse(
            content={"error": outcome.error_message, "expression": outcome.expression},
            status_code=outcome.status_code,
        )
    return JSONResponse(content={"result": outcome.result, "expression": outcome.expression})
