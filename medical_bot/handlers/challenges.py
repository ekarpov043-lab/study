"""Challenges handler — list active, available, take, mark progress."""

import logging

from utils.state_manager import StateManager
from utils.constants import STATES
from utils.keyboards import back_to_menu, challenge_action_keyboard, main_menu

logger = logging.getLogger(__name__)
from database.queries import (
    get_user_challenges, get_matching_challenges, get_patient_profile,
    accept_challenge, update_challenge_progress, get_challenge,
    check_and_award_achievements, add_points,
)
from api_stub.clinic_api import ClinicAPI

clinic_api = ClinicAPI()


def handle_challenges(vk_id, text, send):
    """Entry: show active challenges or route to actions."""
    # Route action buttons from this state
    if "Отметить выполнение" in text:
        StateManager.set_state(vk_id, STATES["CHALLENGE_MARK"])
        handle_mark_done(vk_id, text, send)
        return
    if "Все доступные" in text:
        StateManager.set_state(vk_id, STATES["CHALLENGE_TAKE"])
        handle_take(vk_id, text, send)
        return

    active = get_user_challenges(vk_id)
    if not active:
        send(
            vk_id,
            "🎯 У тебя нет активных челленджей.\n"
            "Нажми «📋 Все доступные» чтобы выбрать новый.",
            keyboard=challenge_action_keyboard(),
        )
        return
    msg = "🎯 Мои активные челленджи:\n\n"
    for uc in active:
        pct = int(uc["progress"] / uc["required_count"] * 100) if uc["required_count"] else 0
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        msg += (
            f"#{uc['challenge_id']} {uc['title']}\n"
            f"  {bar} {pct}%\n"
            f"  {uc['progress']}/{uc['required_count']} | 💎 {uc['reward_points']} баллов\n\n"
        )
    send(vk_id, msg, keyboard=challenge_action_keyboard())


def handle_challenge_action(vk_id, text, send):
    """Route actions: mark done / show all available."""
    if "Отметить выполнение" in text:
        active = get_user_challenges(vk_id)
        if not active:
            send(vk_id, "Нет активных челленджей.", keyboard=challenge_action_keyboard())
            return
        msg = "Напиши номер челленджа, который выполнил:\n"
        for uc in active:
            msg += f"  #{uc['challenge_id']} — {uc['title']} ({uc['progress']}/{uc['required_count']})\n"
        StateManager.set_state(vk_id, STATES["CHALLENGE_MARK"])
        send(vk_id, msg, keyboard=back_to_menu())
        return

    if "Все доступные" in text:
        profile = get_patient_profile(vk_id)
        diseases = profile["chronic_diseases"] if profile else []
        all_c = get_matching_challenges(diseases)
        active_ids = {uc["challenge_id"] for uc in (get_user_challenges(vk_id) or [])}
        available = [c for c in all_c if c["id"] not in active_ids]
        if not available:
            send(vk_id, "Все доступные челленджи уже взяты!", keyboard=challenge_action_keyboard())
            return
        msg = "📋 Доступные челленджи:\n\n"
        for c in available:
            emoji = {"pressure": "❤️", "weight": "⚖️", "activity": "🏃",
                     "medication": "💊", "blood_sugar": "🩸", "steps": "🚶"}.get(c["challenge_type"], "📌")
            msg += (
                f"{emoji} #{c['id']} {c['title']}\n"
                f"  {c['description']}\n"
                f"  🔁 {c['required_count']} раз | 💎 {c['reward_points']} баллов\n"
                f"  Чтобы взять: «возьми {c['id']}»\n\n"
            )
        StateManager.set_state(vk_id, STATES["CHALLENGE_TAKE"])
        send(vk_id, msg, keyboard=back_to_menu())
        return

    send(vk_id, "Используй кнопки ниже.", keyboard=challenge_action_keyboard())


def handle_mark_done(vk_id, text, send):
    """Mark a challenge as done (increment progress)."""
    import re
    m = re.search(r"(\d+)", text)
    if not m:
        send(vk_id, "Напиши номер челленджа (например: 1)", keyboard=back_to_menu())
        return
    cid = int(m.group(1))
    result = update_challenge_progress(vk_id, cid)
    if result is None:
        send(vk_id, "❌ Активный челлендж с таким номером не найден.", keyboard=challenge_action_keyboard())
        return
    if result["status"] == "completed":
        awarded = check_and_award_achievements(vk_id)
        msg = (
            f"🎉 Челлендж «{result['title']}» завершён!\n"
            f"💎 +{result['reward_points']} баллов начислено!\n"
        )
        for a in awarded:
            msg += f"\n{a['icon']} Новое достижение: {a['title']}!"
        send(vk_id, msg, keyboard=challenge_action_keyboard())
    else:
        send(
            vk_id,
            f"✅ Прогресс: {result['progress']}/{result['required_count']}. Так держать!",
            keyboard=challenge_action_keyboard(),
        )
    StateManager.set_state(vk_id, STATES["CHALLENGE_MAIN"])


def handle_take(vk_id, text, send):
    """Take a new challenge."""
    import re
    m = re.search(r"возьми\s*(\d+)", text.lower())
    if not m:
        send(vk_id, "Напиши «возьми N» (например: возьми 1)", keyboard=back_to_menu())
        return
    cid = int(m.group(1))
    ok = accept_challenge(vk_id, cid)
    if ok:
        ch = get_challenge(cid)
        send(
            vk_id,
            f"✅ Челлендж «{ch['title']}» принят!\n"
            f"Начинай выполнять. Удачи! 💪",
            keyboard=challenge_action_keyboard(),
        )
    else:
        send(vk_id, "❌ Не удалось взять челлендж. Возможно он уже активен.", keyboard=back_to_menu())
    StateManager.set_state(vk_id, STATES["CHALLENGE_MAIN"])
