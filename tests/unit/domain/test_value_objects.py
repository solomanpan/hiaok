import pytest
from support import err, ok

from src.domain.vo import Code
from src.domain.vo.text import PERM_CODE, Email, PhoneNumber, Username, non_blank


@pytest.mark.parametrize("raw", ["admin", "project:create", "security.min_length", "a-b_c"])
def test_code_accepts_valid(raw):
    assert ok(Code.create(raw)).value == raw


@pytest.mark.parametrize("raw", ["", "  ", None, "-leading", "has space", "x" * 65])
def test_code_rejects_invalid(raw):
    assert err(Code.create(raw, "role_code")).code == "invalid_role_code"


@pytest.mark.parametrize("raw", ["*", "project:*", "project:create", "project"])
def test_perm_code_pattern(raw):
    assert Code.create(raw, "perm_code", PERM_CODE).is_ok()


def test_perm_code_rejects_double_colon():
    assert Code.create("a:b:c", "perm_code", PERM_CODE).is_error()


def test_non_blank_strips_and_limits_length():
    assert ok(non_blank("  bob ", "name")) == "bob"
    assert err(non_blank("", "name")).code == "name_required"
    assert err(non_blank("x" * 5, "name", max_len=4)).code == "name_too_long"


def test_username_email_phone():
    assert Username.create("jie.pan").is_ok()
    assert err(Username.create("ab")).code == "invalid_username"
    assert Email.create("a@b.co").is_ok()
    assert err(Email.create("not-an-email")).code == "invalid_email"
    assert ok(Email.optional(None)) is None
    assert ok(PhoneNumber.optional("")) is None
    assert PhoneNumber.create("+81-90-1234-5678").is_ok()
