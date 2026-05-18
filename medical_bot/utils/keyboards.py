"""VK keyboards for the bot."""

from vk_api.keyboard import VkKeyboard, VkKeyboardColor


def main_menu(registered=True):
    kb = VkKeyboard(one_time=False, inline=False)
    kb.add_button("🎯 Мои челленджи", color=VkKeyboardColor.PRIMARY)
    kb.add_button("📊 Мой прогресс", color=VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("💊 Здоровье сегодня", color=VkKeyboardColor.PRIMARY)
    kb.add_button("🏆 Достижения", color=VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("🎁 Мои скидки", color=VkKeyboardColor.POSITIVE)
    kb.add_button("ℹ️ Помощь", color=VkKeyboardColor.NEGATIVE)
    if not registered:
        kb.add_line()
        kb.add_button("📝 Регистрация", color=VkKeyboardColor.SECONDARY)
    return kb.get_keyboard()


def back_to_menu():
    kb = VkKeyboard(one_time=False, inline=False)
    kb.add_button("🔙 В меню", color=VkKeyboardColor.PRIMARY)
    return kb.get_keyboard()


def confirm_keyboard():
    kb = VkKeyboard(one_time=False, inline=True)
    kb.add_button("✅ Да, это я", color=VkKeyboardColor.POSITIVE)
    kb.add_button("❌ Нет", color=VkKeyboardColor.NEGATIVE)
    return kb.get_keyboard()


def health_type_keyboard():
    kb = VkKeyboard(one_time=False, inline=True)
    kb.add_button("❤️ Давление", color=VkKeyboardColor.PRIMARY)
    kb.add_button("⚖️ Вес", color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("🩸 Сахар крови", color=VkKeyboardColor.PRIMARY)
    kb.add_button("🚶 Активность", color=VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("💊 Приём лекарств", color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("🔙 В меню", color=VkKeyboardColor.NEGATIVE)
    return kb.get_keyboard()


def challenge_action_keyboard():
    kb = VkKeyboard(one_time=False, inline=True)
    kb.add_button("✅ Отметить выполнение", color=VkKeyboardColor.POSITIVE)
    kb.add_button("📋 Все доступные", color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("🔙 В меню", color=VkKeyboardColor.NEGATIVE)
    return kb.get_keyboard()


def take_challenge_keyboard(challenge_id):
    kb = VkKeyboard(one_time=False, inline=True)
    kb.add_button(f"📥 Взять #{challenge_id}", color=VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("🔙 Назад", color=VkKeyboardColor.NEGATIVE)
    return kb.get_keyboard()


def medication_take_keyboard(med_count):
    kb = VkKeyboard(one_time=False, inline=True)
    for i in range(med_count):
        kb.add_button(f"💊 Принял #{i + 1}", color=VkKeyboardColor.POSITIVE)
        if i < med_count - 1:
            kb.add_button("  ", color=VkKeyboardColor.SECONDARY)
        kb.add_line()
    kb.add_button("🔙 В меню", color=VkKeyboardColor.NEGATIVE)
    return kb.get_keyboard()
