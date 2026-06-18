"""FastAPI app: server-rendered form + HTMX report partial."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import settings
from .pipeline import orchestrator
from .pipeline.orchestrator import InputTooLargeError
from .report import renderer

_ROOT = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(_ROOT / "templates"))

app = FastAPI(title="Autopsy Band")
app.mount("/static", StaticFiles(directory=str(_ROOT / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {"max_chars": settings.max_input_chars},
    )


@app.post("/diagnose", response_class=HTMLResponse)
async def diagnose(request: Request, input_text: str = Form("")) -> HTMLResponse:
    input_text = (input_text or "").strip()
    if not input_text:
        return templates.TemplateResponse(
            request,
            "_report.html",
            {"error": "Provide an input to diagnose."},
            status_code=400,
        )
    if len(input_text) > settings.max_input_chars:
        return templates.TemplateResponse(
            request,
            "_report.html",
            {"error": f"input exceeds {settings.max_input_chars} chars"},
            status_code=400,
        )
    try:
        result = await _dispatch(input_text)
    except InputTooLargeError as exc:
        return templates.TemplateResponse(
            request, "_report.html", {"error": str(exc)}, status_code=400
        )
    except Exception as exc:  # surface model/parse failures to the UI
        return templates.TemplateResponse(
            request,
            "_report.html",
            {"error": f"Diagnosis failed: {exc}"},
            status_code=502,
        )

    return templates.TemplateResponse(
        request,
        "_report.html",
        {"report_html": renderer.to_html(result)},
    )


async def _dispatch(input_text: str) -> dict:
    """Route through the Band council when enabled, else the in-process path.

    If Band is enabled but times out (council process down), fall back to the
    in-process orchestrator so a demo never dead-ends.
    """
    if settings.band_enabled:
        from .band.submit import submit_and_wait

        report = await submit_and_wait(input_text, timeout=settings.band_timeout)
        if report is not None:
            return report
    return await orchestrator.run(input_text)


@app.post("/diagnose/stream")
async def diagnose_stream(input_text: str = Form("")) -> StreamingResponse:
    input_text = (input_text or "").strip()

    async def generate():
        import json
        if not input_text:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Provide an input to diagnose.'})}\n\n"
            return
        async for chunk in orchestrator.stream(input_text):
            yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok", "band_enabled": settings.band_enabled}
