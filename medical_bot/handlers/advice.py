"""Personalized health advice based on measurements, diagnoses, and prescriptions."""

import logging

from api_stub.clinic_api import ClinicAPI

logger = logging.getLogger(__name__)
from database.queries import get_patient_profile, save_advice

clinic_api = ClinicAPI()


def generate_advice(vk_id, measurement_type, value):
    """
    Generate personalized advice after a health measurement.

    Args:
        vk_id: user VK ID
        measurement_type: type of measurement (blood_pressure, weight, etc.)
        value: dict with measurement values

    Returns:
        str with advice text, or empty string if no advice
    """
    patient = clinic_api.get_patient_by_vk_id(vk_id)
    profile = get_patient_profile(vk_id)
    diseases = profile["chronic_diseases"] if profile else patient.get("chronic_diseases", []) if patient else []
    diagnoses = patient["diagnoses"] if patient else []
    prescriptions = patient["prescriptions"] if patient else []

    advice = _rule_based_advice(measurement_type, value, diseases, diagnoses, prescriptions, vk_id)
    if advice:
        save_advice(vk_id, advice)
    return advice


def _rule_based_advice(mtype, value, diseases, diagnoses, prescriptions, vk_id=None):
    """Apply rule-based logic per measurement type."""

    if mtype == "blood_pressure":
        systolic = value.get("systolic", 0)
        diastolic = value.get("diastolic", 0)
        diagnosis_str = ", ".join(diagnoses) if diagnoses else "наблюдение"

        if systolic < 120 and diastolic < 80:
            return "✅ Отличное давление! Продолжай в том же духе."

        if systolic < 90 or diastolic < 60:
            return (
                "🔴 Давление пониженное! Выпей воды, приляг, отдохни.\n"
                "Если состояние не улучшается — обратись к врачу."
            )

        if 120 <= systolic <= 139 and 80 <= diastolic <= 89:
            return (
                "⚠️ Давление немного повышено (предгипертония).\n"
                "Рекомендуем: меньше соли, больше прогулок на свежем воздухе, "
                "контроль стресса."
            )

        if systolic >= 140 or diastolic >= 90:
            med_advice = ""
            if prescriptions:
                med_advice = (
                    f"\nПринял ли ты {prescriptions[0]['medication']}, "
                    f"как назначил врач?"
                )
            return (
                f"🔴 Давление повышено! Учитывая твой диагноз "
                f"({diagnosis_str}), рекомендуется:\n"
                f"• Измерить давление через 15 минут в спокойном состоянии\n"
                f"• Если давление не снижается — обратиться к врачу"
                f"{med_advice}"
            )

        return None

    if mtype == "weight":
        weight = value.get("weight", 0)
        height = 170
        if vk_id:
            p = get_patient_profile(vk_id)
            if p and p.get("height_cm"):
                height = p["height_cm"]
        bmi = weight / ((height / 100) ** 2)
        diagnosis_str = ", ".join(diagnoses) if diagnoses else ""

        if bmi < 18.5:
            return f"⚠️ Вес ниже нормы (ИМТ {bmi:.1f}). Рекомендуем консультацию диетолога."

        if 18.5 <= bmi <= 24.9:
            return f"✅ Вес в норме! ИМТ {bmi:.1f}. Так держать!"

        if 25 <= bmi <= 29.9:
            return (
                f"⚠️ Небольшой лишний вес (ИМТ {bmi:.1f}).\n"
                f"Для твоего здоровья важно следить за этим.\n"
                f"Рекомендуем: сбалансированное питание, регулярная активность."
            )

        if bmi >= 30:
            extra = ""
            if diagnosis_str:
                extra = f"\nС учётом диагноза ({diagnosis_str}) рекомендуем консультацию диетолога."
            return f"🔴 Ожирение (ИМТ {bmi:.1f}) — фактор риска.{extra}"

        return None

    if mtype == "blood_sugar":
        glucose = value.get("glucose", 0)
        has_diabetes = any("диабет" in d.lower() for d in diseases)

        if glucose < 3.9:
            return (
                "🔴 Гипогликемия! Срочно съешь что-то сладкое:\n"
                "• фруктовый сок\n"
                "• сахар (2-3 кубика)\n"
                "• сладкий чай\n"
                "Через 15 минут измерь сахар снова."
            )

        if 3.9 <= glucose <= 5.5:
            return "✅ Сахар в норме! Отличный результат."

        if 5.6 <= glucose <= 6.9:
            extra = ""
            if has_diabetes:
                extra = "\nОбсуди с эндокринологом корректировку дозы препаратов."
            return f"⚠️ Преддиабет (уровень сахара {glucose} ммоль/л).{extra}"

        if glucose >= 7.0:
            extra = ""
            if has_diabetes:
                extra = "\nОбсуди с эндокринологом корректировку терапии."
            return (
                f"🔴 Высокий сахар ({glucose} ммоль/л)!{extra}\n"
                f"Обратись к врачу для коррекции лечения."
            )

        return None

    if mtype == "steps":
        steps = value.get("steps", 0)

        if steps < 3000:
            return (
                "😴 Мало движения сегодня. Даже 10 минут прогулки "
                "улучшат самочувствие и кровообращение!"
            )

        if 3000 <= steps <= 7499:
            return (
                "👟 Неплохо! ВОЗ рекомендует 8000-10000 шагов в день "
                "для поддержания здоровья."
            )

        if 7500 <= steps <= 9999:
            return "💪 Хороший результат! Ещё немного до цели в 10000 шагов."

        if steps >= 10000:
            return "🏆 Цель 10000 шагов достигнута! Ты молодец!"

        return None

    if mtype == "activity_minutes":
        minutes = value.get("minutes", 0)
        if minutes == 0:
            return "😴 Сегодня без активности. Постарайся выделить хотя бы 10 минут на прогулку."
        if minutes < 30:
            return f"👟 {minutes} мин активности — хорошее начало. ВОЗ рекомендует минимум 30 мин в день."
        if minutes >= 30:
            return f"💪 Отлично! {minutes} минут активности — ты выполняешь норму ВОЗ!"
        return None

    if mtype == "medication_intake":
        taken = value.get("taken", [])
        if taken:
            names = ", ".join(taken)
            return f"✅ Приём {names} отмечен. Соблюдение режима лекарств — залог успешного лечения!"
        return None

    return None
