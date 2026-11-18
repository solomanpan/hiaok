"""Localized messages: ``Accept-Language`` -> ``en`` | ``zh`` | ``ja``.

Business errors are values built from catalog specs (English templates + parameters). The envelope shows them in the
caller's language: the message is matched back to its spec (code and text), the parameters are read out of it and
poured into the translated template from ``messages.py``. Unknown messages stay English.
Request-body validation messages come from pydantic and are not translated.
"""

from __future__ import annotations

import re
import string
from contextvars import ContextVar
from dataclasses import dataclass
from functools import cache
from typing import Final

from hiaok_core.exception import DomainError
from hiaok_core.factory import ErrorCatalog

from .messages import NOT_FOUND, PARAM_WORDS, STATIC, TEMPLATES

LOCALES: Final = ("en", "zh", "ja")
DEFAULT_LOCALE: Final = "en"

_locale: ContextVar[str] = ContextVar("hiaok_locale", default=DEFAULT_LOCALE)


def current_locale() -> str:
    return _locale.get()


def set_locale(locale: str) -> None:
    _locale.set(locale if locale in LOCALES else DEFAULT_LOCALE)


def parse_accept_language(header: str | None, default: str = DEFAULT_LOCALE) -> str:
    """``zh-CN,zh;q=0.9,en;q=0.8`` -> ``zh``: highest ``q`` whose primary subtag is supported."""
    best, best_q = default, -1.0
    for position, item in enumerate((header or "").split(",")):
        tag, _, params = item.strip().partition(";")
        primary = tag.strip().lower().partition("-")[0]
        q = 1.0
        if params.strip().startswith("q="):
            try:
                q = float(params.strip()[2:])
            except ValueError:
                continue
        if primary in LOCALES and q > 0 and q - position * 1e-6 > best_q:
            best, best_q = primary, q - position * 1e-6  # earlier entries win ties
    return best


def _regex(template: str) -> re.Pattern[str]:
    out, seen = "", set[str]()
    for literal, name, _, _ in string.Formatter().parse(template):
        out += re.escape(literal)
        if name:
            out += f"(?P={name})" if name in seen else f"(?P<{name}>.+?)"
            seen.add(name)
    return re.compile(f"^{out}$", re.DOTALL)


@dataclass(frozen=True)
class _Entry:
    template: str
    code: re.Pattern[str]
    message: re.Pattern[str]


@cache
def _index(catalogs: int) -> tuple[_Entry, ...]:
    """Every spec of every catalog (most specific first) + the generic ``not_found``; rebuilt if catalogs grow."""
    specs = [spec for catalog in ErrorCatalog.__subclasses__() for _, spec in catalog.specs()]
    specs.sort(key=lambda s: len(s.placeholders))
    entries = [_Entry(s.template, _regex(s.code), _regex(s.template)) for s in specs]
    entries.append(_Entry(NOT_FOUND, re.compile(r"^.+_not_found$"), _regex(NOT_FOUND)))
    return tuple(entries)


def _word(name: str, value: str, locale: str) -> str:
    return PARAM_WORDS.get(name, {}).get(value, {}).get(locale, value)


def localize(error: DomainError, locale: str | None = None) -> str:
    locale = locale or current_locale()
    if locale == DEFAULT_LOCALE:
        return error.message
    for entry in _index(len(ErrorCatalog.__subclasses__())):
        by_code, by_message = entry.code.match(error.code), entry.message.match(error.message)
        if not (by_code and by_message):
            continue
        template = TEMPLATES.get(entry.template, {}).get(locale)
        if template is None:
            break
        params = {k: _word(k, v, locale) for k, v in {**by_code.groupdict(), **by_message.groupdict()}.items()}
        try:
            return template.format(**params)
        except (KeyError, IndexError):
            break
    return error.message


def static_message(message: str, locale: str | None = None) -> str:
    """Fixed messages ("authentication required", "internal error")."""
    return STATIC.get(message, {}).get(locale or current_locale(), message)
