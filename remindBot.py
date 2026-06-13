import asyncio
import dateparser
import re
from datetime import datetime
from aiogram import Bot,Dispatcher,types
from aiogram.filters import Command
from database import init_db, add_reminder, get_due_reminders, mark_sent, list_reminders, delete_reminder, active_reminder, every_add, update_repeat, next_weekly_time
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import os
load_dotenv()
TOKEN = os.getenv('TOKEN')
bot=Bot(token=TOKEN)
dp=Dispatcher()
#Отправка напоминания
async def check_reminders():
    while True:
        reminders = get_due_reminders()
        for rem in reminders:
            rem_id,user_id,remind_text,remind_time,repeat_day=rem
            await bot.send_message(user_id,f'🚨Напоминание {remind_text}')
            if repeat_day is not None:
                update_repeat(rem_id,remind_time,repeat_day)
            else:
                mark_sent(rem_id)
        await asyncio.sleep(60)
#Функция на случай "каждый"
def parse_every(text):
    pattern = r'кажд(?:ый|ую|ое)\s+([а-я]+)\s+в\s+(\d{1,2}:\d{2})'
    match = re.search(pattern, text)
    if match:
        day = match.group(1)
        time = match.group(2)
        remind_text=text[match.end():].strip()
        return day, time, remind_text
    else:
        return None, None, text
@dp.message(Command('start'))
async def start(message: types.Message):
    await message.answer( "🤖 Привет! Я бот-напоминалка.\n\n"
        "📌 Как я работаю:\n"
        "• Отправь дату и текст — я напомню\n"
        "• Понимаю: 'завтра в 19:00', 'через 2 часа'\n"
        "• Могу повторять: 'каждый понедельник в 9:00'\n\n"
        "❓ Команды:\n"
        "/start — это сообщение\n"
        "/remind — создать напоминание\n"
        "/list — все мои напоминания\n"
        "/cancel — отменить")
@dp.message(Command('remind'))
async def remind(message: types.Message):
    text=message.text.split(maxsplit=1)
    if len(text)<2:
        await message.answer('Напиши что напоминать после /remind 😵‍💫')
        return
    user_text=text[1]
    if user_text.startswith('кажд'):
        day, time, remind_text = parse_every(user_text)
        if day and time and remind_text:
            days = {'понедельник': 0,
                    'вторник': 1,
                    'среду': 2,
                    'четверг': 3,
                    'пятницу': 4,
                    'субботу': 5,
                    'воскресенье': 6}
            day = days[day]
            next_time = next_weekly_time(day, time)
            time_str = next_time.strftime('%Y-%m-%d %H:%M:%S')
            every_add(message.from_user.id, remind_text, time_str, day)
            await message.answer(f'🫡 Запомнил: {remind_text}\n⏰ Напомню в: {time_str}')
            return
    date_text=user_text.replace("вечера", "pm").replace("утра", "am").replace("ночи", "pm").replace("дня", "am")
    remind_text=''
    try:
        parts = user_text.split(maxsplit=2)
        date_candidate = f"{parts[0]} {parts[1]}"
        time = datetime.strptime(date_candidate, "%Y-%m-%d %H:%M")
        remind_text = parts[2] if len(parts) > 2 else ""
    except (ValueError, TypeError):
        time=dateparser.parse(date_text, settings={'PREFER_DATES_FROM': 'future'})
        if time is None:
            time_patterns = [
                r'\d{1,2}:\d{2}',  # 19:00
                r'\d{1,2}\s?pm',  # 7pm, 7 pm
                r'\d{1,2}\s?am',  # 7am, 7 am
                r'\d{1,2}\s?вечера',  # 7 вечера
                r'\d{1,2}\s?утра',  # 7 утра
                r'через\s+\d+\s*(часа?|часов?|минуту?|минуты?|минут?)',  # через 2 часа, через 5 минут
                r'через\s+час',  # через час
            ]
            for pattern in time_patterns:
                match = re.search(pattern, user_text)
                if match:
                    end_pos=match.end()
                    date_text=user_text[:end_pos]
                    remind_text=user_text[end_pos:].strip()
                    time = dateparser.parse(date_text, settings={'PREFER_DATES_FROM': 'future'})
                    if time:
                        break
    if time:
        time_str = time.strftime('%Y-%m-%d %H:%M:%S')
        add_reminder(message.from_user.id, remind_text,time_str)
        await message.answer(f'🫡 Запомнил: {remind_text}\n⏰ Напомню в: {time_str}')
    else:
        await message.answer(
            "Не удалось распознать дату и время 🥲\n\n"
            "Пожалуйста, используй один из форматов:\n"
            "• /remind завтра в 19:00 Купить хлеб\n"
            "• /remind 2026-06-15 19:00 Встреча\n"
            "• /remind через 2 часа Выключить чайник\n"
            "• /remind в пятницу в 20:00 Друзья\n"
            "• /remind каждый понедельник в 09:00 Планерка"
        )
@dp.message(Command('list'))
async def list_reminds(message: types.Message):
    reminders = list_reminders(message.from_user.id)
    if not reminders:
        await message.answer("📭 У тебя нет активных напоминаний")
        return
    text = "📋 Твои напоминания:\n\n"
    for rem in reminders:
        rem_id, _, remind_text, remind_time, is_sent, repeat_day = rem
        status = "✅" if is_sent else "❌"
        text += f"{status} #{rem_id} {remind_text} — {remind_time}\n"
    await message.answer(text)
@dp.message(Command('cancel'))
async def cancel(message: types.Message):
    reminders = active_reminder(message.from_user.id)
    if not reminders:
        await message.answer("📭 У тебя нет активных напоминаний")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for rem in reminders:
        rem_id, _, remind_text, remind_time, is_sent, repeat_day = rem
        if is_sent:
            continue
        button=InlineKeyboardButton(
            text=f'{remind_text}-{remind_time}',
            callback_data=f'cancel_{rem_id}'
        )
        keyboard.inline_keyboard.append([button])
    await message.answer("🗑 Выбери напоминание для удаления:", reply_markup=keyboard)
@dp.callback_query()
async def callback(callback: types.CallbackQuery):
    if callback.data.startswith('cancel_'):
        rem_id=int(callback.data.split('_')[1])
        user_id=callback.from_user.id
        deleted=delete_reminder(rem_id, user_id)
        if deleted:
            await callback.message.edit_text("✅ Напоминание удалено!")
        else:
            await callback.message.edit_text("❌ Не найдено")
        await callback.answer()
async def main():
    init_db()
    asyncio.create_task(check_reminders())
    await dp.start_polling(bot)
if __name__ == '__main__':
    asyncio.run(main())