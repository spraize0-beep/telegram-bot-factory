from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.enums import ParseMode, ChatMemberStatus
from pyrogram.errors import FloodWait, PeerFlood, UserDeactivatedBan, PhoneCodeInvalid, SessionPasswordNeeded, UserDeactivated, AuthKeyUnregistered
import asyncio, json, os, time, random, pickle
from datetime import datetime, timedelta

API_ID = int(os.environ.get("API_ID", 33595004))
API_HASH = os.environ.get("API_HASH", "cbd1066ed026997f2f4a7c4323b7bda7")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8842241824:AAEd8ORic2uvKkqBCrjgKR-o5SRbgNbv-yE")
DEVELOPER_ID = int(os.environ.get("DEVELOPER_ID", 8085768728))
SUBSCRIPTION_PRICE = 3
MAX_ACCOUNTS = 20
FORCE_SUB_CHANNEL = os.environ.get("@marketing_azef", "")

PAYMENT_METHODS = {
    "Aptos": "0xef884077ac54475223014b9dcc1e54085bd979e37f69094f3267886517873c71",
    "BEP20": "0x11a34390ce1526efd7db3e5810d58decb74d9f9f",
    "TRC20": "TSirS7HGCcW2nBkBPNJAcrunbtr4grrfSM",
    "LTC": "ltc1qw9s9mu6rlk3jvuycv7eacthm08k9k59d8htmxq",
    "TON": "UQBDg5OGKVUfKUiW2ImekLxu16VrFgtPEEefk6Of-GF6U2BA"
}

bot = Client("subscription_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
DB_FILE = "db.json"
SESSIONS_DIR = "sessions"
ENTITIES_DIR = "entities"
os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(ENTITIES_DIR, exist_ok=True)

userbots = {}
temp_clients = {}
publish_tasks = {}

def init_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({
                "users": {},
                "accounts": {},
                "pending_payments": {},
                "waiting_for": {},
                "admins": [str(DEVELOPER_ID)],
                "banned_users": [],
                "stats": {"total_users": 0}
            }, f)

def load_db():
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_user_data(user_id):
    db = load_db()
    user_id = str(user_id)
    if user_id not in db["users"]:
        db["users"][user_id] = {
            "subscription_end": 0,
            "welcome_enabled": True,
            "reply_enabled": True,
            "welcome_message": "أهلا بيك نورت 🌟",
            "reply_message": "",
            "protection_level": 1,
            "publish_interval": 1,
            "publish_messages": ["", "", "", ""],
            "publish_buttons": [["زر1", "زر2"], ["زر3", "زر4"], ["زر5", "زر6"], ["زر7", "زر8"]],
            "groups": [],
            "active_account_index": 0
        }
        save_db(db)
    return db["users"][user_id]

def save_message_entities(user_id, msg_index, message: Message):
    path = f"{ENTITIES_DIR}/{user_id}_{msg_index}.pkl"
    data = {
        "text": message.text or message.caption or "",
        "entities": message.entities or message.caption_entities or []
    }
    with open(path, "wb") as f:
        pickle.dump(data, f)

def load_message_entities(user_id, msg_index):
    path = f"{ENTITIES_DIR}/{user_id}_{msg_index}.pkl"
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    return None

async def check_subscription(user_id):
    db = load_db()
    if str(user_id) in db["banned_users"]:
        return False
    user = get_user_data(user_id)
    if FORCE_SUB_CHANNEL:
        try:
            member = await bot.get_chat_member(FORCE_SUB_CHANNEL, user_id)
            if member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                return False
        except:
            return False
    return user.get("subscription_end", 0) > time.time()

def is_admin(user_id):
    db = load_db()
    return str(user_id) in db["admins"]

def main_keyboard(user_id):
    buttons = [
        [InlineKeyboardButton("👤 إدارة الحسابات", callback_data="manage_accounts")],
        [InlineKeyboardButton("📢 إعدادات النشر", callback_data="publish_settings")],
        [InlineKeyboardButton("🤖 الرد التلقائي", callback_data="auto_reply")],
        [InlineKeyboardButton("🛡️ الحماية Anti-Flood", callback_data="protection")],
        [InlineKeyboardButton("✨ مميزات البوت", callback_data="features")],
        [InlineKeyboardButton("📦 Source", url="https://t.me/vip6705"), InlineKeyboardButton("🖥️ Servers", url="https://t.me/Vpsazef")],
        [InlineKeyboardButton("🔐 الاشتراك", callback_data="subscription")]
    ]
    if is_admin(user_id):
        buttons.append([InlineKeyboardButton("⚙️ لوحة الأدمن", callback_data="admin_panel")])
    else:
        buttons.append([InlineKeyboardButton("👨‍💻 Programmer", url="https://t.me/Devazf")])
    return InlineKeyboardMarkup(buttons)

def admin_panel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("💳 طلبات الاشتراك", callback_data="admin_payments")],
        [InlineKeyboardButton("📢 إذاعة", callback_data="admin_broadcast")],
        [InlineKeyboardButton("➕ إضافة أدمن", callback_data="admin_add")],
        [InlineKeyboardButton("🚫 حظر مستخدم", callback_data="admin_ban")],
        [InlineKeyboardButton("✅ فك حظر", callback_data="admin_unban")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="back_main")]
    ])

