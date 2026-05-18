"""Level system — 10 medical titles based on total_points."""

import logging

logger = logging.getLogger(__name__)

LEVELS = [
    (0, "Новичок"),
    (100, "Стажёр"),
    (300, "Фельдшер"),
    (600, "Медицинская сестра"),
    (1000, "Врач-интерн"),
    (1500, "Ординатор"),
    (2500, "Врач-специалист"),
    (4000, "Кандидат медицинских наук"),
    (6000, "Доктор медицинских наук"),
    (10000, "Профессор медицины"),
]


def level_from_points(points: int) -> int:
    """Return current level (1-10) based on total points."""
    for i, (threshold, _) in enumerate(LEVELS):
        if points < threshold:
            return i
    return len(LEVELS)


def level_title(level_num: int) -> str:
    """Return human-readable title for level number (1-indexed)."""
    idx = max(0, min(level_num - 1, len(LEVELS) - 1))
    return LEVELS[idx][1]


def next_level_points(points: int) -> int:
    """Return points needed for next level (or 0 if max level)."""
    for threshold, _ in LEVELS:
        if points < threshold:
            return threshold - points
    return 0
