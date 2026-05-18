"""Achievements handler — show earned + locked with hints."""

import logging

from utils.keyboards import back_to_menu
from database.queries import get_all_achievements, get_user_achievements

logger = logging.getLogger(__name__)


def handle_achievements(vk_id, text, send):
    """Show two sections: earned achievements and locked ones."""
    all_ach = get_all_achievements()
    earned = get_user_achievements(vk_id)
    earned_ids = {a["id"] for a in (earned or [])}
    earned_map = {a["id"]: a for a in (earned or [])}

    msg = "🏆 Достижения\n\n"

    # Section 1: earned
    earned_list = [a for a in all_ach if a["id"] in earned_ids]
    if earned_list:
        msg += "📗 Полученные:\n"
        for a in earned_list:
            dt = earned_map[a["id"]]["earned_at"]
            ds = dt.strftime("%d.%m.%Y") if hasattr(dt, "strftime") else str(dt)[:10]
            msg += f"  {a['icon']} {a['title']} — {ds}\n"
        msg += "\n"

    # Section 2: locked with hints
    locked = [a for a in all_ach if a["id"] not in earned_ids]
    if locked:
        msg += "📕 Заблокированные:\n"
        for a in locked:
            hint = _hint_for(a)
            msg += f"  {a['icon']} {a['title']}\n    🔒 {hint}\n"

    if not earned_list:
        msg += (
            "Пока нет полученных достижений.\n"
            "Записывай показатели, выполняй челленджи\n"
            "и накапливай серии дней, чтобы открыть их!"
        )

    send(vk_id, msg, keyboard=back_to_menu())


def _hint_for(ach):
    """Generate a hint string based on achievement condition type."""
    ct = ach["condition_type"]
    cv = ach["condition_value"]
    ce = ach.get("condition_extra", "")

    hints = {
        "logs_total": f"Сделай {cv} измерений",
        "profile_filled": "Заполни профиль пациента",
        "challenges_taken": f"Возьми {cv} челлендж(а)",
        "streak_days": f"Достигни серии в {cv} дней подряд",
        "challenges_completed": f"Заверши {cv} челлендж(а)",
        "points_total": f"Накопи {cv} баллов",
    }

    if ct == "logs_type":
        type_names = {"blood_pressure": "давления", "weight": "веса"}
        tname = type_names.get(ce, ce)
        return f"Сделай {cv} измерений {tname}"

    if ct == "steps_total":
        return f"Пройди суммарно {cv:,} шагов".replace(",", " ")

    return hints.get(ct, "Продолжай активно пользоваться ботом")