def accounts_keyboard(user_id):
    db = load_db()
    accounts = db["accounts"].get(str(user_id), [])
    user_data = get_user_data(user_id)
    active_index = user_data.get("active_account_index", 0)
    buttons = []
    for i, acc in enumerate(accounts):
        if str(user_id) in userbots and i in userbots[str(user_id)]:
            flood_until = userbots[str(user_id)][i].get("flood_until", 0)
            if flood_until > time.time():
                status = "🟡 فلود"
            elif userbots[str(user_id)][i].get("publishing"):
                status = "🟢 نشر"
            else:
                status = "🟢 شغال"
        else:
            status = "🔴 متوقف"
        prefix = "⭐ " if i == active_index else ""
        buttons.append([InlineKeyboardButton(f"{prefix}{status} {acc['phone']}", callback_data=f"acc_{i}")])
    buttons.append([InlineKeyboardButton("➕ إضافة حساب", callback_data="add_account")])
    buttons.append([InlineKeyboardButton("🔄 تبديل الحساب النشط", callback_data="switch_account")])
    buttons.append([InlineKeyboardButton("⬅️ رجوع", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)

def account_control_keyboard(index, user_id):
    acc_active = False
    publishing = False
    if str(user_id) in userbots and index in userbots[str(user_id)]:
        acc_active = True
        publishing = userbots[str(user_id)][index].get("publishing", False)
    toggle_publish_text = "⏸️ إيقاف النشر" if publishing else "▶️ تفعيل النشر"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ تشغيل الحساب" if not acc_active else "⏸️ إيقاف الحساب", callback_data=f"toggle_acc_{index}")],
        [InlineKeyboardButton(toggle_publish_text, callback_data=f"toggle_publish_{index}")],
        [InlineKeyboardButton("📊 حالة الحساب", callback_data=f"status_{index}")],
        [InlineKeyboardButton("👥 جلب المجموعات", callback_data=f"getgroups_{index}")],
        [InlineKeyboardButton("📤 نشر الآن", callback_data=f"publishnow_{index}")],
        [InlineKeyboardButton("🗑️ حذف الحساب", callback_data=f"delacc_{index}")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="manage_accounts")]
    ])

def publish_settings_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ الرسالة 1", callback_data="edit_msg_0"), InlineKeyboardButton("✍️ الرسالة 2", callback_data="edit_msg_1")],
        [InlineKeyboardButton("✍️ الرسالة 3", callback_data="edit_msg_2"), InlineKeyboardButton("✍️ الرسالة 4", callback_data="edit_msg_3")],
        [InlineKeyboardButton("🔘 أزرار الرسائل", callback_data="edit_all_buttons")],
        [InlineKeyboardButton("⏱️ تعيين وقت النشر", callback_data="set_interval")],
        [InlineKeyboardButton("📋 عرض كل الرسائل", callback_data="show_all_msg")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="back_main")]
    ])

def auto_reply_keyboard(user_data):
    welcome = "✅" if user_data["welcome_enabled"] else "❌"
    reply = "✅" if user_data["reply_enabled"] else "❌"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"الترحيب {welcome}", callback_data="toggle_welcome")],
        [InlineKeyboardButton("✍️ تعيين رسالة الترحيب", callback_data="set_welcome")],
        [InlineKeyboardButton(f"الرد على المنشن {reply}", callback_data="toggle_reply")],
        [InlineKeyboardButton("✍️ تعيين رسالة الرد", callback_data="set_reply")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="back_main")]
    ])

def protection_keyboard(user_data):
    level = user_data["protection_level"]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"خفيف {'✅' if level == 1 else ''}", callback_data="prot_1")],
        [InlineKeyboardButton(f"متوسط {'✅' if level == 2 else ''}", callback_data="prot_2")],
        [InlineKeyboardButton(f"قوي {'✅' if level == 3 else ''}", callback_data="prot_3")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="back_main")]
    ])

@bot.on_message(filters.command("start"))
async def start(client, message: Message):
    init_db()
    db = load_db()
    if str(message.from_user.id) in db["banned_users"]:
        return await message.reply("❌ تم حظرك من استخدام البوت")
    get_user_data(message.from_user.id)
    db["stats"]["total_users"] = len(db["users"])
    save_db(db)
    sub_status = "✅ مفعل" if await check_subscription(message.from_user.id) else "❌ غير مفعل"
    await message.reply(
        f"**أهلا بيك في بوت النشر المتطور** 🔥\n\n**الاشتراك:** {sub_status}\n**الحسابات:** {len(db['accounts'].get(str(message.from_user.id), []))}/{MAX_ACCOUNTS}",
        reply_markup=main_keyboard(message.from_user.id)
    )

@bot.on_callback_query(filters.regex("features"))
async def features_menu(client, callback: CallbackQuery):
    text = f"""
**✨ مميزات بوت النشر المتطور**

**1. إدارة الحسابات**
- إضافة لحد {MAX_ACCOUNTS} حساب تيليجرام
- تشغيل/إيقاف كل حساب منفصل
- تبديل الحساب النشط للنشر بضغطة
- حالة الحساب: شغال/متوقف/فلود + عداد

**2. النشر الذكي**
- 4 رسايل مختلفة بترتيب تلقائي
- يحفظ التنسيق كامل: عريض، مائل، كود، اقتباس
- يحفظ ايموجي بريميوم تلقائي من غير ID
- 4 أزرار مخصصة لكل رسالة
- تظبيط وقت النشر بالدقايق: كل 1د/5د/10د...

**3. الرد التلقائي**
- رد على المنشن @username
- رد على الريبلاي
- تفعيل/تعطيل الترحيب والرد
- رسالة ترحيب + رسالة رد مخصصة

**4. الحماية من البان**
- 3 مستويات Anti-Flood: خفيف/متوسط/قوي
- معالجة FloodWait تلقائية
- لو الحساب بلع فلود يوقف ويرجع يشتغل لوحده
- تأخير عشوائي بين الرسايل

**⚡شغال علي افضا سيرفر بدون توقف**
"""
    await callback.message.edit(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Source", url="https://t.me/vip6705")],
        [InlineKeyboardButton("🖥️ Servers", url="https://t.me/Vpsazef")],
        [InlineKeyboardButton("👨‍💻 Programmer", url="https://t.me/Devazf")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="back_main")]
    ]))

