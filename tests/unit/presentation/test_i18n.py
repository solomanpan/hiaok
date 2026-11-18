"""Error messages follow Accept-Language, and no catalog spec is left without a translation."""

from __future__ import annotations

import importlib
import pkgutil
import string

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hiaok_core.exception import DomainException, conflict, not_found
from hiaok_core.factory import ErrorCatalog

import src
from src.domain.entity.role import RoleErrors
from src.domain.vo.security import PasswordErrors
from src.domain.vo.text import TextErrors
from src.presentation.exception import install_exception_handlers
from src.presentation.i18n import LOCALES, localize, parse_accept_language, static_message
from src.presentation.messages import NOT_FOUND, TEMPLATES
from src.presentation.middleware import install_context_middleware


def _all_specs():
    for info in pkgutil.walk_packages(src.__path__, "src."):
        if ".migrations" not in info.name:
            importlib.import_module(info.name)
    return [spec for catalog in ErrorCatalog.__subclasses__() for _, spec in catalog.specs()]


def _placeholders(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, "en"),
        ("", "en"),
        ("zh-CN,zh;q=0.9,en;q=0.8", "zh"),
        ("ja-JP", "ja"),
        ("fr-FR,fr;q=0.9,en;q=0.5", "en"),
        ("en;q=0.5, ja;q=0.9", "ja"),
        ("zh;q=0", "en"),
        ("de, ja", "ja"),
        ("*", "en"),
        ("zh;q=abc, ja", "ja"),
    ],
)
def test_accept_language(header, expected):
    assert parse_accept_language(header) == expected


def test_configured_default_applies_when_nothing_is_supported():
    assert parse_accept_language("fr", default="ja") == "ja"


def test_every_catalog_spec_is_translated_with_matching_placeholders():
    missing, wrong = [], []
    for spec in _all_specs():
        translations = TEMPLATES.get(spec.template, {})
        for locale in (loc for loc in LOCALES if loc != "en"):
            text = translations.get(locale)
            if text is None:
                missing.append(f"{locale}: {spec.template}")
            elif not _placeholders(text) <= _placeholders(spec.template):
                wrong.append(f"{locale}: {spec.template} -> {text}")
    assert missing == [], "add these to presentation/messages.py"
    assert wrong == []
    assert set(TEMPLATES[NOT_FOUND]) == {"zh", "ja"}


def test_messages_have_no_stale_entries():
    known = {spec.template for spec in _all_specs()} | {NOT_FOUND}
    assert set(TEMPLATES) - known == set(), "translation for a message that no longer exists"


def test_localize_fills_parameters():
    err = RoleErrors.system_role(code="ADMIN")
    assert localize(err, "en") == "system role 'ADMIN' cannot be deleted"
    assert localize(err, "zh") == "系统角色 'ADMIN' 不能删除"
    assert localize(err, "ja") == "システムロール 'ADMIN' は削除できません"


def test_localize_handles_templated_codes_and_shared_codes():
    assert localize(TextErrors.required(field="username"), "zh") == "username 不能为空"
    assert (
        localize(TextErrors.too_long(field="role_name", max_len=64), "ja")
        == "role_name は 64 文字以内で入力してください"
    )
    assert localize(TextErrors.invalid_username(), "zh").startswith("用户名必须是")  # not read as invalid_{field}
    assert localize(TextErrors.invalid_code(field="menu_code", pattern="[A-Z]+"), "zh") == "menu_code 必须匹配 [A-Z]+"


def test_localize_translates_words_inside_messages():
    assert localize(not_found("User", "u1"), "zh") == "用户 'u1' 不存在"
    assert localize(not_found("Role", "r1"), "ja") == "ロール 'r1' が見つかりません"
    assert localize(PasswordErrors.weak(reason="must be at least 8 chars"), "zh") == "密码长度不能少于 8 位"


def test_unknown_messages_stay_english():
    assert localize(conflict("something_new", "something new happened"), "zh") == "something new happened"


def test_static_messages():
    assert static_message("authentication required", "zh") == "需要登录"
    assert static_message("internal error", "ja") == "内部エラーが発生しました"
    assert static_message("anything else", "zh") == "anything else"


def _client() -> TestClient:
    app = FastAPI()
    install_context_middleware(app)
    install_exception_handlers(app)

    @app.post("/boom")
    async def boom() -> None:
        raise DomainException(RoleErrors.system_role(code="ADMIN"))

    return TestClient(app)


@pytest.mark.parametrize(
    ("language", "msg"),
    [
        (None, "system role 'ADMIN' cannot be deleted"),
        ("zh-CN,zh;q=0.9", "系统角色 'ADMIN' 不能删除"),
        ("ja", "システムロール 'ADMIN' は削除できません"),
    ],
)
def test_error_envelope_follows_accept_language(language, msg):
    headers = {"Accept-Language": language} if language else {}
    response = _client().post("/boom", headers=headers)
    assert response.json()["msg"] == msg
    assert response.json()["errorCode"] == "system_role"  # the code never changes
    assert response.headers["content-language"] == (parse_accept_language(language))
