"""Input validation for health measurements."""

import logging
import re

logger = logging.getLogger(__name__)


def validate_blood_pressure(raw: str) -> dict | None:
    """Validate '120/80' format. systolic 60-250, diastolic 40-150."""
    m = re.match(r"^\s*(\d{2,3})\s*[/]\s*(\d{2,3})\s*$", raw)
    if not m:
        return None
    systolic = int(m.group(1))
    diastolic = int(m.group(2))
    if 60 <= systolic <= 250 and 40 <= diastolic <= 150:
        return {"systolic": systolic, "diastolic": diastolic}
    return None


def validate_weight(raw: str) -> dict | None:
    """Validate weight in kg. Range 30-300."""
    m = re.match(r"^\s*(\d{1,3}(?:[.,]\d)?)\s*$", raw.replace(",", "."))
    if not m:
        return None
    weight = float(m.group(1).replace(",", "."))
    if 30 <= weight <= 300:
        return {"weight": round(weight, 1)}
    return None


def validate_blood_sugar(raw: str) -> dict | None:
    """Validate blood glucose mmol/L. Range 1.0-30.0."""
    m = re.match(r"^\s*(\d{1,2}(?:[.,]\d)?)\s*$", raw.replace(",", "."))
    if not m:
        return None
    glucose = float(m.group(1).replace(",", "."))
    if 1.0 <= glucose <= 30.0:
        return {"glucose": round(glucose, 1)}
    return None


def validate_steps(raw: str) -> dict | None:
    """Validate steps count. Range 0-200000."""
    m = re.match(r"^\s*(\d{1,6})\s*$", raw)
    if not m:
        return None
    steps = int(m.group(1))
    if 0 <= steps <= 200000:
        return {"steps": steps}
    return None


def validate_activity_minutes(raw: str) -> dict | None:
    """Validate activity minutes. Range 0-1440."""
    m = re.match(r"^\s*(\d{1,4})\s*$", raw)
    if not m:
        return None
    minutes = int(m.group(1))
    if 0 <= minutes <= 1440:
        return {"minutes": minutes}
    return None