@bot.on_callback_query(filters.regex("admin_panel"))
async def admin_panel(client, callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ غير مصرح", show_alert=True)
    await callback.message.edit("**⚙️ لوحة تحكم الأدمن**", reply_markup=admin_panel_keyboard())

@bot.on_callback_query(filters.regex("admin_stats"))
async def admin_stats(client, callback: CallbackQuery):
    db = load_db()
    active_subs = sum(1 for u in db["users"].values() if u.get("subscription_end", 0) > time.time())
    total_accounts = sum(len(accs) for accs in db["accounts"].values())
    active_userbots = sum(len(accs) for accs in userbots.values())
    text = f"**📊 الإحصائيات**\n\n👥 إجمالي المستخدمين: `{len(db['users'])}`\n✅ الاشتراكات النشطة: `{active_subs}`\n👤 إجمالي الحسابات: `{total_accounts}`\n🟢 الحسابات الشغالة: `{active_userbots}`\n🚫 المحظورين: `{len(db['banned_users'])}`\n⏳ طلبات دفع: `{len(db['pending_payments'])}`"
    await callback.message.edit(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ رجوع", callback_data="admin_panel")]]))

@bot.on_callback_query(filters.regex("admin_broadcast"))
async def admin_broadcast_start(client, callback: CallbackQuery):
    db = load_db()
    db["waiting_for"][str(callback.from_user.id)] = "broadcast"
    save_db(db)
    await callback.message.edit("**أرسل الرسالة للإذاعة:**\n\nلإلغاء: /cancel")

@bot.on_callback_query(filters.regex("admin_ban"))
async def admin_ban_start(client, callback: CallbackQuery):
    db = load_db()
    db["waiting_for"][str(callback.from_user.id)] = "ban_user"
    save_db(db)
    await callback.message.edit("**أرسل ID المستخدم للحظر:**\n\nلإلغاء: /cancel")

@bot.on_callback_query(filters.regex("admin_unban"))
async def admin_unban_start(client, callback: CallbackQuery):
    db = load_db()
    db["waiting_for"][str(callback.from_user.id)] = "unban_user"
    save_db(db)
    await callback.message.edit("**أرسل ID المستخدم لفك الحظر:**\n\nلإلغاء: /cancel")

@bot.on_callback_query(filters.regex("admin_add"))
async def admin_add_start(client, callback: CallbackQuery):
    db = load_db()
    db["waiting_for"][str(callback.from_user.id)] = "add_admin"
    save_db(db)
    await callback.message.edit("**أرسل ID المستخدم لإضافته كأدمن:**\n\nلإلغاء: /cancel")

@bot.on_callback_query(filters.regex("admin_payments"))
async def admin_payments(client, callback: CallbackQuery):
    db = load_db()
    pending = [uid for uid, val in db["pending_payments"].items() if val]
    if not pending:
        return await callback.message.edit("لا توجد طلبات دفع معلقة", reply_markup=admin_panel_keyboard())
    text = "**💳 طلبات الدفع المعلقة:**\n\n" + "\n".join([f"• `{uid}`" for uid in pending])
    await callback.message.edit(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ رجوع", callback_data="admin_panel")]]))

@bot.on_callback_query(filters.regex("manage_accounts"))
async def manage_accounts(client, callback: CallbackQuery):
    if not await check_subscription(callback.from_user.id):
        return await callback.answer("فعّل الاشتراك أولاً ❌", show_alert=True)
    await callback.message.edit("**👤 إدارة الحسابات**\n⭐ = الحساب النشط للنشر", reply_markup=accounts_keyboard(callback.from_user.id))

@bot.on_callback_query(filters.regex("add_account"))
async def add_account_start(client, callback: CallbackQuery):
    db = load_db()
    user_id = str(callback.from_user.id)
    if len(db["accounts"].get(user_id, [])) >= MAX_ACCOUNTS:
        return await callback.answer(f"وصلت للحد الأقصى {MAX_ACCOUNTS} حساب ❌", show_alert=True)
    db["waiting_for"][user_id] = "phone"
    save_db(db)
    await callback.message.edit("أرسل رقم الهاتف مع كود الدولة\nمثال: `+201234567890`\n\nلإلغاء: /cancel")

@bot.on_callback_query(filters.regex("switch_account"))
async def switch_account_menu(client, callback: CallbackQuery):
    db = load_db()
    accounts = db["accounts"].get(str(callback.from_user.id), [])
    if not accounts:
        return await callback.answer("مفيش حسابات ❌", show_alert=True)
    buttons = []
    for i, acc in enumerate(accounts):
        buttons.append([InlineKeyboardButton(acc['phone'], callback_data=f"set_active_{i}")])
    buttons.append([InlineKeyboardButton("⬅️ رجوع", callback_data="manage_accounts")])
    await callback.message.edit("**اختر الحساب النشط للنشر:**", reply_markup=InlineKeyboardMarkup(buttons))

@bot.on_callback_query(filters.regex(r"set_active_(\d+)"))
async def set_active_account(client, callback: CallbackQuery):
    index = int(callback.data.split("_")[2])
    db = load_db()
    db["users"][str(callback.from_user.id)]["active_account_index"] = index
    save_db(db)
    await callback.answer("✅ تم تغيير الحساب النشط")
    await manage_accounts(client, callback)

@bot.on_callback_query(filters.regex(r"acc_(\d+)"))
async def acc_menu(client, callback):
    index = int(callback.data.split("_")[1])
    db = load_db()
    acc = db["accounts"][str(callback.from_user.id)][index]
    flood_text = ""
    if str(callback.from_user.id) in userbots and index in userbots[str(callback.from_user.id)]:
        flood_until = userbots[str(callback.from_user.id)][index].get("flood_until", 0)
        if flood_until > time.time():
            remaining = int(flood_until - time.time())
            flood_text = f"\n⏳ **فلود:** متبقي {remaining} ثانية"
    await callback.message.edit(
        f"**التحكم في:** `{acc['phone']}`{flood_text}\n**المجموعات:** {len(acc['groups'])}",
        reply_markup=account_control_keyboard(index, callback.from_user.id)
    )

@bot.on_callback_query(filters.regex(r"status_(\d+)"))
async def account_status(client, callback):
    index = int(callback.data.split("_")[1])
    user_id = str(callback.from_user.id)
    db = load_db()
    acc = db["accounts"][user_id][index]
    status = "🔴 متوقف"
    flood_text = ""
    publishing = "❌ معطل"
    if user_id in userbots and index in userbots[user_id]:
        flood_until = userbots[user_id][index].get("flood_until", 0)
        if flood_until > time.time():
            remaining = int(flood_until - time.time())
            status = "🟡 فلود"
            flood_text = f"\n⏳ **ينتهي بعد:** {remaining} ثانية"
        else:
            status = "🟢 شغال"
        publishing = "✅ مفعل" if userbots[user_id][index].get("publishing") else "❌ معطل"
    text = f"**📊 حالة الحساب**\n\n📱 **الرقم:** `{acc['phone']}`\n🔌 **الحالة:** {status}{flood_text}\n📢 **النشر:** {publishing}\n👥 **المجموعات:** {len(acc['groups'])}"
    await callback.answer(text, show_alert=True)

@bot.on_callback_query(filters.regex(r"toggle_acc_(\d+)"))
async def toggle_account(client, callback):
    index = int(callback.data.split("_")[2])
    user_id = str(callback.from_user.id)
    if user_id in userbots and index in userbots[user_id]:
        if user_id in publish_tasks and index in publish_tasks[user_id]:
            publish_tasks[user_id][index].cancel()
            del publish_tasks[user_id][index]
        await userbots[user_id][index]["client"].stop()
        del userbots[user_id][index]
        db = load_db()
        db["accounts"][user_id][index]["active"] = False
        save_db(db)
        await callback.answer("⏸️ تم إيقاف الحساب")
    else:
        await start_userbot(user_id, index)
        await callback.answer("▶️ تم تشغيل الحساب")
    await acc_menu(client, callback)

@bot.on_callback_query(filters.regex(r"toggle_publish_(\d+)"))
async def toggle_publish(client, callback):
    index = int(callback.data.split("_")[2])
    user_id = str(callback.from_user.id)
    if user_id not in userbots or index not in userbots[user_id]:
        return await callback.answer("شغل الحساب أولاً ❌", show_alert=True)
    current = userbots[user_id][index].get("publishing", False)
    if current:
        userbots[user_id][index]["publishing"] = False
        if user_id in publish_tasks and index in publish_tasks[user_id]:
            publish_tasks[user_id][index].cancel()
            del publish_tasks[user_id][index]
        await callback.answer("⏸️ تم إيقاف النشر")
    else:
        userbots[user_id][index]["publishing"] = True
        task = asyncio.create_task(auto_publish_loop(user_id, index))
        if user_id not in publish_tasks:
            publish_tasks[user_id] = {}
        publish_tasks[user_id][index] = task
        await callback.answer("▶️ تم تفعيل النشر التلقائي")
    await acc_menu(client, callback)

async def auto_publish_loop(user_id, acc_index):
    while True:
        try:
            if not userbots[user_id][acc_index].get("publishing"):
                break
            flood_until = userbots[user_id][acc_index].get("flood_until", 0)
            if flood_until > time.time():
                await asyncio.sleep(5)
                continue
            db = load_db()
            user_data = get_user_data(user_id)
            acc = db["accounts"][user_id][acc_index]
            interval = user_data["publish_interval"] * 60
            if not acc["groups"]:
                await asyncio.sleep(10)
                continue
            ub = userbots[user_id][acc_index]["client"]
            for msg_index in range(4):
                if not userbots[user_id][acc_index].get("publishing"):
                    break
                entities_data = load_message_entities(user_id, msg_index)
                buttons_data = user_data["publish_buttons"][msg_index]
                markup = InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data="none")] for text in buttons_data if text])
                for group in acc["groups"]:
                    try:
                        if entities_data and entities_data["text"]:
                            await ub.send_message(group["id"], entities_data["text"], entities=entities_data["entities"], reply_markup=markup)
                        elif user_data["publish_messages"][msg_index]:
                            await ub.send_message(group["id"], user_data["publish_messages"][msg_index], parse_mode=ParseMode.HTML, reply_markup=markup)
                        await asyncio.sleep(random.uniform(2, 5))
                    except FloodWait as e:
                        userbots[user_id][acc_index]["flood_until"] = time.time() + e.value
                        await asyncio.sleep(e.value)
                        break
                    except:
                        pass
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Publish loop error: {e}")
            await asyncio.sleep(10)

