import os
import logging
import psycopg2
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

# ========= Environment Variables من Railway =========
TOKEN = os.environ.get("TOKEN")
DEVELOPER_ID = int(os.environ.get("DEVELOPER_ID"))
DEVELOPER_USERNAME = os.environ.get("DEVELOPER_USERNAME")
MANDATORY_CHANNEL = os.environ.get("MANDATORY_CHANNEL") # @YourChannel
CHANNEL_ID = int(os.environ.get("CHANNEL_ID")) # -100xxxxxxxxxx
DATABASE_URL = os.environ.get("DATABASE_URL") # Railway بيضيفه تلقائي
# ===================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========= الداتا بيز =========
def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            lang VARCHAR(2) DEFAULT 'ar',
            activated BOOLEAN DEFAULT FALSE,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS activation_codes (
            code VARCHAR(50) PRIMARY KEY,
            used_by BIGINT DEFAULT NULL,
            created_by BIGINT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

def get_user(user_id):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT lang, activated FROM users WHERE user_id = %s", (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result

def add_user(user_id, lang='ar'):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (user_id, lang) VALUES (%s, %s) ON CONFLICT (user_id) DO UPDATE SET lang = %s",
        (user_id, lang, lang)
    )
    conn.commit()
    cur.close()
    conn.close()

