"""DTOs of the asynchronous write protocol: what an accepted write returns, and how to look its outcome up."""

from __future__ import annotations

from hiaok_core.exception import DomainError

from ...application.model import Accepted, CommandOutcome
from ..i18n import localize
from .common import ApiModel, OrgScoped
from .envelope import CODE_OF_KIND, SUCCESS, ApiResponse


class AcceptedResponse(ApiModel):
    request_id: str
    uuid: str
    status: str = "accepted"

    @classmethod
    def of(cls, accepted: Accepted) -> AcceptedResponse:
        return cls.model_validate(accepted)


def accepted(result: Accepted) -> ApiResponse[AcceptedResponse]:
    return ApiResponse.ok(AcceptedResponse.of(result))


class CommandOutcomeRequest(OrgScoped):
    target_request_id: str


def _message(outcome: CommandOutcome) -> str | None:
    """The failure text was recorded in English when the command ran; show it in the caller's language."""
    if outcome.status != "failed" or outcome.msg is None or outcome.error_code is None:
        return outcome.msg
    return localize(DomainError(outcome.kind or "validation", outcome.error_code, outcome.msg))  # type: ignore[arg-type]


class CommandOutcomeResponse(ApiModel):
    """``status``: ``success`` | ``failed`` | ``pending`` (nothing recorded yet / still retrying / dead-lettered)."""

    request_id: str
    status: str
    command_type: str | None = None
    uuid: str | None = None
    code: int = SUCCESS
    msg: str | None = None
    error_code: str | None = None

    @classmethod
    def of(cls, outcome: CommandOutcome) -> CommandOutcomeResponse:
        return cls(
            request_id=outcome.request_id,
            status=outcome.status,
            command_type=outcome.command_type,
            uuid=outcome.uuid,
            code=CODE_OF_KIND.get(outcome.kind or "", SUCCESS) if outcome.status == "failed" else SUCCESS,
            msg=_message(outcome),
            error_code=outcome.error_code,
        )
