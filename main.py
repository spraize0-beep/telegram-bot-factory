import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ========= الإعدادات - عدلها =========
TOKEN = "8804613735:AAGqMkasaRPi6tz9syRAYaGnC65JRdUhY4M"
DEVELOPER_ID = 8085768728 # الأيدي بتاعك على تليجرام
DEVELOPER_USERNAME = "Devazf" # يوزرك بدون @
MANDATORY_CHANNEL = "@Marketing_Azef" # قناة الاشتراك الإجباري
CHANNEL_ID = -1003968712197 # أيدي القناة بالأرقام
ACTIVATION_CODES = {"CODE123", "VIP456", "ADMIN789"} # أكواد التفعيل اللي هتوزعها
# =====================================

logging.basicConfig(level=logging.INFO)

# قاعدة بيانات بسيطة في الميموري
user_lang = {} # user_id: "ar" or "en"
activated_users = set() # المستخدمين اللي فعلوا البوت

# النصوص باللغتين
TEXTS = {
    "ar": {
        "start": "أهلا بيك 👋\nاختر اللغة:",
        "not_subscribed": "❌ لازم تشترك في القناة أول عشان تستخدم البوت",
        "join_btn": "اشترك في القناة",
        "check_btn": "تحققت من الاشتراك ✅",
        "not_activated": "🔒 البوت مدفوع\nابعت كود التفعيل اللي خدته من المطور:",
        "wrong_code": "❌ كود التفعيل غلط. تواصل مع المطور",
        "activated": "✅ تم التفعيل بنجاح! أهلا بيك",
        "main_menu": "القائمة الرئيسية 👇",
        "ban_section": "🚫 قسم الباند",
        "unban_section": "✅ قسم فك الباند",
        "dev_btn": "👨‍💻 تواصل مع المبرمج",
        "ban_types": "اختر نوع الباند:",
        "unban_types": "اختر نوع فك الباند:",
        "back": "🔙 رجوع",
        "whatsapp": "واتساب",
        "facebook": "فيسبوك",
        "instagram": "انستجرام",
        "telegram": "تليجرام",
        "games": "ألعاب",
        "tiktok": "تيك توك"
    },
    "en": {
        "start": "Welcome 👋\nChoose language:",
        "not_subscribed": "❌ You must join the channel first to use the bot",
        "join_btn": "Join Channel",
        "check_btn": "I Joined ✅",
        "not_activated": "🔒 Bot is paid\nSend the activation code you got from the developer:",
        "wrong_code": "❌ Wrong activation code. Contact developer",
        "activated": "✅ Activated successfully! Welcome",
        "main_menu": "Main Menu 👇",
        "ban_section": "🚫 Ban Section",
        "unban_section": "✅ Unban Section",
        "dev_btn": "👨‍💻 Contact Developer",
        "ban_types": "Choose ban type:",
        "unban_types": "Choose unban type:",
        "back": "🔙 Back",
        "whatsapp": "WhatsApp",
        "facebook": "Facebook",
        "instagram": "Instagram",
        "telegram": "Telegram",
        "games": "Games",
        "tiktok": "TikTok"
    }
}

def get_text(user_id, key):
    lang = user_lang.get(user_id, "ar")
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

    # 1. اختيار اللغة
    if query.data.startswith("lang_"):
        lang = query.data.split("_")[1]
        user_lang[user_id] = lang

        # 2. تحقق الاشتراك الإجباري
        if not await check_subscription(user_id, context):
            keyboard = [
                [InlineKeyboardButton(get_text(user_id, "join_btn"), url=f"https://t.me/{MANDATORY_CHANNEL[1:]}")],
                [InlineKeyboardButton(get_text(user_id, "check_btn"), callback_data="check_sub")]
            ]
            await query.edit_message_text(
                get_text(user_id, "not_subscribed"),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        await show_activation_or_menu(query, user_id)

    # 3. تحقق الاشتراك بعد الضغط
    elif query.data == "check_sub":
        if await check_subscription(user_id, context):
            await show_activation_or_menu(query, user_id)
        else:
            await query.answer("لسه مشتركتش", show_alert=True)

    # 4. القائمة الرئيسية
    elif query.data == "main_menu":
        await main_menu(query, user_id)

    # 5. أقسام الباند وفك الباند
    elif query.data == "ban_section":
        await show_ban_types(query, user_id)
    elif query.data == "unban_section":
        await show_unban_types(query, user_id)

    # 6. رجوع
    elif query.data == "back_main":
        await main_menu(query, user_id)

async def show_activation_or_menu(query, user_id):
    if user_id in activated_users or user_id == DEVELOPER_ID:
        await main_menu(query, user_id)
    else:
        await query.edit_message_text(get_text(user_id, "not_activated"))

async def main_menu(query, user_id):
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "ban_section"), callback_data="ban_section")],
        [InlineKeyboardButton(get_text(user_id, "unban_section"), callback_data="unban_section")],
        [InlineKeyboardButton(get_text(user_id, "dev_btn"), url=f"https://t.me/{DEVELOPER_USERNAME}")]
    ]
    await query.edit_message_text(
        get_text(user_id, "main_menu"),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_ban_types(query, user_id):
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "whatsapp"), callback_data="ban_wa")],
        [InlineKeyboardButton(get_text(user_id, "facebook"), callback_data="ban_fb")],
        [InlineKeyboardButton(get_text(user_id, "instagram"), callback_data="ban_ig")],
        [InlineKeyboardButton(get_text(user_id, "telegram"), callback_data="ban_tg")],
        [InlineKeyboardButton(get_text(user_id, "games"), callback_data="ban_games")],
        [InlineKeyboardButton(get_text(user_id, "tiktok"), callback_data="ban_tt")],
        [InlineKeyboardButton(get_text(user_id, "back"), callback_data="back_main")]
    ]
    await query.edit_message_text(
        get_text(user_id, "ban_types"),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_unban_types(query, user_id):
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "whatsapp"), callback_data="unban_wa")],
        [InlineKeyboardButton(get_text(user_id, "facebook"), callback_data="unban_fb")],
        [InlineKeyboardButton(get_text(user_id, "instagram"), callback_data="unban_ig")],
        [InlineKeyboardButton(get_text(user_id, "telegram"), callback_data="unban_tg")],
        [InlineKeyboardButton(get_text(user_id, "games"), callback_data="unban_games")],
        [InlineKeyboardButton(get_text(user_id, "tiktok"), callback_data="unban_tt")],
        [InlineKeyboardButton(get_text(user_id, "back"), callback_data="back_main")]
    ]
    await query.edit_message_text(
        get_text(user_id, "unban_types"),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if text in ACTIVATION_CODES:
        activated_users.add(user_id)
        ACTIVATION_CODES.remove(text) # الكود يستخدم مرة واحدة
        await update.message.reply_text(get_text(user_id, "activated"))
        # اعرض القائمة بعد التفعيل
        keyboard = [
            [InlineKeyboardButton(get_text(user_id, "ban_section"), callback_data="ban_section")],
            [InlineKeyboardButton(get_text(user_id, "unban_section"), callback_data="unban_section")],
            [InlineKeyboardButton(get_text(user_id, "dev_btn"), url=f"https://t.me/{DEVELOPER_USERNAME}")]
        ]
        await update.message.reply_text(
            get_text(user_id, "main_menu"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(get_text(user_id, "wrong_code"))

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
