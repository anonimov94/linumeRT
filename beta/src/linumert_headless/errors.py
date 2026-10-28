"""Hierarchia błędów API aplikacji headless.

SPDX-License-Identifier: GPL-2.0-or-later

Każdy błąd ma **kod maszynowy** (``code``), który GUI pokazuje albo tłumaczy, oraz status HTTP,
żeby ten sam błąd działał identycznie przez REST, WebSocket, CLI i SDK. GUI nie musi znać
wyjątków Pythona: transport zawsze oddaje ``{"error": {"code", "message", "details"}}``.

Zasada: błąd przewidywalny (zła wartość, brak pliku, odmowa bezpieczeństwa) to ``ApiError``
z kodem — nie wyjątek nieoczekiwany. Błąd nieoczekiwany wraca jako ``internal`` i jest
logowany po stronie usługi, a GUI dostaje ten sam kształt odpowiedzi.
"""

from __future__ import annotations

from typing import Any


class ApiError(Exception):
    """Błąd zgłaszany klientowi. ``code`` jest częścią kontraktu API."""

    code = "error"
    http_status = 500

    def __init__(self, message: str, *, details: dict[str, Any] | None = None,
                 cause: BaseException | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


class InvalidRequest(ApiError):
    """Parametry nie przeszły walidacji schematu."""

    code = "invalid_request"
    http_status = 400


class NotFound(ApiError):
    """Nie ma programu, narzędzia, osi, maszyny ani operacji o tej nazwie."""

    code = "not_found"
    http_status = 404


class Conflict(ApiError):
    """Operacja sprzeczna z obecnym stanem (np. ruch przy E-STOP, program w AUTO)."""

    code = "conflict"
    http_status = 409


class PermissionDenied(ApiError):
    """Za niski poziom dostępu (role: operator < technolog < serwis)."""

    code = "permission_denied"
    http_status = 403


class SafetyRefused(ApiError):
    """Odmowa z powodu bezpieczeństwa: brak bazowania, aktywny limit, brak zgody operatora."""

    code = "safety_refused"
    http_status = 422


class RateLimited(ApiError):
    """Za dużo poleceń w jednostce czasu (ochrona LinuxCNC przed zalaniem)."""

    code = "rate_limited"
    http_status = 429


class BackendUnavailable(ApiError):
    """Backend maszyny nie odpowiada albo nie jest skonfigurowany."""

    code = "backend_unavailable"
    http_status = 503


class NotImplementedCapability(ApiError):
    """Operacja jest w kontrakcie, ale nie ma jeszcze implementacji headless.

    GUI dostaje ``code = not_implemented`` i ``details.plan`` z wskazaniem, czego brakuje.
    Dzięki temu interfejs może pokazać funkcję jako „w przygotowaniu" zamiast padać.
    """

    code = "not_implemented"
    http_status = 501

    def __init__(self, operation: str, plan: str = ""):
        super().__init__(
            f"operacja {operation} nie ma jeszcze implementacji headless",
            details={"operation": operation, "plan": plan},
        )


class InternalError(ApiError):
    """Błąd nieoczekiwany; szczegóły zostają w dzienniku usługi."""

    code = "internal"
    http_status = 500


__all__ = [
    "ApiError",
    "BackendUnavailable",
    "Conflict",
    "InternalError",
    "InvalidRequest",
    "NotFound",
    "NotImplementedCapability",
    "PermissionDenied",
    "RateLimited",
    "SafetyRefused",
]