async def start_userbot(user_id, acc_index):
    db = load_db()
    user_id = str(user_id)
    acc = db["accounts"][user_id][acc_index]
    user_data = get_user_data(user_id)
    session = acc["session"]
    ub = Client(
        session,
        api_id=API_ID,
        api_hash=API_HASH,
        device_model="iPhone 17 pro",
        system_version="iOS 19.0",
        app_version="10.5.0"
    )

    @ub.on_message(filters.mentioned | filters.reply)
    async def auto_reply_handler(client, message: Message):
        if not await check_subscription(int(user_id)):
            return
        if not user_data["reply_enabled"]:
            return
        if message.reply_to_message and message.reply_to_message.from_user.id!= client.me.id:
            return
        if not userbots[user_id][acc_index].get("publishing", False):
            return
        flood_until = userbots[user_id][acc_index].get("flood_until", 0)
        if flood_until > time.time():
            return
        level = user_data["protection_level"]
        delay = {1: 1, 2: 3, 3: 6}[level]
        await asyncio.sleep(random.uniform(delay, delay + 2))
        reply_entities = load_message_entities(user_id, "reply")
        buttons_data = user_data["publish_buttons"][0]
        markup = InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data="none")] for text in buttons_data if text])
        try:
            if reply_entities and reply_entities["text"]:
                await message.reply(reply_entities["text"], entities=reply_entities["entities"], reply_markup=markup)
            elif user_data["reply_message"]:
                await message.reply(user_data["reply_message"], parse_mode=ParseMode.HTML, reply_markup=markup)
            else:
                entities_data = load_message_entities(user_id, 0)
                if entities_data and entities_data["text"]:
                    await message.reply(entities_data["text"], entities=entities_data["entities"], reply_markup=markup)
                elif user_data["publish_messages"][0]:
                    await message.reply(user_data["publish_messages"][0], parse_mode=ParseMode.HTML, reply_markup=markup)
        except FloodWait as e:
            userbots[user_id][acc_index]["flood_until"] = time.time() + e.value
        except:
            pass

    await ub.start()
    if user_id not in userbots:
        userbots[user_id] = {}
    userbots[user_id][acc_index] = {"client": ub, "flood_until": 0, "publishing": False}
    db["accounts"][user_id][acc_index]["active"] = True
    save_db(db)

