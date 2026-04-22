import logging
import os
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.services.calculator import safe_eval

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS: allow origins controlled via ALLOW_ORIGINS env (comma-separated). Default to localhost for development.
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


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Response:
    return templates.TemplateResponse(name="index.html", context={"request": request, "result": None, "expression": ""})


@app.post("/calculate")
async def calculate(request: Request, expression: str = Form(...)) -> Response:
    try:
        result = safe_eval(expression)
        return templates.TemplateResponse(name="result.html", context={"request": request, "result": result, "expression": expression})
    except ZeroDivisionError:
        logger.warning(f"Division by zero: {expression}")
        return templates.TemplateResponse(name="result.html", context={"request": request, "result": "0で割ることはできません", "expression": expression})
    except (SyntaxError, ValueError) as e:
        logger.warning(f"Invalid expression: {expression} - {e}")
        return templates.TemplateResponse(name="result.html", context={"request": request, "result": "計算式が正しくありません", "expression": expression})
    except Exception as e:
        logger.error(f"Unexpected error calculating {expression}: {e}", exc_info=True)
        # Re-raise so the error is not silently swallowed and is visible in logs/tracebacks
        raise


class CalcRequest(BaseModel):
    expression: str


@app.post("/api/calculate")
async def api_calculate(request: Request, body: CalcRequest) -> JSONResponse:
    try:
        result = safe_eval(body.expression)
        return JSONResponse(content={"result": result, "expression": body.expression})
    except ZeroDivisionError:
        logger.warning(f"Division by zero: {body.expression}")
        return JSONResponse(content={"error": "0で割ることはできません", "expression": body.expression}, status_code=400)
    except (SyntaxError, ValueError) as e:
        logger.warning(f"Invalid expression: {body.expression} - {e}")
        return JSONResponse(content={"error": "計算式が正しくありません", "expression": body.expression}, status_code=400)
    except Exception as e:
        logger.error(f"Unexpected error calculating {body.expression}: {e}", exc_info=True)
        return JSONResponse(content={"error": "システムエラーが発生しました", "expression": body.expression}, status_code=500)
