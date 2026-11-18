"""Business errors raised by usecases (rules spanning several aggregates)."""

from hiaok_core.factory import ErrorCatalog, ErrorSpec


class UseCaseErrors(ErrorCatalog):
    role_tenant_mismatch = ErrorSpec.validation("role_tenant_mismatch", "roles {roles} belong to another tenant")
    user_disabled = ErrorSpec.validation("user_disabled", "user '{user_uuid}' is disabled")
    employee_inactive = ErrorSpec.validation("employee_inactive", "employee '{employee_uuid}' is not active")
    tenant_required = ErrorSpec.validation("tenant_required", "tenant_uuid is required to open a login account")
    invalid_payload = ErrorSpec.validation("invalid_payload", "{command_type}: {problem}")
    unknown_command = ErrorSpec.validation("unknown_command", "no handler for {command_type}")
    invalid_credentials = ErrorSpec.forbidden("invalid_credentials", "invalid username or password")