@bot.on_callback_query(filters.regex(r"getgroups_(\d+)"))
async def get_groups(client, callback):
    index = int(callback.data.split("_")[1])
    user_id = str(callback.from_user.id)
    if user_id not in userbots or index not in userbots[user_id]:
        return await callback.answer("شغل الحساب أولاً ❌", show_alert=True)
    ub = userbots[user_id][index]["client"]
    groups = []
    async for dialog in ub.get_dialogs():
        if dialog.chat.type in ["group", "supergroup"]:
            groups.append({"id": dialog.chat.id, "title": dialog.chat.title})
    db = load_db()
    db["accounts"][user_id][index]["groups"] = groups
    save_db(db)
    text = "**المجموعات:**\n" + "\n".join([f"• {g['title']}" for g in groups]) if groups else "لا توجد مجموعات"
    await callback.message.edit(text, reply_markup=account_control_keyboard(index, callback.from_user.id))

@bot.on_callback_query(filters.regex(r"publishnow_(\d+)"))
async def publish_now(client, callback):
    index = int(callback.data.split("_")[1])
    user_id = str(callback.from_user.id)
    db = load_db()
    acc = db["accounts"][user_id][index]
    user_data = get_user_data(user_id)
    if user_id not in userbots or index not in userbots[user_id]:
        return await callback.answer("شغل الحساب أولاً ❌", show_alert=True)
    if not acc["groups"]:
        return await callback.answer("مفيش مجموعات ❌", show_alert=True)
    ub = userbots[user_id][index]["client"]
    flood_until = userbots[user_id][index].get("flood_until", 0)
    if flood_until > time.time():
        remaining = int(flood_until - time.time())
        return await callback.answer(f"الحساب في فلود. متبقي {remaining}ث ❌", show_alert=True)
    sent = 0
    entities_data = load_message_entities(user_id, 0)
    buttons_data = user_data["publish_buttons"][0]
    markup = InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data="none")] for text in buttons_data if text])
    for group in acc["groups"]:
        try:
            if entities_data and entities_data["text"]:
                await ub.send_message(group["id"], entities_data["text"], entities=entities_data["entities"], reply_markup=markup)
            elif user_data["publish_messages"][0]:
                await ub.send_message(group["id"], user_data["publish_messages"][0], parse_mode=ParseMode.HTML, reply_markup=markup)
            sent += 1
            await asyncio.sleep(random.uniform(2, 5))
        except FloodWait as e:
            userbots[user_id][index]["flood_until"] = time.time() + e.value
            await callback.answer(f"⏳ فلود {e.value}ث", show_alert=True)
            break
        except Exception as e:
            print(f"Publish error: {e}")
    if sent > 0:
        await callback.answer(f"✅ تم النشر في {sent} مجموعة", show_alert=True)

@bot.on_callback_query(filters.regex(r"delacc_(\d+)"))
async def delete_account(client, callback):
    index = int(callback.data.split("_")[1])
    user_id = str(callback.from_user.id)
    db = load_db()
    acc = db["accounts"][user_id].pop(index)
    save_db(db)
    if user_id in userbots and index in userbots[user_id]:
        if user_id in publish_tasks and index in publish_tasks[user_id]:
            publish_tasks[user_id][index].cancel()
            del publish_tasks[user_id][index]
        await userbots[user_id][index]["client"].stop()
        del userbots[user_id][index]
    try:
        os.remove(f"{acc['session']}.session")
    except:
        pass
    await callback.answer("تم حذف الحساب ✅")
    await callback.message.edit("**👤 إدارة الحسابات**", reply_markup=accounts_keyboard(callback.from_user.id))

