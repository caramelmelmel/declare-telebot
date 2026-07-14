from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/healthz")
async def healthz(request: Request) -> Response:
    checks = {
        "postgres": request.app.state.prompt_repository,
        "redis": request.app.state.dedup_cache,
        "minio": request.app.state.payload_store,
    }
    for name, dependency in checks.items():
        if not await dependency.ping():
            return JSONResponse(status_code=503, content={"status": "degraded", "detail": name})

    return JSONResponse(status_code=200, content={"status": "ok"})
