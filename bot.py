"""
YurishVaqti — Avtoservis eslatma Telegram boti (MVP)
-----------------------------------------------------
Nima qiladi:
  - Avtoservis admini /add buyrug'i orqali mijoz + mashina + xizmat sanasini kiritadi
  - Bot har kuni belgilangan vaqtda (default 09:00) tekshiradi:
    kimning muddati kelib qolgan / yaqinlashgan bo'lsa, o'sha mijozga
    Telegram orqali eslatma + chegirma taklifini yuboradi
  - Mijoz botga /start bosgan bo'lishi kerak (chat_id shu orqali olinadi)

O'rnatish:
  pip install python-telegram-bot==21.6 apscheduler

Ishga tushirish:
  export BOT_TOKEN="sizning_bot_tokeningiz"
  export ADMIN_ID="sizning_telegram_id_raqamingiz"
  python bot.py

Bepul hosting uchun: Railway.app yoki Render.com (free tier) ga
shu papkani yuklab qo'yish yetarli — bot doim ishlab turadi.
"""

import os
import sqlite3
import logging
from datetime import date, datetime, timedelta

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("yurishvaqti")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "PUT_YOUR_TOKEN_HERE")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
DB_PATH = "yurishvaqti.db"
REMIND_DAYS_BEFORE = 3   # muddatdan necha kun oldin eslatish
DISCOUNT_PERCENT = 10


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            chat_id INTEGER PRIMARY KEY,
            full_name TEXT,
            phone TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            plate TEXT,
            service TEXT,
            next_due DATE,
            last_reminded DATE
        )
    """)
    return conn


# ---------- Mijoz tomoni ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    name = update.effective_user.full_name
    conn = db()
    conn.execute(
        "INSERT OR IGNORE INTO customers (chat_id, full_name) VALUES (?, ?)",
        (chat_id, name),
    )
    conn.commit()
    conn.close()
    await update.message.reply_text(
        f"Assalomu alaykum, {name}! 🚗\n\n"
        "Siz YurishVaqti botiga ulandingiz. Endi navbatdagi texnik xizmat "
        "vaqti kelganda sizga shu yerdan eslatib turamiz — birga chegirma "
        "taklifi bilan.\n\n"
        f"Sizning chat ID: {chat_id}\n"
        "(Bu raqamni ustaxona adminiga bering, u sizni tizimga qo'shadi)"
    )


# ---------- Admin tomoni ----------

async def add_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Bu buyruq faqat admin uchun.")
        return
    # /add <mijoz_chat_id> <davlat_raqami> <xizmat_turi> <necha_kundan_keyin>
    try:
        parts = context.args
        cust_chat_id = int(parts[0])
        plate = parts[1]
        days_ahead = int(parts[-1])
        service = " ".join(parts[2:-1])
        next_due = date.today() + timedelta(days=days_ahead)

        conn = db()
        conn.execute(
            "INSERT INTO cars (chat_id, plate, service, next_due) VALUES (?, ?, ?, ?)",
            (cust_chat_id, plate, service, next_due.isoformat()),
        )
        conn.commit()
        conn.close()
        await update.message.reply_text(
            f"✅ Qo'shildi: {plate} — {service} — {next_due.strftime('%d.%m.%Y')}"
        )
    except Exception:
        await update.message.reply_text(
            "Format: /add <mijoz_chat_id> <davlat_raqami> <xizmat_turi> <necha_kundan_keyin>\n"
            "Masalan: /add 123456789 01A777BC Salon_himchistkasi 30"
        )


async def list_cars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    conn = db()
    rows = conn.execute("SELECT plate, service, next_due, chat_id FROM cars ORDER BY next_due").fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("Hozircha mashina qo'shilmagan.")
        return
    text = "📋 Ro'yxat:\n\n"
    for plate, service, next_due, chat_id in rows:
        d = (date.fromisoformat(next_due) - date.today()).days
        text += f"{plate} — {service} — {next_due} ({d} kun) — mijoz:{chat_id}\n"
    await update.message.reply_text(text)


# ---------- Avtomatik eslatma (scheduler) ----------

async def send_due_reminders(app: Application):
    conn = db()
    today = date.today()
    threshold = today + timedelta(days=REMIND_DAYS_BEFORE)
    rows = conn.execute(
        "SELECT id, chat_id, plate, service, next_due, last_reminded FROM cars "
        "WHERE next_due <= ?",
        (threshold.isoformat(),),
    ).fetchall()

    for row_id, chat_id, plate, service, next_due, last_reminded in rows:
        # bugun allaqachon eslatilgan bo'lsa, qayta yubormaymiz
        if last_reminded == today.isoformat():
            continue
        due_date = date.fromisoformat(next_due)
        overdue = (today - due_date).days
        if overdue > 0:
            msg = (f"🚗 {plate} uchun *{service}* muddati {overdue} kun oldin o'tgan.\n"
                   f"Hozir kelsangiz — *{DISCOUNT_PERCENT + 5}% chegirma*!")
        else:
            days_left = (due_date - today).days
            msg = (f"🚗 {plate} uchun *{service}* vaqti yaqinlashmoqda "
                   f"({days_left} kun qoldi).\n"
                   f"Shu hafta kelsangiz — *{DISCOUNT_PERCENT}% chegirma*!")
        try:
            await app.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
            conn.execute(
                "UPDATE cars SET last_reminded=? WHERE id=?",
                (today.isoformat(), row_id),
            )
            conn.commit()
            log.info(f"Reminder sent to {chat_id} for {plate}")
        except Exception as e:
            log.warning(f"Could not message {chat_id}: {e}")
    conn.close()


async def on_startup(app: Application):
    scheduler = AsyncIOScheduler()
    # Har kuni soat 09:00 da tekshiradi. Sinov uchun IntervalTrigger(seconds=30) ishlating.
    scheduler.add_job(send_due_reminders, "cron", hour=9, minute=0, args=[app])
    scheduler.start()
    log.info("Scheduler ishga tushdi — har kuni 09:00 da eslatmalar yuboriladi.")


def main():
    app = Application.builder().token(BOT_TOKEN).post_init(on_startup).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_car))
    app.add_handler(CommandHandler("list", list_cars))
    app.run_polling()


if __name__ == "__main__":
    main()
