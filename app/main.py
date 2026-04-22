from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from app.services.calculator import safe_eval
from pathlib import Path

app = FastAPI()
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"result": None, "expression": ""})

@app.post("/calculate")
async def calculate(request: Request, expression: str = Form(...)):
    try:
        result = safe_eval(expression)
        return templates.TemplateResponse(request, "result.html", {"result": result, "expression": expression})
    except ZeroDivisionError:
        return templates.TemplateResponse(request, "result.html", {"result": "0で割ることはできません", "expression": expression}, status_code=400)
    except Exception:
        return templates.TemplateResponse(request, "result.html", {"result": "計算式が正しくありません", "expression": expression}, status_code=400)

class CalcRequest(BaseModel):
    expression: str

@app.post("/api/calculate")
async def api_calculate(request: Request, body: CalcRequest):
    try:
        result = safe_eval(body.expression)
        return JSONResponse(content={"result": result, "expression": body.expression})
    except ZeroDivisionError:
        return JSONResponse(content={"error": "0で割ることはできません", "expression": body.expression}, status_code=400)
    except Exception:
        return JSONResponse(content={"error": "計算式が正しくありません", "expression": body.expression}, status_code=400)