@bot.on_callback_query(filters.regex("publish_settings"))
async def publish_settings(client, callback):
    await callback.message.edit("**📢 إعدادات النشر**\n\n4 رسايل + 4 أزرار لكل رسالة + توقيت", reply_markup=publish_settings_keyboard())

@bot.on_callback_query(filters.regex(r"edit_msg_(\d)"))
async def edit_msg_start(client, callback):
    msg_index = int(callback.data.split("_")[2])
    db = load_db()
    db["waiting_for"][str(callback.from_user.id)] = f"edit_msg_{msg_index}"
    save_db(db)
    await callback.message.edit(f"**أرسل الرسالة رقم {msg_index + 1}:**\n\nابعت أي رسالة فيها ايموجي بريميوم أو تنسيق وهيتحفظ تلقائي\n\nلإلغاء: /cancel")

@bot.on_callback_query(filters.regex("edit_all_buttons"))
async def edit_all_buttons_start(client, callback):
    db = load_db()
    db["waiting_for"][str(callback.from_user.id)] = "edit_all_buttons"
    save_db(db)
    await callback.message.edit("**أرسل أزرار الـ4 رسايل:**\n\nكل سطرين = رسالة واحدة\nمثال:\nزر1-1\nزر1-2\nزر2-1\nزر2-2\nزر3-1\nزر3-2\nزر4-1\nزر4-2\n\nلإلغاء: /cancel")

@bot.on_callback_query(filters.regex("set_interval"))
async def set_interval_start(client, callback):
    db = load_db()
    db["waiting_for"][str(callback.from_user.id)] = "set_interval"
    save_db(db)
    await callback.message.edit("**أرسل وقت النشر بالدقايق:**\n\nمثال: `5` يعني كل 5 دقايق ينشر رسالة\n\nلإلغاء: /cancel")

@bot.on_callback_query(filters.regex("show_all_msg"))
async def show_all_msg(client, callback):
    user_data = get_user_data(callback.from_user.id)
    await callback.message.delete()
    for i in range(4):
        entities_data = load_message_entities(callback.from_user.id, i)
        buttons_data = user_data["publish_buttons"][i]
        markup = InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data="none")] for text in buttons_data if text])
        text = f"**📝 الرسالة {i+1}**\n⏱️ كل {user_data['publish_interval']} دقيقة"
        if entities_data and entities_data["text"]:
            await bot.send_message(callback.from_user.id, f"{text}\n\n{entities_data['text']}", entities=entities_data["entities"], reply_markup=markup)
        elif user_data["publish_messages"][i]:
            await bot.send_message(callback.from_user.id, f"{text}\n\n{user_data['publish_messages'][i]}", parse_mode=ParseMode.HTML, reply_markup=markup)
        else:
            await bot.send_message(callback.from_user.id, f"{text}\n\n_فارغة_", reply_markup=markup)
        await asyncio.sleep(0.5)
    await bot.send_message(callback.from_user.id, "**القائمة الرئيسية**", reply_markup=main_keyboard(callback.from_user.id))

@bot.on_callback_query(filters.regex("auto_reply"))
async def auto_reply_menu(client, callback):
    user_data = get_user_data(callback.from_user.id)
    await callback.message.edit("**🤖 إعدادات الرد التلقائي**", reply_markup=auto_reply_keyboard(user_data))

@bot.on_callback_query(filters.regex("toggle_welcome"))
async def toggle_welcome(client, callback):
    db = load_db()
    db["users"][str(callback.from_user.id)]["welcome_enabled"] = not db["users"][str(callback.from_user.id)]["welcome_enabled"]
    save_db(db)
    await auto_reply_menu(client, callback)

@bot.on_callback_query(filters.regex("toggle_reply"))
async def toggle_reply(client, callback):
    db = load_db()
    db["users"][str(callback.from_user.id)]["reply_enabled"] = not db["users"][str(callback.from_user.id)]["reply_enabled"]
    save_db(db)
    await auto_reply_menu(client, callback)

@bot.on_callback_query(filters.regex("set_welcome"))
async def set_welcome_start(client, callback):
    db = load_db()
    db["waiting_for"][str(callback.from_user.id)] = "set_welcome"
    save_db(db)
    await callback.message.edit("**أرسل رسالة الترحيب الجديدة:**\n\nتقدر تستخدم تنسيق + ايموجي بريميوم وهيتحفظ تلقائي\n\nلإلغاء: /cancel")

@bot.on_callback_query(filters.regex("set_reply"))
async def set_reply_start(client, callback):
    db = load_db()
    db["waiting_for"][str(callback.from_user.id)] = "set_reply"
    save_db(db)
    await callback.message.edit("**أرسل رسالة الرد التلقائي:**\n\nاللي هتتبعت لما حد يعمل منشن أو ريبلاي\nتقدر تستخدم تنسيق + ايموجي بريميوم\n\nلإلغاء: /cancel")

@bot.on_callback_query(filters.regex("protection"))
async def protection_menu(client, callback):
    user_data = get_user_data(callback.from_user.id)
    await callback.message.edit("**🛡️ الحماية من التجميد والفلود**\n\nخفيف: 1 ثانية\nمتوسط: 3 ثواني\nقوي: 6 ثواني", reply_markup=protection_keyboard(user_data))

@bot.on_callback_query(filters.regex(r"prot_(\d)"))
async def set_protection(client, callback):
    level = int(callback.data.split("_")[1])
    db = load_db()
    db["users"][str(callback.from_user.id)]["protection_level"] = level
    save_db(db)
    await callback.answer("تم تحديث مستوى الحماية ✅")
    await protection_menu(client, callback)

