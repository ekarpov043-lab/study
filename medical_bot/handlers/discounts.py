"""Discounts handler — active/available/locked with progress bars and promo code gen."""

import logging
import re

from utils.state_manager import StateManager
from utils.constants import STATES
from utils.keyboards import back_to_menu

logger = logging.getLogger(__name__)
from database.queries import get_available_discounts, purchase_discount, get_user


def handle_discounts(vk_id, text, send):
    """Show three sections: active promo codes, available to buy, locked."""
    user = get_user(vk_id)
    discounts = get_available_discounts(vk_id)

    if not discounts:
        send(vk_id, "🎁 Пока нет доступных скидок. Загляни позже!", keyboard=back_to_menu())
        return

    msg = "🎁 Мои скидки\n\n"

    # Section 1: active (unused) promo codes
    active = [d for d in discounts if d.get("is_used") is False and d.get("user_promo_code")]
    if active:
        msg += "✅ Активные промокоды:\n"
        for d in active:
            expires = d["user_expires_at"]
            exp_str = expires.strftime("%d.%m.%Y") if hasattr(expires, "strftime") else str(expires)[:10]
            msg += (
                f"  🎁 {d['service_description']}\n"
                f"     Промокод: {d['user_promo_code']}\n"
                f"     Действует до: {exp_str}\n"
                f"     [Покажи на кассе]\n\n"
            )

    # Section 2: available to buy (enough points, not purchased)
    available = [
        d for d in discounts
        if not d.get("user_promo_code")
        and user["total_points"] >= d["required_points"]
    ]
    if available:
        msg += "💫 Доступны для получения:\n"
        for d in available:
            msg += (
                f"  {d['service_description']}\n"
                f"     Стоимость: {d['required_points']} баллов\n"
                f"     У вас: {user['total_points']} баллов ✅\n"
                f"     Чтобы получить: «получить {d['id']}»\n\n"
            )

    # Section 3: locked (not enough points)
    locked = [
        d for d in discounts
        if not d.get("user_promo_code")
        and user["total_points"] < d["required_points"]
    ]
    if locked:
        msg += "🔒 Недоступно (не хватает баллов):\n"
        for d in locked:
            pct = min(int(user["total_points"] / d["required_points"] * 100), 99)
            bar = "▓" * (pct // 10) + "░" * (10 - pct // 10)
            msg += (
                f"  {d['service_description']}\n"
                f"     Нужно: {d['required_points']} баллов\n"
                f"     У вас: {user['total_points']} баллов\n"
                f"     {bar} {pct}%\n\n"
            )

    StateManager.set_state(vk_id, STATES["DISCOUNT_LIST"])
    send(vk_id, msg, keyboard=back_to_menu())


def handle_buy_discount(vk_id, text, send):
    """Process purchase command: 'получить N'."""
    m = re.search(r"получить\s*(\d+)", text.lower())
    if not m:
        send(vk_id, "Напиши «получить N» (например: получить 1)")
        return

    did = int(m.group(1))
    result = purchase_discount(vk_id, did, send_callback=send)

    if result is None:
        send(
            vk_id,
            "❌ Не удалось получить скидку.\n"
            "Причины: не хватает баллов, скидка уже получена или неактивна.",
            keyboard=back_to_menu(),
        )
        return

    msg = (
        f"✅ Скидка получена!\n\n"
        f"🎁 {result['service_description']}\n"
        f"💰 Скидка: -{result['discount_percent']}%\n"
        f"🏷 Промокод: {result['promo_code']}\n"
        f"📅 Действует до: {result['expires_at'].strftime('%d.%m.%Y')}\n\n"
        "Предъяви этот промокод на ресепшене клиники."
    )
    send(vk_id, msg, keyboard=back_to_menu())
