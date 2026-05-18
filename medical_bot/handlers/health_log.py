"""Health logging FSM — 5 measurement types with validation and advice."""

import logging

from utils.state_manager import StateManager
from utils.constants import STATES
from utils.keyboards import health_type_keyboard, back_to_menu, main_menu

logger = logging.getLogger(__name__)
from utils.validators import (
    validate_blood_pressure, validate_weight,
    validate_blood_sugar, validate_steps, validate_activity_minutes,
)
from database.queries import (
    save_health_log, get_user_challenges, update_challenge_progress,
    add_points, check_and_award_achievements, update_streak,
)
from handlers.advice import generate_advice
from api_stub.clinic_api import ClinicAPI

clinic_api = ClinicAPI()

MEASUREMENT_TO_CHALLENGE = {
    "blood_pressure": "pressure",
    "weight": "weight",
    "blood_sugar": "blood_sugar",
    "steps": "steps",
    "activity_minutes": "activity",
    "medication_intake": "medication",
}


def handle_health_today(vk_id, text, send):
    StateManager.set_state(vk_id, STATES["HEALTH_LOG_TYPE"])
    send(
        vk_id,
        "💊 Выбери тип показателя:\n\n"
        "• ❤️ Давление — систолическое/диастолическое\n"
        "• ⚖️ Вес — масса тела в кг\n"
        "• 🩸 Сахар крови — уровень глюкозы в ммоль/л\n"
        "• 🚶 Активность — шаги или минуты\n"
        "• 💊 Приём лекарств — отметить приём",
        keyboard=health_type_keyboard(),
    )


def handle_select_type(vk_id, text, send):
    if "Давление" in text:
        StateManager.set_state(vk_id, STATES["HEALTH_LOG_PRESSURE"])
        send(vk_id, "❤️ Введи показание в формате:\n120/80\n\nСистолическое (60-250), диастолическое (40-150).", keyboard=back_to_menu())
    elif "Вес" in text:
        StateManager.set_state(vk_id, STATES["HEALTH_LOG_WEIGHT"])
        send(vk_id, "⚖️ Введи вес в кг (например: 75.5)\nДиапазон: 30-300 кг.", keyboard=back_to_menu())
    elif "Сахар" in text:
        StateManager.set_state(vk_id, STATES["HEALTH_LOG_SUGAR"])
        send(vk_id, "🩸 Введи уровень сахара в ммоль/л (например: 5.6)\nДиапазон: 1.0-30.0.", keyboard=back_to_menu())
    elif "Активность" in text:
        StateManager.set_state(vk_id, STATES["HEALTH_LOG_STEPS"])
        send(vk_id, "🚶 Сколько шагов сегодня?\n(или напиши «минут X» для минут активности)\n\nНапример: 8500 или минут 45", keyboard=back_to_menu())
    elif "Приём лекарств" in text or "лекарств" in text:
        StateManager.set_state(vk_id, STATES["HEALTH_LOG_MEDS"])
        patient = clinic_api.get_patient_by_vk_id(vk_id)
        if patient and patient["prescriptions"]:
            msg = "💊 Отметь какие лекарства ты принял сегодня:\n\n"
            for i, p in enumerate(patient["prescriptions"], 1):
                msg += f"#{i} {p['medication']} — {p['schedule']}\n"
            msg += "\nНапиши номера через пробел (например: 1 2 3)"
            send(vk_id, msg, keyboard=back_to_menu())
        else:
            send(vk_id, "У тебя нет назначенных препаратов.", keyboard=health_type_keyboard())
    else:
        send(vk_id, "Выбери тип показателя кнопками.", keyboard=health_type_keyboard())


def handle_input_pressure(vk_id, text, send):
    if text == "🔙 В меню":
        StateManager.set_state(vk_id, STATES["MAIN_MENU"])
        send(vk_id, "Главное меню.", keyboard=main_menu())
        return
    result = validate_blood_pressure(text)
    if not result:
        logger.warning(f"vk_id={vk_id} invalid pressure format: {text}")
        send(vk_id, "❌ Неверный формат. Используй: 120/80\n(систола 60-250, диастола 40-150)")
        return
    _save_and_check(vk_id, "blood_pressure", result, send)
    send(vk_id, f"❤️ Давление {result['systolic']}/{result['diastolic']} сохранено!", keyboard=health_type_keyboard())
    StateManager.set_state(vk_id, STATES["HEALTH_LOG_TYPE"])


def handle_input_weight(vk_id, text, send):
    if text == "🔙 В меню":
        StateManager.set_state(vk_id, STATES["MAIN_MENU"])
        send(vk_id, "Главное меню.", keyboard=main_menu())
        return
    result = validate_weight(text)
    if not result:
        send(vk_id, "❌ Неверный формат. Используй: 75.5 (30-300 кг)")
        return
    _save_and_check(vk_id, "weight", result, send)
    send(vk_id, f"⚖️ Вес {result['weight']} кг сохранён!", keyboard=health_type_keyboard())
    StateManager.set_state(vk_id, STATES["HEALTH_LOG_TYPE"])


