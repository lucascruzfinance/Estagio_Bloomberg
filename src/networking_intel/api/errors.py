"""RFC 7807 problem responses. No stack traces or input echoes leave the server."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_MEDIA_TYPE = "application/problem+json"
logger = structlog.get_logger("networking_intel.api")

TITLES = {
    400: "Requisição inválida",
    404: "Recurso não encontrado",
    405: "Método não permitido",
    422: "Parâmetros inválidos",
    429: "Limite de requisições excedido",
    500: "Erro interno",
    503: "Serviço indisponível",
}


class ApiError(Exception):
    def __init__(self, status: int, detail: str, *, code: str = "error") -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail
        self.code = code


def problem(
    request: Request,
    status: int,
    detail: str | None,
    *,
    code: str = "error",
    errors: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"https://networking-intel.local/problems/{code}",
        "title": TITLES.get(status, "Erro"),
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        "request_id": getattr(request.state, "request_id", None),
    }
    if errors:
        body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type=PROBLEM_MEDIA_TYPE, headers=headers)


def _sanitize(errors: list[Any]) -> list[dict[str, Any]]:
    # Pydantic includes the rejected input; never reflect it back to the client.
    return [
        {
            "loc": [str(part) for part in error.get("loc", ())],
            "msg": error.get("msg"),
            "type": error.get("type"),
        }
        for error in errors
    ]


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError) -> JSONResponse:
        return problem(request, exc.status, exc.detail, code=exc.code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return problem(
            request,
            422,
            "Um ou mais parâmetros não respeitam o contrato da API.",
            code="validation",
            errors=_sanitize(list(exc.errors())),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) and exc.status_code < 500 else None
        return problem(request, exc.status_code, detail, code=f"http-{exc.status_code}")

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "unhandled_exception",
            request_id=getattr(request.state, "request_id", None),
            error_type=type(exc).__name__,
            exc_info=exc,
        )
        return problem(
            request, 500, "Falha inesperada; use o request_id para investigar.", code="internal"
        )