@bot.on_callback_query(filters.regex("subscription"))
async def subscription_menu(client, callback):
    text = f"**💳 الاشتراك الشهري: {SUBSCRIPTION_PRICE}$**\n\n**طرق الدفع:**\n"
    for name, addr in PAYMENT_METHODS.items():
        text += f"**{name}**: `{addr}`\n"
    text += "\n**بعد الدفع:**\n1️⃣ اضغط 'تم الدفع'\n2️⃣ ابعت سكرين شوت للتحويل\n3️⃣ ابعت هاش المعاملة + اسم الشبكة\n\nمثال:\n`0x123abc... BEP20`"
    buttons = [[InlineKeyboardButton("✅ تم الدفع", callback_data="paid")], [InlineKeyboardButton("⬅️ رجوع", callback_data="back_main")]]
    await callback.message.edit(text, reply_markup=InlineKeyboardMarkup(buttons))

@bot.on_callback_query(filters.regex("paid"))
async def paid_handler(client, callback):
    await callback.message.edit("**ارفع سكرين شوت التحويل + ابعت هاش المعاملة**\n\nمثال:\n`0x123abc... BEP20`\n\nلو بعت الصورة بس من غير الهاش هيترفض\n\nلإلغاء: /cancel")
    db = load_db()
    db["pending_payments"][str(callback.from_user.id)] = {"step": "waiting_screenshot"}
    save_db(db)

@bot.on_callback_query(filters.regex(r"accept_(\d+)"))
async def accept_sub(client, callback):
    user_id = callback.data.split("_")[1]
    db = load_db()
    db["users"][user_id]["subscription_end"] = time.time() + 30*24*60*60
    db["pending_payments"].pop(user_id, None)
    save_db(db)
    await bot.send_message(int(user_id), "🎉 **تم تفعيل اشتراكك لمدة شهر**\n\nتقدر تستخدم كل مميزات البوت دلوقتي")
    await callback.message.edit(f"✅ تم تفعيل الاشتراك للمستخدم `{user_id}`")

@bot.on_callback_query(filters.regex(r"reject_(\d+)"))
async def reject_sub(client, callback):
    user_id = callback.data.split("_")[1]
    db = load_db()
    db["pending_payments"].pop(user_id, None)
    save_db(db)
    await bot.send_message(int(user_id), "❌ **تم رفض طلب الاشتراك**\n\nتأكد من صحة البيانات أو تواصل مع المطور")
    await callback.message.edit(f"❌ تم رفض طلب الاشتراك للمستخدم `{user_id}`")