def activate_user(user_id, code):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT used_by FROM activation_codes WHERE code = %s", (code,))
    result = cur.fetchone()
    if not result:
        cur.close()
        conn.close()
        return "not_found"
    if result[0] is not None:
        cur.close()
        conn.close()
        return "used"

    cur.execute("UPDATE activation_codes SET used_by = %s WHERE code = %s", (user_id, code))
    cur.execute("UPDATE users SET activated = TRUE WHERE user_id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    return "success"

def add_code(code, created_by):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO activation_codes (code, created_by) VALUES (%s, %s)", (code, created_by))
        conn.commit()
        result = True
    except:
        result = False
    cur.close()
    conn.close()
    return result

def get_stats():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE activated = TRUE")
    active_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM activation_codes WHERE used_by IS NULL")
    available_codes = cur.fetchone()[0]
    cur.close()
    conn.close()
    return total_users, active_users, available_codes

# ========= النصوص =========
TEXTS = {
    "ar": {
        "start": "أهلا بيك في بوت استرجاع الحسابات 👋\n\nاختر اللغة:",
        "not_subscribed": "❌ عشان تستخدم البوت لازم تشترك في القناة الرسمية الأول",
        "join_btn": "📢 اشترك في القناة",
        "check_btn": "✅ تحققت من الاشتراك",
        "not_activated": "🔒 البوت مدفوع\nابعت كود التفعيل اللي خدته من المطور:\n\nلو مش معاك كود، تواصل مع المطور 👇",
        "wrong_code": "❌ كود التفعيل غلط أو مستخدم قبل كده",
        "used_code": "❌ الكود ده مستخدم قبل كده",
        "activated": "✅ تم التفعيل بنجاح! تقدر تستخدم البوت دلوقتي",
        "main_menu": "🔐 *القائمة الرئيسية*\n\nاختر المنصة اللي عايز تسترجع حسابك عليها:",
        "dev_btn": "👨‍💻 المبرمج",
        "back": "🔙 رجوع للقائمة",
        "whatsapp": "WhatsApp واتساب",
        "instagram": "Instagram انستجرام",
        "facebook": "Facebook فيسبوك",
        "tiktok": "TikTok تيك توك",
        "telegram": "Telegram تليجرام",
        "snapchat": "Snapchat سناب",
        "google": "Google جوجل",
        "admin_panel": "🔧 *لوحة التحكم*\n\nاختر أمر:",
        "add_code_btn": "➕ إضافة كود جديد",
        "stats_btn": "📊 الإحصائيات",
        "send_add_code": "ابعت الكود الجديد اللي عايز تضيفه:\n\nمثال: VIP123",
        "code_added": "✅ تم إضافة الكود بنجاح",
        "code_exists": "❌ الكود ده موجود بالفعل",
        "admin_only": "❌ الأمر ده للمبرمج فقط"
    },
    "en": {
        "start": "Welcome to Account Recovery Bot 👋\n\nChoose language:",
        "not_subscribed": "❌ To use the bot, you must join the official channel first",
        "join_btn": "📢 Join Channel",
        "check_btn": "✅ I Joined",
        "not_activated": "🔒 Bot is Paid\n\nSend the activation code you got from the developer:\n\nIf you don't have a code, contact the developer 👇",
        "wrong_code": "❌ Wrong activation code or already used",
        "used_code": "❌ This code has already been used",
        "activated": "✅ Activated successfully! You can use the bot now",
        "main_menu": "🔐 *Main Menu*\n\nChoose the platform you want to recover your account on:",
        "dev_btn": "👨‍💻 Programmer",
        "back": "🔙 Back to Menu",
        "whatsapp": "WhatsApp",
        "instagram": "Instagram",
        "facebook": "Facebook",
        "tiktok": "TikTok",
        "telegram": "Telegram",
        "snapchat": "Snapchat",
        "google": "Google",
        "admin_panel": "🔧 *Admin Panel*\n\nChoose command:",
        "add_code_btn": "➕ Add New Code",
        "stats_btn": "📊 Statistics",
        "send_add_code": "Send the new code you want to add:\n\nExample: VIP123",
        "code_added": "✅ Code added successfully",
        "code_exists": "❌ This code already exists",
        "admin_only": "❌ This command is for Programmer only"
    }
}

# روابط الدعم الرسمية
RECOVERY_LINKS = {
    "whatsapp": {
        "ar": "🔐 *استرجاع حساب واتساب*\n\n1. احذف التطبيق وثبته تاني\n2. دخل رقمك وهيجيلك كود\n3. لو اتقفل بسبب مخالفة:\nhttps://www.whatsapp.com/contact/?subject=messenger\n\n⚠️ متحاولش تستخدم طرق غير رسمية عشان حسابك ميتقفلش نهائي",
        "en": "🔐 *WhatsApp Account Recovery*\n\n1. Delete and reinstall the app\n2. Enter your number to get verification code\n3. If banned for violation:\nhttps://www.whatsapp.com/contact/?subject=messenger\n\n⚠️ Don't use unofficial methods to avoid permanent ban"
    },
    "instagram": {
        "ar": "🔐 *استرجاع حساب انستجرام*\n\n1. من صفحة تسجيل الدخول دوس 'Get help logging in'\n2. لو معطل: https://help.instagram.com/contact/606967319425038\n3. لو مسروق: https://help.instagram.com/368191326593075\n\n📧 تابع إيميلك بعد تقديم الطعن",
        "en": "🔐 *Instagram Account Recovery*\n\n1. From login page tap 'Get help logging in'\n2. If disabled: https://help.instagram.com/contact/606967319425038\n3. If hacked: https://help.instagram.com/368191326593075\n\n📧 Check your email after submitting appeal"
    },
    "facebook": {
        "ar": "🔐 *استرجاع حساب فيسبوك*\n\n1. https://www.facebook.com/hacked\n2. لو معطل: https://www.facebook.com/help/contact/260749603972907\n3. جهز بطاقة هوية لو طلبوها\n\n⏱️ الرد خلال 24-48 ساعة",
        "en": "🔐 *Facebook Account Recovery*\n\n1. https://www.facebook.com/hacked\n2. If disabled: https://www.facebook.com/help/contact/260749603972907\n3. Prepare your ID if requested\n\n⏱️ Response within 24-48 hours"
    },
    "tiktok": {
        "ar": "🔐 *استرجاع حساب تيك توك*\n\n1. من التطبيق: Profile > Settings > Report a problem\n2. لينك الطعن المباشر: https://www.tiktok.com/legal/report/feedback\n3. إيميل الدعم: feedback@tiktok.com\n\n📝 اشرح مشكلتك بالتفصيل",
        "en": "🔐 *TikTok Account Recovery*\n\n1. From app: Profile > Settings > Report a problem\n2. Direct appeal link: https://www.tiktok.com/legal/report/feedback\n3. Support email: feedback@tiktok.com\n\n📝 Explain your issue in detail"
    },
    "telegram": {
        "ar": "🔐 *استرجاع حساب تليجرام*\n\n1. لو الرقم معاك: سجل دخول عادي هيجيلك كود\n2. لو الرقم ضاع: https://telegram.org/support\n3. لو محظور: راسل @SpamBot داخل التطبيق\n\n⚠️ تليجرام مش بيرجع الحسابات بدون الرقم",
        "en": "🔐 *Telegram Account Recovery*\n\n1. If you have the number: login normally to get code\n2. If number lost: https://telegram.org/support\n3. If banned: message @SpamBot inside the app\n\n⚠️ Telegram won't recover accounts without phone number"
    },
    "snapchat": {
        "ar": "🔐 *استرجاع حساب سناب شات*\n\n1. https://support.snapchat.com/en-US/a/locked-account\n2. لو مخترق: https://support.snapchat.com/en-US/i-need-help\n3. اختار 'My account is compromised'\n\n📧 هيردوا على الإيميل المسجل",
        "en": "🔐 *Snapchat Account Recovery*\n\n1. https://support.snapchat.com/en-US/a/locked-account\n2. If hacked: https://support.snapchat.com/en-US/i-need-help\n3. Choose 'My account is compromised'\n\n📧 They'll reply to registered email"
    },
    "google": {
        "ar": "🔐 *استرجاع حساب جوجل*\n\n1. https://accounts.google.com/signin/recovery\n2. جاوب أسئلة الأمان صح\n3. لو Gmail مربوط برقم/إيميل بديل هيرجع بسهولة\n\n🔑 فعل التحقق بخطوتين بعد ما ترجعه",
        "en": "🔐 *Google Account Recovery*\n\n1. https://accounts.google.com/signin/recovery\n2. Answer security questions correctly\n3. If Gmail linked to phone/recovery email it's easy\n\n🔑 Enable 2-Step Verification after recovery"
    }
}

def t(user_id, key):
    user_data = get_user(user_id)
    lang = user_data[0] if user_data else 'ar'
    return TEXTS[lang][key]

async def check_subscription(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("العربية 🇪🇬", callback_data="lang_ar")],
        [InlineKeyboardButton("English 🇺🇸", callback_data="lang_en")]
    ]
    await update.message.reply_text(
        TEXTS["ar"]["start"],
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data.startswith("lang_"):
        lang = query.data.split("_")[1]
        add_user(user_id, lang)

        if not await check_subscription(user_id, context):
            keyboard = [
                [InlineKeyboardButton(t(user_id, "join_btn"), url=f"https://t.me/{MANDATORY_CHANNEL[1:]}")],
                [InlineKeyboardButton(t(user_id, "check_btn"), callback_data="check_sub")]
            ]
            await query.edit_message_text(t(user_id, "not_subscribed"), reply_markup=InlineKeyboardMarkup(keyboard))
            return
        await check_activation(query, user_id)

    elif query.data == "check_sub":
        if await check_subscription(user_id, context):
            await check_activation(query, user_id)
        else:
            await query.answer("❌", show_alert=True)

    elif query.data == "main_menu":
        await show_main_menu(query, user_id)

    elif query.data.startswith("recovery_"):
        platform = query.data.split("_")[1]
        user_data = get_user(user_id)
        lang = user_data[0] if user_data else 'ar'
        text = RECOVERY_LINKS[platform][lang]
        keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data="main_menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

    elif query.data == "admin_panel":
        if user_id!= DEVELOPER_ID:
            await query.answer(t(user_id, "admin_only"), show_alert=True)
            return
        keyboard = [
            [InlineKeyboardButton(t(user_id, "add_code_btn"), callback_data="admin_add_code")],
            [InlineKeyboardButton(t(user_id, "stats_btn"), callback_data="admin_stats")]
        ]
        await query.edit_message_text(t(user_id, "admin_panel"), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    elif query.data == "admin_add_code":
        context.user_data['awaiting_code'] = True
        await query.edit_message_text(t(user_id, "send_add_code"))

    elif query.data == "admin_stats":
        total, active, codes = get_stats()
        lang = get_user(user_id)[0]
        if lang == 'ar':
            text = f"📊 *الإحصائيات*\n\n👥 إجمالي المستخدمين: {total}\n✅ المفعلين: {active}\n🔑 الأكواد المتاحة: {codes}"
        else:
            text = f"📊 *Statistics*\n\n👥 Total users: {total}\n✅ Activated: {active}\n🔑 Available codes: {codes}"
        keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data="admin_panel")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def check_activation(query, user_id):
    user_data = get_user(user_id)
    if not user_data:
        add_user(user_id)
        user_data = ('ar', False)

    if user_data[1] or user_id == DEVELOPER_ID:
        await show_main_menu(query, user_id)
    else:
        keyboard = [[InlineKeyboardButton(t(user_id, "dev_btn"), url=f"https://t.me/{DEVELOPER_USERNAME}")]]
        await query.edit_message_text(t(user_id, "not_activated"), reply_markup=InlineKeyboardMarkup(keyboard))

async def show_main_menu(query, user_id):
    keyboard = [
        [InlineKeyboardButton(t(user_id, "whatsapp"), callback_data="recovery_whatsapp")],
        [InlineKeyboardButton(t(user_id, "instagram"), callback_data="recovery_instagram")],
        [InlineKeyboardButton(t(user_id, "facebook"), callback_data="recovery_facebook")],
        [InlineKeyboardButton(t(user_id, "tiktok"), callback_data="recovery_tiktok")],
        [InlineKeyboardButton(t(user_id, "telegram"), callback_data="recovery_telegram")],
        [InlineKeyboardButton(t(user_id, "snapchat"), callback_data="recovery_snapchat")],
        [InlineKeyboardButton(t(user_id, "google"), callback_data="recovery_google")],
        [InlineKeyboardButton(t(user_id, "dev_btn"), url=f"https://t.me/{DEVELOPER_USERNAME}")]
    ]
    await query.edit_message_text(t(user_id, "main_menu"), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    # لوحة الأدمن - إضافة كود
    if context.user_data.get('awaiting_code') and user_id == DEVELOPER_ID:
        if add_code(text, user_id):
            await update.message.reply_text(t(user_id, "code_added"))
        else:
            await update.message.reply_text(t(user_id, "code_exists"))
        context.user_data['awaiting_code'] = False
        return

    # تفعيل الكود
    user_data = get_user(user_id)
    if not user_data:
        add_user(user_id)
        user_data = ('ar', False)

    if not user_data[1]:
        result = activate_user(user_id, text)
        if result == "success":
            await update.message.reply_text(t(user_id, "activated"))
            keyboard = [
                [InlineKeyboardButton(t(user_id, "whatsapp"), callback_data="recovery_whatsapp")],
                [InlineKeyboardButton(t(user_id, "instagram"), callback_data="recovery_instagram")],
                [InlineKeyboardButton(t(user_id, "facebook"), callback_data="recovery_facebook")],
                [InlineKeyboardButton(t(user_id, "tiktok"), callback_data="recovery_tiktok")],
                [InlineKeyboardButton(t(user_id, "telegram"), callback_data="recovery_telegram")],
                [InlineKeyboardButton(t(user_id, "snapchat"), callback_data="recovery_snapchat")],
                [InlineKeyboardButton(t(user_id, "google"), callback_data="recovery_google")],
                [InlineKeyboardButton(t(user_id, "dev_btn"), url=f"https://t.me/{DEVELOPER_USERNAME}")]
            ]
            await update.message.reply_text(t(user_id, "main_menu"), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
        elif result == "used":
            await update.message.reply_text(t(user_id, "used_code"))
        else:
            await update.message.reply_text(t(user_id, "wrong_code"))

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id!= DEVELOPER_ID:
        await update.message.reply_text(t(user_id, "admin_only"))
        return
    keyboard = [
        [InlineKeyboardButton(t(user_id, "add_code_btn"), callback_data="admin_add_code")],
        [InlineKeyboardButton(t(user_id, "stats_btn"), callback_data="admin_stats")]
    ]
    await update.message.reply_text(t(user_id, "admin_panel"), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
