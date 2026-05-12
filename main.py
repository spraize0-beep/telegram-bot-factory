import os
import asyncio
import sqlite3
import time
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, SessionPasswordNeededError, PhoneCodeInvalidError
from telethon.tl.functions.messages import GetDialogFiltersRequest

API_ID = 33595004 # رقم، من غير كوتس
API_HASH = "cbd1066ed026997f2f4a7c4323b7bda7"
BOT_TOKEN = "8999384350:AAGbf5UaMpTdMVbKNOBqlr2mK2xMWRpi3eU"
OWNER_ID = 8085768728 # ID بتاعك
FORCE_CHANNEL = "marketing_azef" # اسم القناة من غير @
BOT_PASSWORD = "Azefx2006" # كلمة سر دخول البوت
SESSION_PASSWORD = "Azefr2006#"

bot = TelegramClient('bot', API_ID, API_HASH)

DB = sqlite3.connect("bot.db", check_same_thread=False)
c = DB.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS accounts
    (id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT, session TEXT, status TEXT DEFAULT 'active')''')
c.execute('''CREATE TABLE IF NOT EXISTS groups
    (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, chat_name TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS settings
    (key TEXT PRIMARY KEY, value TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS saved_posts
    (id INTEGER PRIMARY KEY AUTOINCREMENT,
     msg1 TEXT, msg1_entities BLOB, msg1_enabled INTEGER DEFAULT 1,
     msg2 TEXT, msg2_entities BLOB, msg2_enabled INTEGER DEFAULT 1,
     msg3 TEXT, msg3_entities BLOB, msg3_enabled INTEGER DEFAULT 1,
     msg4 TEXT, msg4_entities BLOB, msg4_enabled INTEGER DEFAULT 1)''')
c.execute('''CREATE TABLE IF NOT EXISTS reply_cooldown
    (user_id INTEGER, chat_id INTEGER, last_reply INTEGER, PRIMARY KEY(user_id, chat_id))''')
DB.commit()

FLOOD_LEVELS = {"خفيف": 5, "متوسط": 15, "شديد": 30}
user_states = {}
user_clients = {}
posting_active = False
current_post_data = {}
user_authed = set()

def is_owner(user_id):
    return user_id == OWNER_ID and user_id in user_authed

def get_setting(key, default="off"):
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    return row[0] if row else default

def set_setting(key, value):
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
    DB.commit()

async def check_force_sub(user_id):
    if user_id == OWNER_ID:
        return True
    try:
        await bot.get_participant(f"@{FORCE_CHANNEL}", user_id)
        return True
    except:
        return False

async def send_force_sub(event):
    buttons = [[Button.url("📢 اشترك", f"https://t.me/{FORCE_CHANNEL}")],
               [Button.inline("✅ تحققت", "check_sub")]]
    await event.reply("⚠️ لازم تشترك في القناة", buttons=buttons)

main_menu = [
    [Button.inline("📁 المجلدات", "get_folders"), Button.inline("📥 المجموعات", "get_groups")],
    [Button.inline("⚙️ الحسابات", "accounts"), Button.inline("🚀 النشر", "start_post")],
    [Button.inline("🛡️ الحماية", "protect"), Button.inline("🤖 الرد التلقائي", "auto_reply")],
    [Button.inline("👋 الترحيب", "welcome"), Button.inline("📝 الرسائل المحفوظة", "saved_posts")],
    [Button.inline("⏹️ إيقاف النشر", "stop_post"), Button.inline("🚪 تسجيل الخروج", "logout")]
]

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id!= OWNER_ID:
        return
    if event.sender_id not in user_authed:
        await event.reply("🔐 ابعت /login وسجل دخولك الأول")
        return
    if not await check_force_sub(event.sender_id):
        await send_force_sub(event)
        return
    await event.reply("🚀 بوت النشر Pro v4.1 - مؤمّن", buttons=main_menu)

@bot.on(events.NewMessage(pattern='/login'))
async def login(event):
    if event.sender_id!= OWNER_ID:
        return
    user_states[event.sender_id] = "await_password"
    await event.reply("🔐 ابعت كلمة سر البوت:")

@bot.on(events.NewMessage)
async def check_password(event):
    if user_states.get(event.sender_id) == "await_password":
        if event.message.text == BOT_PASSWORD:
            user_authed.add(event.sender_id)
            user_states.pop(event.sender_id)
            await event.reply("✅ تم تسجيل الدخول", buttons=main_menu)
        else:
            await event.reply("❌ كلمة السر غلط")
        return

@bot.on(events.CallbackQuery(data=b'logout'))
async def logout(event):
    user_authed.discard(event.sender_id)
    await event.edit("🚪 تم تسجيل الخروج")

@bot.on(events.CallbackQuery)
async def callback(event):
    if not is_owner(event.sender_id):
        return await event.answer("🔐 سجل دخولك الأول", alert=True)

    data = event.data.decode()

    if data == "back_main":
        await event.edit("لوحة التحكم:", buttons=main_menu)

    elif data == "accounts":
        await accounts_menu(event)

    elif data == "add_account":
        user_states[event.sender_id] = {"step": "await_phone"}
        await event.edit("📱 ابعت رقم الهاتف مع كود الدولة\nمثال: +201234567890")

    elif data == "start_post":
        user_states[event.sender_id] = {"step": "msg1", "msgs": {}}
        await event.edit("📝 ابعت الرسالة 1\nحدد النص واضغط B للعريض، I للمائل، > للاقتباس، ` للكود")

    elif data == "saved_posts":
        c.execute("SELECT id, msg1, msg2, msg3, msg4 FROM saved_posts ORDER BY id DESC LIMIT 10")
        posts = c.fetchall()
        buttons = []
        for p in posts:
            preview = p[1][:20] if p[1] else "فارغ"
            buttons.append([Button.inline(f"📄 {preview}", f"edit_post_{p[0]}")])
        buttons.append([Button.inline("🔙 رجوع", "back_main")])
        await event.edit("📝 الرسائل المحفوظة:", buttons=buttons)

    elif data.startswith("edit_post_"):
        post_id = int(data.split("_")[2])
        c.execute("SELECT * FROM saved_posts WHERE id=?", (post_id,))
        post = c.fetchone()
        buttons = [
            [Button.inline(f"رسالة 1 {'✅' if post[4]==1 else '❌'}", f"toggle_1_{post_id}")],
            [Button.inline(f"رسالة 2 {'✅' if post[7]==1 else '❌'}", f"toggle_2_{post_id}")],
            [Button.inline(f"رسالة 3 {'✅' if post[10]==1 else '❌'}", f"toggle_3_{post_id}")],
            [Button.inline(f"رسالة 4 {'✅' if post[13]==1 else '❌'}", f"toggle_4_{post_id}")],
            [Button.inline("🚀 ابدأ النشر", f"use_post_{post_id}")],
            [Button.inline("🔙 رجوع", "back_main")]
        ]
        await event.edit("🎛️ تحكم في الرسائل:\n✅ مفعلة | ❌ معطلة", buttons=buttons)

    elif data.startswith("toggle_"):
        parts = data.split("_")
        msg_num = int(parts[1])
        post_id = int(parts[2])
        col = f"msg{msg_num}_enabled"
        c.execute(f"UPDATE saved_posts SET {col} = CASE WHEN {col}=1 THEN 0 ELSE 1 END WHERE id=?", (post_id,))
        DB.commit()
        await callback(event)

    elif data.startswith("use_post_"):
        post_id = int(data.split("_")[2])
        c.execute("SELECT * FROM saved_posts WHERE id=?", (post_id,))
        post = c.fetchone()
        messages = []
        for i in range(4):
            if post[3 + i*3 + 2] == 1:
                messages.append({
                    "text": post[3 + i*3],
                    "entities": eval(post[3 + i*3 + 1])
                })
        if not messages:
            return await event.answer("❌ كل الرسايل معطلة", alert=True)
        current_post_data[event.sender_id] = messages
        await event.edit("✅ تم تحميل الرسايل المفعلة\nالآن اختر المجلد من زر المجلدات")

    elif data == "get_folders":
        await get_folders(event)
    elif data == "protect":
        await protect_menu(event)
    elif data == "auto_reply":
        await auto_reply_menu(event)
    elif data == "welcome":
        await welcome_menu(event)
    elif data.startswith("set_flood_"):
        level = data.split("_")[2]
        set_setting("flood_level", level)
        await event.answer(f"✅ تم تعيين {level}")
        await protect_menu(event)
    elif data == "toggle_auto_reply":
        current = get_setting("auto_reply", "off")
        set_setting("auto_reply", "off" if current=="on" else "on")
        await auto_reply_menu(event)
    elif data == "toggle_welcome":
        current = get_setting("welcome", "off")
        set_setting("welcome", "off" if current=="on" else "on")
        await welcome_menu(event)
    elif data == "stop_post":
        global posting_active
        posting_active = False
        await event.answer("⏹️ تم إيقاف النشر")

async def accounts_menu(event):
    c.execute("SELECT id, phone, status FROM accounts")
    accs = c.fetchall()
    text = f"⚙️ الحسابات: {len(accs)}/50\n"
    buttons = []
    for acc in accs:
        status = "🟢" if acc[2] == "active" else "🔴"
        text += f"{status} {acc[1]}\n"
        buttons.append([Button.inline(f"🗑️ حذف {acc[1]}", f"del_acc_{acc[0]}")])
    if len(accs) < 50:
        buttons.append([Button.inline("➕ إضافة حساب", "add_account")])
    buttons.append([Button.inline("🔙 رجوع", "back_main")])
    await event.edit(text, buttons=buttons)

async def protect_menu(event):
    current = get_setting("flood_level", "متوسط")
    buttons = [
        [Button.inline(f"🟢 خفيف {'✓' if current=='خفيف' else ''}", "set_flood_خفيف")],
        [Button.inline(f"🟡 متوسط {'✓' if current=='متوسط' else ''}", "set_flood_متوسط")],
        [Button.inline(f"🔴 شديد {'✓' if current=='شديد' else ''}", "set_flood_شديد")],
        [Button.inline("🔙 رجوع", "back_main")]
    ]
    await event.edit(f"🛡️ مستوى الحماية: {current}\n\n🔒 البوت مؤمّن بكلمة سر وتشفير جلسات", buttons=buttons)

async def auto_reply_menu(event):
    status = get_setting("auto_reply", "off")
    buttons = [[Button.inline(f"{'❌ تعطيل' if status=='on' else '✅ تفعيل'}", "toggle_auto_reply")],
               [Button.inline("🔙 رجوع", "back_main")]]
    await event.edit(f"🤖 الرد التلقائي: {'مفعل' if status=='on' else 'معطل'}", buttons=buttons)

async def welcome_menu(event):
    status = get_setting("welcome", "off")
    buttons = [[Button.inline(f"{'❌ تعطيل' if status=='on' else '✅ تفعيل'}", "toggle_welcome")],
               [Button.inline("🔙 رجوع", "back_main")]]
    await event.edit(f"👋 الترحيب: {'مفعل' if status=='on' else 'معطل'}", buttons=buttons)

async def get_folders(event):
    client = await get_first_client()
    if not client:
        return await event.edit("❌ مفيش حسابات متاحة")
    try:
        folders = await client(GetDialogFiltersRequest())
        buttons = []
        for folder in folders:
            if hasattr(folder, 'title'):
                buttons.append([Button.inline(f"📁 {folder.title}", f"post_folder_{folder.id}")])
        buttons.append([Button.inline("🔙 رجوع", "back_main")])
        await event.edit("📁 اختر المجلد:", buttons=buttons)
    except Exception as e:
        await event.edit(f"❌ خطأ: {e}")

@bot.on(events.CallbackQuery(pattern=b'post_folder_'))
async def post_folder(event):
    if not is_owner(event.sender_id):
        return
    folder_id = int(event.data.decode().split("_")[2])
    if event.sender_id not in current_post_data:
        return await event.answer("❌ مفيش رسايل محفوظة", alert=True)
    client = await get_first_client()
    if not client:
        return await event.edit("❌ مفيش حسابات متاحة")
    dialogs = await client.get_dialogs()
    chats = [d.id for d in dialogs if d.folder_id == folder_id]
    if not chats:
        return await event.edit("❌ المجلد فاضي")
    messages = current_post_data[event.sender_id]
    await event.edit(f"🚀 بدأ النشر في {len(chats)} مجموعة")
    asyncio.create_task(post_messages(client, chats, messages))

@bot.on(events.NewMessage)
async def handle_message(event):
    if event.sender_id!= OWNER_ID:
        return

    state = user_states.get(event.sender_id)
    if isinstance(state, dict) and state.get("step", "").startswith("msg"):
        text = event.message.text
        entities = event.message.entities if event.message.entities else []
        msg_num = int(state["step"][3])
        state.setdefault("msgs", {})[f"msg{msg_num}"] = {"text": text, "entities": str(entities)}

        if msg_num < 4:
            state["step"] = f"msg{msg_num + 1}"
            await event.reply(f"✅ اتحفظت الرسالة {msg_num}\nابعت الرسالة {msg_num + 1}")
        else:
            msgs = state["msgs"]
            c.execute("""INSERT INTO saved_posts
                (msg1, msg1_entities, msg2, msg2_entities, msg3, msg3_entities, msg4, msg4_entities)
                VALUES (?,?,?,?,?,?,?,?)""",
                (msgs["msg1"]["text"], msgs["msg1"]["entities"],
                 msgs["msg2"]["text"], msgs["msg2"]["entities"],
                 msgs["msg3"]["text"], msgs["msg3"]["entities"],
                 msgs["msg4"]["text"], msgs["msg4"]["entities"]))
            DB.commit()
            user_states.pop(event.sender_id, None)
            await event.reply("✅ اتحفظوا الـ 4 رسايل بالتنسيق بتاعهم")
        return

    # الترحيب والرد التلقائي
    if get_setting("welcome") == "on" and event.is_private and event.sender_id!= OWNER_ID:
        await event.reply("أهلاً بيك 👋\nتواصل مع @AzefSupport")

    if get_setting("auto_reply") == "on" and (event.mentioned or event.is_reply) and event.sender_id!= OWNER_ID:
        user_id = event.sender_id
        chat_id = event.chat_id
        current_time = int(time.time())
        c.execute("SELECT last_reply FROM reply_cooldown WHERE user_id=? AND chat_id=?", (user_id, chat_id))
        row = c.fetchone()
        if not row or current_time - row[0] >= 3600:
            reply_text = get_setting("reply_text", "تم استلام رسالتك ✅")
            await event.reply(reply_text)
            c.execute("INSERT OR REPLACE INTO reply_cooldown VALUES (?,?,?)",
                     (user_id, chat_id, current_time))
            DB.commit()

    # إضافة حساب
    state = user_states.get(event.sender_id)
    if isinstance(state, dict) and state.get("step") == "await_phone":
        phone = event.message.text.strip()
        user_states[event.sender_id] = {"step": "await_code", "phone": phone}
        client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, device_model="iPhone 17", password=SESSION_PASSWORD)
        await client.connect()
        try:
            await client.send_code_request(phone)
            user_clients[event.sender_id] = client
            await event.reply("📩 ابعت الكود اللي وصلك")
        except Exception as e:
            await event.reply(f"❌ خطأ: {e}")

    elif isinstance(state, dict) and state.get("step") == "await_code":
        code = event.message.text.strip()
        phone = state["phone"]
        client = user_clients[event.sender_id]
        try:
            await client.sign_in(phone, code)
            session = f"sessions/{phone}.session"
            c.execute("INSERT INTO accounts (phone, session, status) VALUES (?,?, 'active')",
                     (phone, session))
            DB.commit()
            await event.reply(f"✅ تم إضافة الحساب {phone}")
            user_states.clear()
            user_clients.clear()
        except SessionPasswordNeededError:
            user_states[event.sender_id] = {"step": "await_2fa", "phone": phone}
            await event.reply("🔐 ابعت باسورد التحقق بخطوتين")
        except Exception as e:
            await event.reply(f"❌ خطأ: {e}")

    elif isinstance(state, dict) and state.get("step") == "await_2fa":
        password = event.message.text.strip()
        phone = state["phone"]
        client = user_clients[event.sender_id]
        try:
            await client.sign_in(password=password)
            session = f"sessions/{phone}.session"
            c.execute("INSERT INTO accounts (phone, session, status) VALUES (?,?, 'active')",
                     (phone, session))
            DB.commit()
            await event.reply(f"✅ تم إضافة الحساب {phone}")
            user_states.clear()
            user_clients.clear()
        except Exception as e:
            await event.reply(f"❌ خطأ: {e}")

@bot.on(events.NewMessage(pattern='/export'))
async def block_export(event):
    await event.reply("❌ الميزة دي مقفولة لأسباب أمنية")

async def get_first_client():
    c.execute("SELECT session FROM accounts WHERE status='active' LIMIT 1")
    row = c.fetchone()
    if not row:
        return None
    client = TelegramClient(row[0], API_ID, API_HASH, device_model="iPhone 17", password=SESSION_PASSWORD)
    await client.connect()
    return client

async def post_messages(client, chats, messages):
    flood_level = get_setting("flood_level", "متوسط")
    delay = FLOOD_LEVELS[flood_level]
    global posting_active
    posting_active = True
    try:
        for msg_data in messages:
            if not posting_active:
                break
            for chat in chats:
                if not posting_active:
                    break
                try:
                    await client.send_message(chat, msg_data["text"], formatting_entities=msg_data["entities"])
                    await asyncio.sleep(delay)
                except FloodWaitError as e:
                    await bot.send_message(OWNER_ID, f"⚠️ فلود {e.seconds} ثانية")
                    await asyncio.sleep(e.seconds)
            if len(messages) > 1:
                await asyncio.sleep(900)
    except Exception as e:
        await bot.send_message(OWNER_ID, f"خطأ: {e}")
    finally:
        posting_active = False

async def main():
    os.makedirs("sessions", exist_ok=True)
    print("Bot started...")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ الخطأ الحقي: {e}")
        raise