def handle_input_sugar(vk_id, text, send):
    if text == "🔙 В меню":
        StateManager.set_state(vk_id, STATES["MAIN_MENU"])
        send(vk_id, "Главное меню.", keyboard=main_menu())
        return
    result = validate_blood_sugar(text)
    if not result:
        send(vk_id, "❌ Неверный формат. Используй: 5.6 (1.0-30.0)")
        return
    _save_and_check(vk_id, "blood_sugar", result, send)
    send(vk_id, f"🩸 Сахар {result['glucose']} ммоль/л сохранён!", keyboard=health_type_keyboard())
    StateManager.set_state(vk_id, STATES["HEALTH_LOG_TYPE"])


def handle_input_activity(vk_id, text, send):
    if text == "🔙 В меню":
        StateManager.set_state(vk_id, STATES["MAIN_MENU"])
        send(vk_id, "Главное меню.", keyboard=main_menu())
        return
    result = None
    mtype = None
    if text.lower().startswith("минут"):
        parts = text.split()
        if len(parts) >= 2:
            result = validate_activity_minutes(parts[1])
            mtype = "activity_minutes"
    if not result:
        result = validate_steps(text)
        mtype = "steps" if result else None
    if not result:
        send(vk_id, "❌ Неверный формат. Напиши число шагов (например: 8500)\nили «минут 45» для минут активности.")
        return
    label = f"шагов {result['steps']}" if mtype == "steps" else f"активность {result['minutes']} мин"
    _save_and_check(vk_id, mtype, result, send)
    send(vk_id, f"🚶 {label} сохранено!", keyboard=health_type_keyboard())
    StateManager.set_state(vk_id, STATES["HEALTH_LOG_TYPE"])


def handle_input_medication(vk_id, text, send):
    if text == "🔙 В меню":
        StateManager.set_state(vk_id, STATES["MAIN_MENU"])
        send(vk_id, "Главное меню.", keyboard=main_menu())
        return
    import re
    nums = re.findall(r"\d+", text)
    if not nums:
        send(vk_id, "Напиши номера препаратов через пробел (например: 1 2 3)")
        return
    patient = clinic_api.get_patient_by_vk_id(vk_id)
    if not patient or not patient["prescriptions"]:
        send(vk_id, "Нет назначений.", keyboard=health_type_keyboard())
        return
    taken = []
    for n in nums:
        idx = int(n) - 1
        if 0 <= idx < len(patient["prescriptions"]):
            taken.append(patient["prescriptions"][idx]["medication"])
    if not taken:
        send(vk_id, "❌ Нет препаратов с такими номерами.")
        return
    result = {"taken": taken, "count": len(taken)}
    _save_and_check(vk_id, "medication_intake", result, send)
    msg = "💊 Отмечено:\n" + "\n".join(f"  ✅ {t}" for t in taken)
    send(vk_id, msg, keyboard=health_type_keyboard())
    StateManager.set_state(vk_id, STATES["HEALTH_LOG_TYPE"])


def _save_and_check(vk_id, mtype, value, send):
    """Save health log, award points, check challenges, check achievements, give advice."""
    save_health_log(vk_id, mtype, value)
    add_points(vk_id, 5)
    send(vk_id, f"+5 ⭐ баллов! Всего: {__get_total_points(vk_id)}")
    update_streak(vk_id)

    challenge_type = MEASUREMENT_TO_CHALLENGE.get(mtype)
    if challenge_type:
        active = get_user_challenges(vk_id)
        for uc in active:
            if uc["challenge_type"] == challenge_type:
                result = update_challenge_progress(vk_id, uc["challenge_id"])
                if result and result["status"] == "completed":
                    awarded = check_and_award_achievements(vk_id)
                    msg = (
                        f"🎉 Челлендж «{result['title']}» завершён!\n"
                        f"💎 +{result['reward_points']} баллов начислено!"
                    )
                    for a in awarded:
                        msg += f"\n🎉 Новое достижение! {a['icon']} {a['title']}\n{a['description']}"
                    send(vk_id, msg)
                    break

    awarded = check_and_award_achievements(vk_id)
    for a in awarded:
        send(vk_id, f"🎉 Новое достижение! {a['icon']} {a['title']}\n{a['description']}")

    advice = generate_advice(vk_id, mtype, value)
    if advice:
        send(vk_id, f"💡 Совет дня:\n{advice}")


def __get_total_points(vk_id):
    from database.queries import get_user
    u = get_user(vk_id)
    return u["total_points"] if u else 0
