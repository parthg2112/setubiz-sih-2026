from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from setubiz import __version__
from setubiz.api.routes import router

app = FastAPI(
    title="SetuBiz API",
    version=__version__,
    summary="Hyper-local business advisory and financial structuring for rural micro-entrepreneurs",
    description=(
        "Estimation may be uncertain; decisions never are. Loan structuring, eligibility and "
        "stress tests are deterministic code. The language layer explains, it never decides."
    ),
)

# The PWA is served separately in development; production serves it from the same origin.
# The advisory response is ~130 KB raw (schedules, provenance, per-figure index); on a rural
# link that is the difference between seconds and tens of seconds. Vercel and nginx each add
# their own compression; this covers the bare uvicorn path.
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/healthz", summary="Liveness")
def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
