"""Profile card — user stats, level, streak, achievements count."""

import logging

from utils.levels import level_title, next_level_points

logger = logging.getLogger(__name__)
from utils.keyboards import main_menu
from database.queries import (
    get_user, get_user_achievements, get_user_challenges,
    get_completed_challenges, get_available_discounts,
    get_patient_profile,
)
from api_stub.clinic_api import ClinicAPI

clinic_api = ClinicAPI()


def handle_profile(vk_id, text, send):
    """Show full profile card with stats."""
    user = get_user(vk_id)
    if not user:
        send(vk_id, "Пользователь не найден.", keyboard=main_menu())
        return
    patient = clinic_api.get_patient_by_vk_id(vk_id)
    profile = get_patient_profile(vk_id)

    name = f"{patient['first_name']} {patient['last_name']}" if patient else f"{user['first_name']} {user['last_name']}"
    level_name = level_title(user["level"])
    points_to_next = next_level_points(user["total_points"])
    achievements_count = len(get_user_achievements(vk_id) or [])
    completed_count = user["completed_challenges_count"]
    streak = user["current_streak"]
    discounts = get_available_discounts(vk_id)
    available_discounts = sum(1 for d in (discounts or []) if not d.get("is_used") and user["total_points"] >= d["required_points"])

    card = (
        f"👤 Профиль\n\n"
        f"📋 {name}\n"
        f"┌─────────────────────┐\n"
        f"│ 💎 Баллы: {user['total_points']}\n"
        f"│ 🏅 Уровень: {user['level']} — {level_name}\n"
        f"│ {'→ до след. уровня: ' + str(points_to_next) + ' баллов' if points_to_next else '⚡ Максимальный уровень!'}\n"
        f"│ 📈 Выполнено челленджей: {completed_count}\n"
        f"│ 🔥 Серия дней: {streak}\n"
        f"│ 🏆 Достижений: {achievements_count}\n"
        f"│ 🎁 Доступных скидок: {available_discounts}\n"
        f"└─────────────────────┘\n"
    )

    if profile and profile["chronic_diseases"]:
        diseases = ", ".join(profile["chronic_diseases"])
        card += f"\n🩺 Диагнозы: {diseases}"

    send(vk_id, card, keyboard=main_menu())
