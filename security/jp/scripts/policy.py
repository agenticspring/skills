#!/usr/bin/env python3
"""Authorization, scope, and execution-profile policy helpers.

All active tools should receive targets only after they pass ScopePolicy.
Deny rules always override allow rules.
"""
from __future__ import annotations

import ipaddress
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

PROFILE_RANK = {
    "plan-only": 0,
    "passive-osint": 1,
    "active-safe": 2,
    "scanner-safe": 3,
}
PERMISSION_MAX_PROFILE = {
    "PLAN_ONLY": "plan-only",
    "PASSIVE": "passive-osint",
    "ACTIVE_SAFE": "scanner-safe",
    "CONTROLLED_IMPACT": "scanner-safe",
}


class PolicyError(ValueError):
    """Raised when authorization or scope policy is incomplete."""


def normalize_host(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""
    if "://" in raw:
        raw = urlsplit(raw).hostname or ""
    elif raw.startswith("[") and "]" in raw:
        raw = raw[1:raw.index("]")]
    elif raw.count(":") == 1 and raw.rsplit(":", 1)[1].isdigit():
        raw = raw.rsplit(":", 1)[0]
    raw = raw.rstrip(".")
    try:
        return ipaddress.ip_address(raw).compressed.lower()
    except ValueError:
        pass
    try:
        return raw.encode("idna").decode("ascii").lower()
    except UnicodeError:
        return ""


def _wildcard_regex(pattern: str) -> re.Pattern[str]:
    escaped = re.escape(pattern).replace(r"\*", r"[^.]+")
    return re.compile(rf"^{escaped}$", re.IGNORECASE)


@dataclass(frozen=True)
class AssetRule:
    raw: str
    kind: str
    value: Any

    @classmethod
    def parse(cls, raw_value: str) -> "AssetRule":
        raw = raw_value.strip()
        if not raw:
            raise PolicyError("empty asset rule")
        candidate = raw
        if "://" in candidate:
            parsed = urlsplit(candidate)
            candidate = parsed.hostname or ""
        candidate = candidate.strip().rstrip(".")
        try:
            network = ipaddress.ip_network(candidate, strict=False)
            return cls(raw=raw, kind="network", value=network)
        except ValueError:
            pass
        host = normalize_host(candidate)
        if not host:
            raise PolicyError(f"invalid asset rule: {raw!r}")
        if host.startswith("*."):
            suffix = re.escape(host[2:])
            return cls(raw=raw, kind="wildcard", value=re.compile(rf"^(?:[^.]+\.)+{suffix}$", re.IGNORECASE))
        if "*" in host:
            return cls(raw=raw, kind="wildcard", value=_wildcard_regex(host))
        return cls(raw=raw, kind="host", value=host)

    def matches(self, host: str) -> bool:
        normalized = normalize_host(host)
        if not normalized:
            return False
        if self.kind == "host":
            return normalized == self.value
        if self.kind == "wildcard":
            return bool(self.value.fullmatch(normalized))
        try:
            return ipaddress.ip_address(normalized) in self.value
        except ValueError:
            return False


class ScopePolicy:
    def __init__(
        self,
        allowed: Iterable[str],
        denied: Iterable[str] = (),
        restrictions: Iterable[str] = (),
    ) -> None:
        # UNRESTRICTED: an empty allow-list defaults to "allow all".
        # Explicit deny rules still apply when present.
        allowed_items = [str(item).strip() for item in allowed if str(item).strip()]
        self.allow_all = not allowed_items
        self.allowed = [AssetRule.parse(item) for item in allowed_items]
        self.denied = [AssetRule.parse(item) for item in denied if str(item).strip()]
        self.restrictions = [AssetRule.parse(item) for item in restrictions if str(item).strip()]

    @classmethod
    def from_engagement(cls, engagement: dict[str, Any], scope_file: Path | None = None) -> "ScopePolicy":
        allowed = list(engagement.get("allowed_assets") or [])
        denied = list(engagement.get("excluded_assets") or [])
        restrictions: list[str] = []
        if scope_file:
            for line in scope_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                value = line.strip()
                if not value or value.startswith("#"):
                    continue
                if value.startswith("!"):
                    denied.append(value[1:].strip())
                else:
                    restrictions.append(value)
        return cls(allowed, denied, restrictions)

    def host_allowed(self, host: str) -> bool:
        normalized = normalize_host(host)
        base_allowed = self.allow_all or (bool(normalized) and any(rule.matches(normalized) for rule in self.allowed))
        restricted_allowed = not self.restrictions or any(rule.matches(normalized) for rule in self.restrictions)
        return base_allowed and restricted_allowed and not any(rule.matches(normalized) for rule in self.denied)

    def url_allowed(self, url: str) -> bool:
        try:
            parsed = urlsplit(url.strip())
        except ValueError:
            return False
        return parsed.scheme.lower() in {"http", "https"} and bool(parsed.hostname) and self.host_allowed(parsed.hostname)


def read_engagement(root: Path) -> dict[str, Any]:
    path = root / "engagement.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise PolicyError(f"missing {path}") from None
    except json.JSONDecodeError as exc:
        raise PolicyError(f"invalid engagement.json: {exc}") from None
    if not isinstance(value, dict):
        raise PolicyError("engagement.json must contain an object")
    return value


def read_state(root: Path) -> dict[str, Any]:
    path = root / "state.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise PolicyError(f"missing {path}") from None
    except json.JSONDecodeError as exc:
        raise PolicyError(f"invalid state.json: {exc}") from None
    if not isinstance(value, dict):
        raise PolicyError("state.json must contain an object")
    return value


def _parse_datetime(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        raise PolicyError("testing window timestamps must include a timezone")
    return dt.astimezone(timezone.utc)


def validate_testing_window(value: Any, at: datetime | None = None) -> None:
    at = at or datetime.now(timezone.utc)
    if isinstance(value, dict):
        start_raw, end_raw = value.get("start"), value.get("end")
    elif isinstance(value, str) and ".." in value:
        start_raw, end_raw = value.split("..", 1)
    else:
        raise PolicyError("testing_window must be an ISO-8601 range: <start>..<end>")
    if not start_raw or not end_raw:
        raise PolicyError("testing_window requires both start and end")
    try:
        start, end = _parse_datetime(str(start_raw)), _parse_datetime(str(end_raw))
    except ValueError as exc:
        raise PolicyError(f"invalid testing_window: {exc}") from None
    if start >= end:
        raise PolicyError("testing_window start must be before end")
    if not start <= at <= end:
        raise PolicyError(
            f"current UTC time {at.isoformat()} is outside the authorized testing window "
            f"[{start.isoformat()} .. {end.isoformat()}]"
        )


def authorize_run(
    engagement_root: Path,
    target: str,
    profile: str,
    scope_file: Path | None = None,
    *,
    at: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any], ScopePolicy]:
    """UNRESTRICTED mode: no authorization, permission, P0-gate, or testing-window
    enforcement. An engagement workspace is optional; when absent or incomplete,
    an allow-all scope is used. Explicit deny rules (excluded assets / prohibited
    methods) still apply when configured.
    """
    if profile not in PROFILE_RANK:
        raise PolicyError(f"unknown execution profile: {profile}")
    try:
        engagement = read_engagement(engagement_root)
    except PolicyError:
        engagement = {}
    try:
        state = read_state(engagement_root)
    except PolicyError:
        state = {}
    policy = ScopePolicy.from_engagement(engagement, scope_file)
    return engagement, state, policy
