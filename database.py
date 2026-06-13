import sqlite3
from datetime import datetime, timedelta
#Расчёт даты
def next_weekly_time(day_of_week, time_str):
    now = datetime.now()
    days_ahead = (day_of_week - now.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    next_date = now + timedelta(days=days_ahead)
    hour, minute = map(int, time_str.split(':'))
    return next_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
#Создание таблицы
def init_db():
    connection = sqlite3.connect('reminders.db')
    cursor = connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS reminders(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    remind_text TEXT,
    remind_time TEXT,
    is_sent INTEGER,
    repeat_day INTEGER   
    )
    ''')
    connection.commit()
    connection.close()
#Добавление в БД времени
def add_reminder(user_id,remind_text,remind_time):
    connection = sqlite3.connect('reminders.db')
    cursor = connection.cursor()
    cursor.execute(
        'INSERT INTO reminders (user_id, remind_text, remind_time, is_sent) VALUES (?, ?, ?, ?)',
        (user_id, remind_text, remind_time,0)
    )
    connection.commit()
    connection.close()
#Проверка отправлялось ли напоминание или нет
def get_due_reminders():
    connection = sqlite3.connect('reminders.db')
    cursor = connection.cursor()
    cursor.execute('SELECT id, user_id, remind_text, remind_time, repeat_day FROM reminders WHERE is_sent = 0')
    rows = cursor.fetchall()
    connection.close()
    now = datetime.now()
    due = []
    for row in rows:
        rem_id, user_id, text, time_str, repeat_day = row
        remind_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        if remind_time <= now:
            due.append(row)
    return due
#Отметка, что сообщение уже отправилось
def mark_sent(reminder_id):
    connection = sqlite3.connect('reminders.db')
    cursor = connection.cursor()
    cursor.execute(
        'UPDATE reminders SET is_sent=1 WHERE id=?',(reminder_id,))
    connection.commit()
    connection.close()
#Список напоминаний
def list_reminders(user_id):
    connection = sqlite3.connect('reminders.db')
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM reminders WHERE user_id=?', (user_id,))
    rows = cursor.fetchall()
    connection.close()
    return rows
#Удаление напоминаний
def delete_reminder(reminder_id, user_id):
    conn = sqlite3.connect('reminders.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM reminders WHERE id = ? AND user_id = ?', (reminder_id, user_id))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted
#Список только активных напоминаний
def active_reminder(user_id):
    connection = sqlite3.connect('reminders.db')
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM reminders WHERE is_sent = 0 AND user_id = ?', (user_id,))
    rows = cursor.fetchall()
    connection.close()
    return rows
#На случай "каждый"
def every_add(user_id,remind_text,remind_time,repeat_day):
    connection = sqlite3.connect('reminders.db')
    cursor = connection.cursor()
    cursor.execute(
        'INSERT INTO reminders (user_id, remind_text, remind_time, repeat_day, is_sent) VALUES (?, ?, ?, ?, ?)',
        (user_id, remind_text, remind_time,repeat_day,0)
    )
    connection.commit()
    connection.close()
#Обновление счётчика
def update_repeat(reminder_id, remind_time_str, repeat_day):
    time_part = remind_time_str.split()[1]
    time_part = time_part[:-3]
    next_time = next_weekly_time(repeat_day, time_part)
    conn = sqlite3.connect('reminders.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE reminders SET remind_time = ? WHERE id = ?',
                   (next_time.strftime('%Y-%m-%d %H:%M:%S'), reminder_id))
    conn.commit()
    conn.close()
#Отображение всего списка БД для веб-админки
def admin_panel():
    connection = sqlite3.connect('reminders.db')
    cursor = connection.cursor()
    cursor.execute('SELECT id,user_id,remind_text,remind_time,repeat_day,is_sent FROM reminders ORDER BY remind_time DESC')
    rows = cursor.fetchall()
    connection.close()
    return rows
#Для удаления напоминаний в веб-админке
def delete_reminders(reminder_id):
    connection = sqlite3.connect('reminders.db')
    cursor = connection.cursor()
    cursor.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))
    connection.commit()
    connection.close()