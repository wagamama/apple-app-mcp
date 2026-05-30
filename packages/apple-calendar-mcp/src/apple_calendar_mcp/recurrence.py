"""Recurrence expansion for Apple Calendar event series."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

SUPPORTED_KEYS = {"FREQ", "INTERVAL", "COUNT", "UNTIL", "BYDAY"}
SUPPORTED_FREQS = {"DAILY", "WEEKLY", "MONTHLY", "YEARLY"}
WEEKDAYS = {
    "MO": 0,
    "TU": 1,
    "WE": 2,
    "TH": 3,
    "FR": 4,
    "SA": 5,
    "SU": 6,
}


@dataclass(frozen=True)
class Occurrence:
    event_id: str
    start: str
    end: str


@dataclass(frozen=True)
class ExpansionResult:
    occurrences: list[Occurrence]
    unsupported: bool = False
    reason: str = ""


def expand_occurrences(
    event: dict,
    coverage_start: str,
    coverage_end: str,
    *,
    max_occurrences: int,
) -> ExpansionResult:
    """Return expanded occurrences or an unsupported result."""
    start = _parse_datetime(event["start_date"])
    end = _parse_datetime(event["end_date"])
    window_start = _parse_datetime(coverage_start)
    window_end = _parse_datetime(coverage_end)
    duration = end - start
    recurrence = (event.get("recurrence") or "").strip()

    if not recurrence:
        if _overlaps(start, end, window_start, window_end):
            return ExpansionResult(
                [_occurrence(event["event_id"], start, end)]
            )
        return ExpansionResult([])

    parsed = _parse_recurrence(recurrence)
    if isinstance(parsed, ExpansionResult):
        return parsed

    freq = parsed["FREQ"]
    interval = int(parsed.get("INTERVAL", "1"))
    count = _optional_int(parsed.get("COUNT"))
    until = _optional_datetime(parsed.get("UNTIL"))
    excluded = {
        _parse_datetime(value) for value in event.get("excluded_dates", [])
    }

    occurrences: list[Occurrence] = []
    generated = 0
    for occurrence_start in _iter_candidate_starts(start, freq, interval, parsed):
        if count is not None and generated >= count:
            break
        generated += 1
        if until is not None and occurrence_start > until:
            break
        occurrence_end = occurrence_start + duration
        if occurrence_start in excluded:
            continue
        if _overlaps(occurrence_start, occurrence_end, window_start, window_end):
            occurrences.append(
                _occurrence(event["event_id"], occurrence_start, occurrence_end)
            )
            if len(occurrences) >= max_occurrences:
                break
        if count is None and until is None and occurrence_start >= window_end:
            break

    return ExpansionResult(occurrences)


def _parse_recurrence(value: str) -> dict[str, str] | ExpansionResult:
    parts: dict[str, str] = {}
    for raw_part in value.split(";"):
        if not raw_part:
            continue
        if "=" not in raw_part:
            return ExpansionResult([], True, f"Invalid recurrence part {raw_part}")
        key, raw = raw_part.split("=", 1)
        key = key.upper()
        if key not in SUPPORTED_KEYS:
            return ExpansionResult([], True, f"Unsupported recurrence key {key}")
        parts[key] = raw

    freq = parts.get("FREQ", "").upper()
    if freq not in SUPPORTED_FREQS:
        return ExpansionResult([], True, f"Unsupported FREQ {freq}")
    parts["FREQ"] = freq

    try:
        interval = int(parts.get("INTERVAL", "1"))
        if interval < 1:
            raise ValueError
    except ValueError:
        return ExpansionResult([], True, "INTERVAL must be a positive integer")
    parts["INTERVAL"] = str(interval)

    for key in ("COUNT",):
        if key in parts:
            try:
                if int(parts[key]) < 1:
                    raise ValueError
            except ValueError:
                return ExpansionResult(
                    [], True, f"{key} must be a positive integer"
                )

    if "UNTIL" in parts:
        try:
            _parse_datetime(parts["UNTIL"])
        except ValueError:
            return ExpansionResult([], True, "UNTIL must be a datetime")

    if "BYDAY" in parts:
        days = parts["BYDAY"].split(",")
        bad = [day for day in days if day not in WEEKDAYS]
        if bad:
            return ExpansionResult([], True, f"Unsupported BYDAY {bad[0]}")
        if freq != "WEEKLY":
            return ExpansionResult([], True, "BYDAY is only supported weekly")

    return parts


def _iter_candidate_starts(
    start: datetime, freq: str, interval: int, rule: dict[str, str]
):
    if freq == "DAILY":
        current = start
        while True:
            yield current
            current += timedelta(days=interval)
    elif freq == "WEEKLY" and "BYDAY" in rule:
        weekdays = sorted(WEEKDAYS[day] for day in rule["BYDAY"].split(","))
        week_start = start - timedelta(days=start.weekday())
        while True:
            for weekday in weekdays:
                current = (week_start + timedelta(days=weekday)).replace(
                    hour=start.hour,
                    minute=start.minute,
                    second=start.second,
                    microsecond=start.microsecond,
                )
                if current >= start:
                    yield current
            week_start += timedelta(weeks=interval)
    elif freq == "WEEKLY":
        current = start
        while True:
            yield current
            current += timedelta(weeks=interval)
    elif freq == "MONTHLY":
        offset = 0
        while True:
            yield _add_months(start, offset)
            offset += interval
    elif freq == "YEARLY":
        offset = 0
        while True:
            yield _add_years(start, offset)
            offset += interval


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _optional_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return _parse_datetime(value)


def _optional_int(value: str | None) -> int | None:
    if not value:
        return None
    return int(value)


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _add_years(value: datetime, years: int) -> datetime:
    year = value.year + years
    day = min(value.day, calendar.monthrange(year, value.month)[1])
    return value.replace(year=year, day=day)


def _overlaps(
    start: datetime,
    end: datetime,
    coverage_start: datetime,
    coverage_end: datetime,
) -> bool:
    return start < coverage_end and end > coverage_start


def _occurrence(event_id: str, start: datetime, end: datetime) -> Occurrence:
    return Occurrence(
        event_id=event_id,
        start=_format_datetime(start),
        end=_format_datetime(end),
    )


def _format_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