@bot.on_message(filters.private)
async def handle_input(client, message: Message):
    db = load_db()
    user_id = str(message.from_user.id)
    wait_for = db["waiting_for"].get(user_id)

    if message.text == "/cancel":
        db["waiting_for"].pop(user_id, None)
        save_db(db)
        return await message.reply("تم الإلغاء ✅", reply_markup=main_keyboard(message.from_user.id))

    if wait_for == "phone":
        phone = message.text.strip()
        session_name = f"{SESSIONS_DIR}/{user_id}_{phone}"
        temp_client = Client(session_name, api_id=API_ID, api_hash=API_HASH, device_model="iPhone 17 pro", system_version="iOS 19.0", app_version="10.5.0")
        temp_clients[user_id] = temp_client
        await temp_client.connect()
        try:
            sent_code = await temp_client.send_code(phone)
            db["waiting_for"][user_id] = f"code_{phone}_{sent_code.phone_code_hash}"
            save_db(db)
            await message.reply("تم إرسال الكود. أرسل الكود الآن:")
        except Exception as e:
            await message.reply(f"خطأ: {e}")
            await temp_client.disconnect()
            del temp_clients[user_id]
            db["waiting_for"].pop(user_id, None)
            save_db(db)

    elif wait_for and wait_for.startswith("code_"):
        _, phone, phone_hash = wait_for.split("_", 2)
        temp_client = temp_clients.get(user_id)
        if not temp_client:
            return await message.reply("انتهت الجلسة. ابدأ من جديد")
        try:
            await temp_client.sign_in(phone, phone_hash, message.text.strip())
        except SessionPasswordNeeded:
            db["waiting_for"][user_id] = f"2fa_{phone}"
            save_db(db)
            return await message.reply("الحساب عليه تحقق بخطوتين. أرسل كلمة السر:")
        except PhoneCodeInvalid:
            return await message.reply("الكود غلط ❌")
        if str(user_id) not in db["accounts"]:
            db["accounts"][str(user_id)] = []
        db["accounts"][str(user_id)].append({"phone": phone, "session": f"{SESSIONS_DIR}/{user_id}_{phone}", "active": False, "groups": []})
        db["waiting_for"].pop(user_id, None)
        save_db(db)
        await temp_client.disconnect()
        del temp_clients[user_id]
        await message.reply("✅ تم إضافة الحساب بنجاح", reply_markup=accounts_keyboard(message.from_user.id))

    elif wait_for and wait_for.startswith("2fa_"):
        phone = wait_for.split("_")[1]
        temp_client = temp_clients.get(user_id)
        try:
            await temp_client.check_password(message.text.strip())
            if str(user_id) not in db["accounts"]:
                db["accounts"][str(user_id)] = []
            db["accounts"][str(user_id)].append({"phone": phone, "session": f"{SESSIONS_DIR}/{user_id}_{phone}", "active": False, "groups": []})
            db["waiting_for"].pop(user_id, None)
            save_db(db)
            await temp_client.disconnect()
            del temp_clients[user_id]
            await message.reply("✅ تم إضافة الحساب بنجاح", reply_markup=accounts_keyboard(message.from_user.id))
        except Exception as e:
            await message.reply(f"كلمة السر غلط: {e}")

    elif wait_for and wait_for.startswith("edit_msg_"):
        msg_index = int(wait_for.split("_")[2])
        save_message_entities(user_id, msg_index, message)
        db["users"][user_id]["publish_messages"][msg_index] = message.text or message.caption or ""
        db["waiting_for"].pop(user_id, None)
        save_db(db)
        await message.reply(f"✅ تم حفظ الرسالة {msg_index + 1} مع التنسيق والايموجي البريميوم تلقائي", reply_markup=publish_settings_keyboard())

    elif wait_for == "edit_all_buttons":
        lines = message.text.split("\n")
        buttons = [[], [], [], []]
        for i in range(min(8, len(lines))):
            buttons[i // 2].append(lines[i])
        for i in range(4):
            while len(buttons[i]) < 2:
                buttons[i].append("")
        db["users"][user_id]["publish_buttons"] = buttons
        db["waiting_for"].pop(user_id, None)
        save_db(db)
        await message.reply("✅ تم حفظ الأزرار", reply_markup=publish_settings_keyboard())

    elif wait_for == "set_interval":
        try:
            interval = int(message.text.strip())
            if interval < 1:
                return await message.reply("الوقت لازم يكون دقيقة أو أكثر ❌")
            db["users"][user_id]["publish_interval"] = interval
            db["waiting_for"].pop(user_id, None)
            save_db(db)
            await message.reply(f"✅ تم تعيين وقت النشر: كل {interval} دقيقة", reply_markup=publish_settings_keyboard())
        except:
            await message.reply("أرسل رقم صحيح ❌")

    elif wait_for == "set_welcome":
        save_message_entities(user_id, "welcome", message)
        db["users"][user_id]["welcome_message"] = message.text or message.caption or ""
        db["waiting_for"].pop(user_id, None)
        save_db(db)
        await message.reply("✅ تم حفظ رسالة الترحيب", reply_markup=auto_reply_keyboard(get_user_data(user_id)))

    elif wait_for == "set_reply":
        save_message_entities(user_id, "reply", message)
        db["users"][user_id]["reply_message"] = message.text or message.caption or ""
        db["waiting_for"].pop(user_id, None)
        save_db(db)
        await message.reply("✅ تم حفظ رسالة الرد التلقائي", reply_markup=auto_reply_keyboard(get_user_data(user_id)))

    elif wait_for == "broadcast":
        count = 0
        for uid in db["users"].keys():
            try:
                await bot.send_message(int(uid), message.text, entities=message.entities)
                count += 1
                await asyncio.sleep(0.1)
            except:
                pass
        db["waiting_for"].pop(user_id, None)
        save_db(db)
        await message.reply(f"✅ تم إرسال الإذاعة لـ {count} مستخدم")

    elif wait_for == "ban_user":
        target_id = message.text.strip()
        if target_id not in db["banned_users"]:
            db["banned_users"].append(target_id)
            db["waiting_for"].pop(user_id, None)
            save_db(db)
            await message.reply(f"✅ تم حظر {target_id}")
        else:
            await message.reply("المستخدم محظور بالفعل")

    elif wait_for == "unban_user":
        target_id = message.text.strip()
        if target_id in db["banned_users"]:
            db["banned_users"].remove(target_id)
            db["waiting_for"].pop(user_id, None)
            save_db(db)
            await message.reply(f"✅ تم فك حظر {target_id}")
        else:
            await message.reply("المستخدم غير محظور")

    elif wait_for == "add_admin":
        target_id = message.text.strip()
        if target_id not in db["admins"]:
            db["admins"].append(target_id)
            db["waiting_for"].pop(user_id, None)
            save_db(db)
            await message.reply(f"✅ تم إضافة {target_id} كأدمن")
        else:
            await message.reply("المستخدم أدمن بالفعل")

    # استقبال طلب الدفع - سكرين شوت + هاش
    elif db["pending_payments"].get(user_id, {}).get("step") == "waiting_screenshot":
        if message.photo:
            db["pending_payments"][user_id] = {"step": "waiting_hash", "photo_id": message.photo.file_id}
            save_db(db)
            await message.reply("✅ تم استلام السكرين\n\nدلوقتي ابعت هاش المعاملة + اسم الشبكة\nمثال:\n`0x123abc... BEP20`")
        else:
            await message.reply("❌ لازم تبعت صورة السكرين شوت الأول")

    elif db["pending_payments"].get(user_id, {}).get("step") == "waiting_hash":
        if message.text:
            photo_id = db["pending_payments"][user_id]["photo_id"]
            hash_text = message.text
            buttons = [[
                InlineKeyboardButton("✅ قبول", callback_data=f"accept_{user_id}"),
                InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}")
            ]]
            caption = f"""
**💳 طلب اشتراك جديد**

👤 **المستخدم:** {message.from_user.mention}
🆔 **ID:** `{user_id}`
💰 **المبلغ:** {SUBSCRIPTION_PRICE}$
🔗 **الهاش:** `{hash_text}`

**راجع السكرين والهاش قبل القبول**
"""
            await bot.send_photo(
                DEVELOPER_ID,
                photo_id,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            await message.reply("✅ تم ارسال طلبك للمطور\n\nهيتم المراجعة والتفعيل في أقرب وقت")
            db["pending_payments"][user_id] = {"step": "pending_review", "hash": hash_text}
            save_db(db)
        else:
            await message.reply("❌ ابعت الهاش كـ نص")

@bot.on_callback_query(filters.regex("back_main"))
async def back_main(client, callback):
    await callback.message.edit("**القائمة الرئيسية**", reply_markup=main_keyboard(callback.from_user.id))

if __name__ == "__main__":
    init_db()
    print("Bot started...")
    bot.run()
