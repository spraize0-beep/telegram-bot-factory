import telebot
import sqlite3
import random
import string
import os
from datetime import datetime, timedelta

TOKEN = os.getenv("TOKEN", "8804613735:AAHDj0O244e52Pd_9ibygSZD_pdLAL0AvPY")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@marketing_azef")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8085768728"))
DEV_USERNAME = "devazf" # غيره لليوزر بتاعك

bot = telebot.TeleBot(TOKEN)
conn = sqlite3.connect("bot.db", check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users
            (user_id INTEGER PRIMARY KEY, username TEXT, exp_date TEXT, status TEXT, lang TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS admins
            (admin_id INTEGER PRIMARY KEY)''')
c.execute('''CREATE TABLE IF NOT EXISTS sub_codes
            (code TEXT PRIMARY KEY, days INTEGER, used_by INTEGER DEFAULT NULL)''')
c.execute('''INSERT OR IGNORE INTO admins VALUES (?)''', (ADMIN_ID,))
conn.commit()

TEXTS = {
    "ar": {
        "choose_lang": "اختر اللغة / Choose Language",
        "join_channel": "يجب الاشتراك في القناة أولاً:\n{}",
        "menu": "مرحباً {name}\nاختر الخدمة:",
        "choose_problem": "اختار نوع المشكلة:",
        "choose_report": "اختار نوع البلاغ:",
        "choose_count": "اختر عدد البلاغات:",
        "choose_delay": "اختر الفاصل الزمني بين كل بلاغ:",
        "template_msg": "**{}**\n\n**الرسالة الجاهزة:**\n```{}```\n\n**قدمها هنا:**\n{}\n\n_انسخ الرسالة واملأ الفورم يدوياً_",
        "ready_msg": "**جاهز {} بلاغ**\n\n**الحساب المستهدف:** `{}`\n**الفاصل:** {} ثانية\n**لينك الفورم:** {}\n\n**الرسالة الجاهزة:**\n```{}```\n\n_افتح اللينك واملأ الفورم، استنى {} ثانية وكرر العملية {} مرة_",
        "no_sub": "غير مشترك. أرسل كود الاشتراك لتفعيل الخدمة.",
        "code_enter": "أرسل كود الاشتراك:",
        "code_wrong": "الكود غلط.",
        "code_used": "الكود مستخدم قبل كده.",
        "activated": "تم التفعيل ✅\nالاشتراك ينتهي: {}",
        "admin_panel": "لوحة التحكم:",
        "stats": "المشتركين النشطين: {}\nالأكواد الفارغة: {}",
        "error": "حصل خطأ، ابدأ من الأول بـ /start"
    },
    "en": {
        "choose_lang": "Choose Language / اختر اللغة",
        "join_channel": "You must join the channel first:\n{}",
        "menu": "Welcome {name}\nChoose service:",
        "choose_problem": "Choose problem type:",
        "choose_report": "Choose report type:",
        "choose_count": "Choose report count:",
        "choose_delay": "Choose delay between reports:",
        "template_msg": "**{}**\n\n**Message Template:**\n```{}```\n\n**Submit here:**\n{}\n\n_Copy and submit manually_",
        "ready_msg": "**Ready {} reports**\n\n**Target:** `{}`\n**Delay:** {} seconds\n**Form link:** {}\n\n**Message Template:**\n```{}```\n\n_Open the link, submit, wait {} seconds and repeat {} times_",
        "no_sub": "Not subscribed. Send subscription code to activate.",
        "code_enter": "Send subscription code:",
        "code_wrong": "Wrong code.",
        "code_used": "Code already used.",
        "activated": "Activated ✅\nExpires: {}",
        "admin_panel": "Admin Panel:",
        "stats": "Active users: {}\nEmpty codes: {}",
        "error": "Error, start again with /start"
    }
}

BAN_TYPES = {
    "disabled": {"ar": "حساب معطل", "en": "Account Disabled", "link": "https://help.instagram.com/contact/260345859025179"},
    "action_block": {"ar": "حظر الإجراءات", "en": "Action Block", "link": "https://help.instagram.com/contact/1652567838289083"},
    "shadowban": {"ar": "شادوباند", "en": "Shadowban", "link": "https://help.instagram.com/contact/1652567838289083"},
    "challenge": {"ar": "تحدي الهوية", "en": "Identity Check", "link": "https://help.instagram.com/contact/1580664645601280"},
    "login_issue": {"ar": "مشكلة تسجيل الدخول", "en": "Login Issue", "link": "https://help.instagram.com/contact/1652567838289083"},
    "logout_loop": {"ar": "لوج آوت متكرر", "en": "Logout Loop", "link": "https://help.instagram.com/contact/1652567838289083"},
    "age_restrict": {"ar": "حظر السن", "en": "Age Restriction", "link": "https://help.instagram.com/contact/1750571408884062"},
    "message_restrict": {"ar": "تقييد الرسائل", "en": "Message Restriction", "link": "https://help.instagram.com/contact/1652567838289083"},
    "comment_restrict": {"ar": "تقييد التعليقات", "en": "Comment Restriction", "link": "https://help.instagram.com/contact/1652567838289083"},
    "copyright": {"ar": "حقوق النشر", "en": "Copyright", "link": "https://help.instagram.com/contact/505429837857191"}
}

REPORT_TYPES = {
    "fake": {"ar": "حساب مزيف", "en": "Fake Account", "reason": "impersonation"},
    "spam": {"ar": "سبام", "en": "Spam", "reason": "spam"},
    "harassment": {"ar": "تحرش/تنمر", "en": "Harassment", "reason": "harassment"},
    "hate": {"ar": "خطاب كراهية", "en": "Hate Speech", "reason": "hate"},
    "violence": {"ar": "عنف", "en": "Violence", "reason": "violence"},
    "self_harm": {"ar": "إيذاء النفس", "en": "Self Harm", "reason": "self_harm"},
    "illegal": {"ar": "نشاط غير قانوني", "en": "Illegal Activity", "reason": "illegal"},
    "underage": {"ar": "قاصر", "en": "Underage", "reason": "underage"},
    "copyright": {"ar": "انتهاك حقوق", "en": "Copyright", "reason": "copyright"},
    "scam": {"ar": "احتيال", "en": "Scam", "reason": "scam"}
}

MESSAGES = {
    "disabled": {"ar": "مرحباً دعم انستجرام، تم تعطيل حسابي @{} بالخطأ. لم أخالف القوانين. ارجو المراجعة.",
                 "en": "Hello Instagram Support, my account @{} was disabled by mistake. I did not violate Community Guidelines. Please review."},
    "action_block": {"ar": "مرحباً، حسابي @{} مقيد مؤقتاً. لم استخدم بوتات. ارجو إزالة التقييد.",
                     "en": "Hello, my account @{} is temporarily restricted. I did not use bots. Please remove restriction."},
    "shadowban": {"ar": "مرحباً، منشورات حسابي @{} لا تظهر في الهاشتاج. ارجو الفحص.",
                  "en": "Hello, my account @{} posts don't appear in hashtags. Please check."},
    "challenge": {"ar": "مرحباً دعم، حسابي @{} يحتاج تحقق هوية ولا يعمل. ارجو المساعدة.",
                  "en": "Hello Support, my account @{} requires identity verification but it's not working. Please help."},
    "login_issue": {"ar": "Hello, I cannot log in to my account @{} due to a security issue. Please help me regain access."},
    "logout_loop": {"ar": "مرحباً، حسابي @{} يخرج تلقائياً ولا أستطيع الدخول. ارجو الحل.",
                    "en": "Hello, my account @{} keeps logging out. I cannot access it. Please fix."},
    "age_restrict": {"ar": "مرحباً، حسابي @{} محظور بسبب السن بالخطأ. عمري أكبر من 18 سنة.",
                     "en": "Hello, my account @{} is age restricted by mistake. I am over 18 years old."},
    "message_restrict": {"ar": "مرحباً، الرسائل في حسابي @{} مقيدة. لم أرسل سبام. ارجو إزالة التقييد.",
                         "en": "Hello, my account @{} message feature is restricted. I did not send spam. Please remove."},
    "comment_restrict": {"ar": "مرحباً، التعليقات في حسابي @{} مقيدة بالخطأ. ارجو المراجعة.",
                         "en": "Hello, my account @{} comments are restricted by mistake. Please review."},
    "copyright": {"ar": "مرحباً، تم إزالة منشور من حسابي @{} بسبب حقوق النشر بالخطأ. ارجو المراجعة.",
                  "en": "Hello, a post was removed from my account @{} due to copyright by mistake. Please review."},
    "report_fake": {"ar": "مرحباً، هذا الحساب {} مزيف وينتحل شخصية. ارجو المراجعة والحذف.",
                    "en": "Hello, this account {} is fake and impersonating someone. Please review and remove."},
    "report_spam": {"ar": "مرحباً، هذا الحساب {} ينشر سبام وإزعاج. ارجو الحظر.",
                    "en": "Hello, this account {} is spamming. Please block it."},
    "report_harassment": {"ar": "مرحباً، هذا الحساب {} يقوم بالتحرش والتنمر. ارجو اتخاذ إجراء.",
                          "en": "Hello, this account {} is harassing others. Please take action."},
    "report_hate": {"ar": "مرحباً، هذا الحساب {} ينشر خطاب كراهية. ارجو الحذف.",
                    "en": "Hello, this account {} is posting hate speech. Please remove it."},
    "report_violence": {"ar": "مرحباً، هذا الحساب {} يحرض على العنف. ارجو المراجعة.",
                        "en": "Hello, this account {} is promoting violence. Please review."},
    "report_self_harm": {"ar": "مرحباً، هذا الحساب {} يتحدث عن إيذاء النفس. ارجو التدخل.",
                         "en": "Hello, this account {} is talking about self harm. Please intervene."},
    "report_illegal": {"ar": "مرحباً، هذا الحساب {} يقوم بنشاط غير قانوني. ارجو الحظر.",
                       "en": "Hello, this account {} is doing illegal activity. Please ban it."},
    "report_underage": {"ar": "مرحباً، هذا الحساب {} لشخص أقل من 13 سنة. ارجو الحذف.",
                        "en": "Hello, this account {} belongs to someone under 13. Please remove."},
    "report_copyright": {"ar": "مرحباً، هذا الحساب {} يسرق محتوى محمي بحقوق النشر.",
                         "en": "Hello, this account {} is stealing copyrighted content."},
    "report_scam": {"ar": "مرحباً، هذا الحساب {} يقوم بعملية احتيال. ارجو الحظر.",
                    "en": "Hello, this account {} is running a scam. Please ban it."}
}

user_sessions = {}

def get_lang(user_id):
    c.execute("SELECT lang FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    return row[0] if row else "ar"

def check_channel(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def is_subscribed(user_id):
    c.execute("SELECT exp_date, status FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if not row or row[0] is None:
        return False
    try:
        exp_date = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        return exp_date >= datetime.now() and row[1] == 'active'
    except:
        return False

def is_admin(user_id):
    c.execute("SELECT 1 FROM admins WHERE admin_id=?", (user_id,))
    return c.fetchone() is not None

def generate_code(length=10):
    return 'CODE_' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("العربية", callback_data="lang_ar"),
        telebot.types.InlineKeyboardButton("English", callback_data="lang_en")
    )
    bot.send_message(message.chat.id, "اختر اللغة / Choose Language", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def set_lang(call):
    try:
        lang = call.data.split("_")[1]
        c.execute("INSERT OR REPLACE INTO users(user_id, lang, status) VALUES (?,?,'none')",
                  (call.from_user.id, lang))
        conn.commit()
        check_subscription(call.message, lang)
    except Exception as e:
        print(e)
        bot.send_message(call.message.chat.id, "Error")

def check_subscription(message, lang):
    if check_channel(message.from_user.id):
        show_main_menu(message, lang)
    else:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_ID[1:]}"))
        markup.add(telebot.types.InlineKeyboardButton("Check" if lang=="en" else "تحقق", callback_data="check_sub"))
        bot.send_message(message.chat.id, TEXTS["join_channel"].format(CHANNEL_ID), reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub(call):
    lang = get_lang(call.from_user.id)
    if check_channel(call.from_user.id):
        show_main_menu(call.message, lang)
    else:
        bot.answer_callback_query(call.id, "Not subscribed yet" if lang=="en" else "لسه مش مشترك")

def show_main_menu(message, lang):
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton("فك الباند" if lang=="ar" else "Unban Account", callback_data="unban"),
        telebot.types.InlineKeyboardButton("تبنيد حساب" if lang=="ar" else "Report Account", callback_data="report_menu")
    )
    markup.add(
        telebot.types.InlineKeyboardButton("المبرمج" if lang=="ar" else "Developer", url=f"https://t.me/{DEV_USERNAME}"),
        telebot.types.InlineKeyboardButton("كود اشتراك" if lang=="ar" else "Subscription Code", callback_data="sub_code")
    )
    bot.send_message(message.chat.id, TEXTS["menu"].format(name=message.from_user.first_name), reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "unban")
def unban_menu(call):
    if not is_subscribed(call.from_user.id):
        lang = get_lang(call.from_user.id)
        bot.send_message(call.from_user.id, TEXTS["no_sub"])
        return

    lang = get_lang(call.from_user.id)
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    for key, val in BAN_TYPES.items():
        markup.add(telebot.types.InlineKeyboardButton(val[lang], callback_data=f"ban_{key}"))
    bot.send_message(call.from_user.id, TEXTS["choose_problem"], reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ban_"))
def send_template(call):
    try:
        ban_type = call.data.split("_")[1]
        lang = get_lang(call.from_user.id)
        data = BAN_TYPES[ban_type]
        template = MESSAGES[ban_type][lang].format(call.from_user.username or "username")
        msg = TEXTS["template_msg"].format(data[lang], template, data["link"])
        bot.send_message(call.from_user.id, msg, parse_mode="Markdown")
    except Exception as e:
        print(e)
        bot.send_message(call.from_user.id, TEXTS["error"])

@bot.callback_query_handler(func=lambda call: call.data == "report_menu")
def report_menu(call):
    if not is_subscribed(call.from_user.id):
        lang = get_lang(call.from_user.id)
        bot.send_message(call.from_user.id, TEXTS["no_sub"])
        return

    lang = get_lang(call.from_user.id)
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    for key, val in REPORT_TYPES.items():
        markup.add(telebot.types.InlineKeyboardButton(val[lang], callback_data=f"rep_{key}"))
    bot.send_message(call.from_user.id, TEXTS["choose_report"], reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("rep_"))
def get_report_target(call):
    try:
        report_type = call.data.split("_")[1]
        user_id = call.from_user.id
        lang = get_lang(user_id)
        user_sessions[user_id] = {"report_type": report_type}

        target_msg = "أرسل رابط الحساب أو اليوزرنيم:" if lang=="ar" else "Send account link or username:"
        bot.send_message(user_id, target_msg)
        bot.register_next_step_handler(call.message, get_report_count)
    except Exception as e:
        print(e)

def get_report_count(message):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    user_sessions[user_id]["target"] = message.text.strip()

    markup = telebot.types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        telebot.types.InlineKeyboardButton("1", callback_data="count_1"),
        telebot.types.InlineKeyboardButton("3", callback_data="count_3"),
        telebot.types.InlineKeyboardButton("5", callback_data="count_5"),
        telebot.types.InlineKeyboardButton("10", callback_data="count_10"),
        telebot.types.InlineKeyboardButton("20", callback_data="count_20"),
        telebot.types.InlineKeyboardButton("50", callback_data="count_50")
    )
    bot.send_message(user_id, TEXTS["choose_count"], reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("count_"))
def get_delay(call):
    user_id = call.from_user.id
    count = int(call.data.split("_")[1])
    user_sessions[user_id]["count"] = count
    lang = get_lang(user_id)

    markup = telebot.types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        telebot.types.InlineKeyboardButton("30 ثانية", callback_data="delay_30"),
        telebot.types.InlineKeyboardButton("1 دقيقة", callback_data="delay_60"),
        telebot.types.InlineKeyboardButton("2 دقيقة", callback_data="delay_120"),
        telebot.types.InlineKeyboardButton("5 دقائق", callback_data="delay_300"),
        telebot.types.InlineKeyboardButton("10 دقائق", callback_data="delay_600")
    )
    bot.send_message(user_id, TEXTS["choose_delay"], reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delay_"))
def generate_reports(call):
    try:
        user_id = call.from_user.id
        delay = int(call.data.split("_")[1])
        session = user_sessions.get(user_id)
        lang = get_lang(user_id)

        if not session:
            bot.send_message(user_id, TEXTS["error"])
            return

        target = session["target"]
        report_type = session["report_type"]
        count = session["count"]
        link = "https://help.instagram.com/contact/1652567838289083"
        template = MESSAGES[f"report_{report_type}"][lang].format(target)

        msg = TEXTS["ready_msg"].format(count, target, delay, link, template, delay, count)
        bot.send_message(user_id, msg, parse_mode="Markdown")
        del user_sessions[user_id]
    except Exception as e:
        print(e)
        bot.send_message(call.from_user.id, TEXTS["error"])

@bot.callback_query_handler(func=lambda call: call.data == "sub_code")
def ask_code(call):
    lang = get_lang(call.from_user.id)
    bot.send_message(call.from_user.id, TEXTS["code_enter"])
    bot.register_next_step_handler(call.message, activate_code)

def activate_code(message):
    try:
        code = message.text.strip()
        user_id = message.from_user.id
        lang = get_lang(user_id)
        c.execute("SELECT days, used_by FROM sub_codes WHERE code=?", (code,))
        row = c.fetchone()
        if not row:
            bot.send_message(user_id, TEXTS["code_wrong"])
            return
        if row[1] is not None:
            bot.send_message(user_id, TEXTS["code_used"])
            return

        days = row[0]
        exp_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE sub_codes SET used_by=? WHERE code=?", (user_id, code))
        c.execute("UPDATE users SET exp_date=?, status='active' WHERE user_id=?", (exp_date, user_id))
        conn.commit()
        bot.send_message(user_id, TEXTS["activated"].format(exp_date))
        show_main_menu(message, lang)
    except Exception as e:
        print(e)
        bot.send_message(message.chat.id, TEXTS["error"])

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id): return
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton("إنشاء كود", callback_data="admin_create"),
        telebot.types.InlineKeyboardButton("إحصائيات", callback_data="admin_stats"),
        telebot.types.InlineKeyboardButton("إضافة أدمن", callback_data="admin_add"),
        telebot.types.InlineKeyboardButton("حذف أدمن", callback_data="admin_remove")
    )
    bot.send_message(message.chat.id, "لوحة التحكم:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_actions(call):
    if not is_admin(call.from_user.id): return
    action = call.data.split("_")[1]

    if action == "create":
        code = generate_code()
        days = 30
        c.execute("INSERT INTO sub_codes VALUES (?,?, NULL)", (code, days))
        conn.commit()
        bot.send_message(call.message.chat.id, f"تم إنشاء الكود:\n`{code}`\nالمدة: {days} يوم", parse_mode="Markdown")

    elif action == "stats":
        c.execute("SELECT COUNT(*) FROM users WHERE status='active'")
        active = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM sub_codes WHERE used_by IS NULL")
        codes = c.fetchone()[0]
        bot.send_message(call.message.chat.id, TEXTS["stats"].format(active, codes))

    elif action == "add":
        bot.send_message(call.message.chat.id, "أرسل ايدي الأدمن الجديد:")
        bot.register_next_step_handler(call.message, add_admin)

    elif action == "remove":
        bot.send_message(call.message.chat.id, "أرسل ايدي الأدمن اللي عايز تحذفه:")
        bot.register_next_step_handler(call.message, remove_admin)

def add_admin(message):
    try:
        admin_id = int(message.text)
        c.execute("INSERT OR IGNORE INTO admins VALUES (?)", (admin_id,))
        conn.commit()
        bot.send_message(message.chat.id, "تم إضافة الأدمن ✅")
    except:
        bot.send_message(message.chat.id, "ايدي غلط.")

def remove_admin(message):
    try:
        admin_id = int(message.text)
        if admin_id == ADMIN_ID:
            bot.send_message(message.chat.id, "مش هتقدر تحذف الأدمن الرئيسي.")
            return
        c.execute("DELETE FROM admins WHERE admin_id=?", (admin_id,))
        conn.commit()
        bot.send_message(message.chat.id, "تم حذف الأدمن ✅")
    except:
        bot.send_message(message.chat.id, "ايدي غلط.")

print("Bot is running...")
bot.infinity_polling()
