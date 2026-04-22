import logging
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Response:
    return templates.TemplateResponse(request, "index.html", {"result": None, "expression": ""})


@app.post("/calculate")
async def calculate(request: Request, expression: str = Form(...)) -> Response:
    try:
        result = safe_eval(expression)
        return templates.TemplateResponse(
            request, "result.html", {"result": result, "expression": expression}
        )
    except ZeroDivisionError:
        logger.warning(f"Division by zero: {expression}")
        return templates.TemplateResponse(
            request,
            "result.html",
            {"result": "0で割ることはできません", "expression": expression},
        )
    except (SyntaxError, ValueError) as e:
        logger.warning(f"Invalid expression: {expression} - {e}")
        return templates.TemplateResponse(
            request,
            "result.html",
            {"result": "計算式が正しくありません", "expression": expression},
        )
    except Exception as e:
        logger.error(f"Unexpected error calculating {expression}: {e}", exc_info=True)
        return templates.TemplateResponse(
            request,
            "result.html",
            {"result": "システムエラーが発生しました", "expression": expression},
            status_code=500,
        )


class CalcRequest(BaseModel):
    expression: str


@app.post("/api/calculate")
async def api_calculate(request: Request, body: CalcRequest) -> JSONResponse:
    try:
        result = safe_eval(body.expression)
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
