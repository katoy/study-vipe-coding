from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from calculator import safe_eval
from pathlib import Path
from jinja2 import Template

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

def _load_template(name: str) -> str:
    """Read a template file with UTF-8‑sig to strip possible BOM.
    This ensures Jinja2 receives a clean string.
    """
    path = Path(__file__).parent / "templates" / name
    return path.read_text(encoding="utf-8-sig")

def render_template(name: str, context: dict) -> str:
    """Render a Jinja2 template without caching.
    Reads the file each request to avoid environment complexities.
    """
    tmpl = Template(_load_template(name))
    return tmpl.render(**context)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    html = render_template("index.html", {"request": request, "result": None, "expression": ""})
    return HTMLResponse(content=html)

@app.post("/calculate")
async def calculate(request: Request, expression: str = Form(...)):
    try:
        result = safe_eval(expression)
        html = render_template("result.html", {"request": request, "result": result, "expression": expression})
        return HTMLResponse(content=html)
    except ZeroDivisionError:
        html = render_template("result.html", {"request": request, "result": "0で割ることはできません", "expression": expression})
        return HTMLResponse(content=html, status_code=400)
    except Exception:
        html = render_template("result.html", {"request": request, "result": "計算式が正しくありません", "expression": expression})
        return HTMLResponse(content=html, status_code=400)

@app.post("/api/calculate")
async def api_calculate(request: Request, expression: str = Form(...)):
    try:
        result = safe_eval(expression)
        return JSONResponse(content={"result": result, "expression": expression})
    except ZeroDivisionError:
        return JSONResponse(content={"error": "0で割ることはできません", "expression": expression}, status_code=400)
    except Exception:
        return JSONResponse(content={"error": "計算式が正しくありません", "expression": expression}, status_code=400)
