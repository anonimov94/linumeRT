"""Authenticated offline preparation endpoints; independent of CNC commands.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import sqlite3
from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Request, Response
from linumert.machine.schema import MachineConfigError
from linumert.programs.prepare import JobService
from pydantic import BaseModel, ConfigDict, Field


class PrepareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    program: str = Field(min_length=5, max_length=128)
    name: str = Field(min_length=1, max_length=64)
    origin: tuple[Annotated[float, Field(allow_inf_nan=False)],
                  Annotated[float, Field(allow_inf_nan=False)],
                  Annotated[float, Field(allow_inf_nan=False)]] = Field(strict=False)
    offset: str = "G54"


class PreflightRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    job_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    start_mm: tuple[Annotated[float, Field(allow_inf_nan=False)],
                    Annotated[float, Field(allow_inf_nan=False)],
                    Annotated[float, Field(allow_inf_nan=False)]] = Field(strict=False)


class ExecutionConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    job_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    verification_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    target: Literal["sim", "plant"]


def register_jobs(app: FastAPI, service: JobService | None,
                  need_token: Callable[[Request], None]) -> None:
    def enabled(request: Request) -> JobService:
        need_token(request)
        if service is None:
            raise HTTPException(409, "Przygotowanie zadań nie jest skonfigurowane w bramie")
        return service

    def run(action):
        try:
            return action()
        except (ValueError, OSError, sqlite3.Error, MachineConfigError) as error:
            raise HTTPException(409, str(error)) from None

    @app.get("/api/jobs/context")
    def context(request: Request) -> dict:
        need_token(request)
        if service is None:
            return {"available": False, "reason": "Przygotowanie zadań nie jest skonfigurowane"}
        return run(service.context)

    @app.post("/api/jobs/prepare")
    def prepare(request: Request, payload: PrepareRequest) -> dict:
        active = enabled(request)
        return run(lambda: active.prepare(payload.program, payload.name,
                                           payload.origin, payload.offset))

    @app.get("/api/jobs/{name}/archive")
    def archive(request: Request, name: str) -> Response:
        active = enabled(request)
        data = run(lambda: active.archive(name))
        return Response(data, media_type="application/zip", headers={
            "Content-Disposition": f'attachment; filename="{name}.zip"'})

    @app.post("/api/jobs/{name}/preflight")
    def preflight(request: Request, name: str, payload: PreflightRequest) -> dict:
        from linumert_sim.job_preflight import check

        active = enabled(request)
        return run(lambda: active.preflight(name, payload.start_mm, payload.job_id, checker=check))

    @app.post("/api/jobs/{name}/verify")
    def verify_job(request: Request, name: str, payload: PreflightRequest) -> dict:
        from linumert_sim.job_verify import verify

        active = enabled(request)
        return run(lambda: active.preflight(name, payload.start_mm, payload.job_id, checker=verify))

    @app.post("/api/jobs/{name}/execution-config")
    def execution_config(request: Request, name: str, payload: ExecutionConfigRequest) -> Response:
        active = enabled(request)
        data = run(lambda: active.execution_archive(name, payload.job_id,
                                                    payload.verification_id, payload.target))
        return Response(data, media_type="application/zip", headers={
            "Content-Disposition": f'attachment; filename="{name}-{payload.target}.zip"'})
