YURISHVAQTI — Avtoservis eslatma MVP
======================================

Ikki qism:

1) dashboard.html — admin uchun vizual demo
   - Brauzerda oching, mashinalar ro'yxati va "necha kun qoldi" hisoblagichini
     ko'rasiz. "Eslatma yuborish" tugmasini bosib, Telegram xabari qanday
     ko'rinishini simulyatsiya qiling. Bu — mijozlarga/hamkorlarga ko'rsatish
     va investorlarga tushuntirish uchun.

2) bot.py — haqiqiy ishlaydigan Telegram bot
   Qadamlar:
   a) @BotFather orqali yangi bot yarating, tokenni oling
   b) pip install python-telegram-bot==21.6 apscheduler
   c) export BOT_TOKEN="..." va export ADMIN_ID="sizning_telegram_id"
   d) python bot.py

   Foydalanish:
   - Mijoz botga /start bosadi -> bot uning chat_id raqamini beradi
   - Admin: /add <mijoz_chat_id> <davlat_raqami> <xizmat_turi> <necha_kundan_keyin>
     Masalan: /add 123456789 01A777BC Salon_himchistkasi 30
   - /list — barcha mashinalarni ko'rsatadi
   - Bot har kuni soat 09:00 da avtomatik tekshiradi va muddati kelgan/
     yaqinlashgan mijozlarga chegirma taklifi bilan xabar yuboradi

Keyingi qadamlar (validatsiyadan keyin):
   - Admin panelni qo'lda /add yozish o'rniga tugmali qilish (mijozlar ko'p bo'lsa)
   - SMS integratsiyasi qo'shish (Eskiz.uz kabi) — Telegram'i yo'q mijozlar uchun
   - Bir nechta avtoservis uchun (multi-tenant) qilish, agar SaaS sifatida sotmoqchi bo'lsangiz
   - Birinchi 3-5 ta avtoservisda BEPUL sinab ko'ring, keyin oylik obuna narxini aniqlang
