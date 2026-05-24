from telethon import TelegramClient, events, Button
import asyncio, json, os
from datetime import datetime, timedelta
import random

API_ID = 37879014
API_HASH = 'db129fe3286650ad869b2891abd72df2'
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 29449730
DEVELOPER_LINK = 'https://t.me/aabdulrahmaan'
REQUIRED_CHANNELS = ['F2F2FFF']
DB_FILE = 'database.json'

bot = TelegramClient('bot', API_ID, API_HASH)
db = {'users': {}, 'codes': {}, 'stats': {'total_sent': 0}, 'login_notifications': True}
waiting_for = {}

def load_db():
    global db
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            db = json.load(f)
    except:
        save_db()

def save_db():
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def get_user_data(uid):
    uid = str(uid)
    if uid not in db['users']:
        db['users'][uid] = {
            'sub_end': None,
            'accounts': {}, 'current_account': None,
            'messages': [{'text': '', 'entities': [], 'file_id': None, 'type': 'text'} for _ in range(4)],
            'publish_interval': 5, 'flood_protection': 2, 'stealth_mode': 'balanced',
            'auto_reply': False, 'auto_reply_msg': '', 'auto_reply_entities': [],
            'welcome_msg': '', 'welcome_entities': [], 'welcome_sent': [],
            'publish_active': False
        }
        save_db()
    return db['users'][uid]

def is_subscribed(uid):
    if uid == ADMIN_ID:
        return True
    user = get_user_data(uid)
    sub_end = user.get('sub_end')
    if not sub_end:
        return False
    return datetime.fromisoformat(sub_end) > datetime.now()

def main_menu(uid):
    btns = [
        [Button.inline("📱 الحسابات", b"accounts_menu")],
        [Button.inline("📤 قسم النشر", b"publish_menu")],
        [Button.inline("🛡️ قسم الحماية", b"protect_menu")],
        [Button.inline("🤖 قسم التفاعل", b"interact_menu")],
        [Button.inline("👥 قسم الجروبات", b"groups_menu")],
        [Button.inline("✨ المميزات", b"features"), Button.inline("💡 النصائح", b"tips")],
        [Button.inline("🛒 شراء بوت مماثل", b"buy_bot"), Button.url("👨‍💻 المبرمج", DEVELOPER_LINK)]
    ]
    if uid == ADMIN_ID:
        btns.insert(0, [Button.inline("👑 لوحة المبرمج", b"admin_menu")])
    return btns

def admin_menu():
    notif_status = "✅" if db.get('login_notifications', True) else "❌"
    return [
        [Button.inline("🔑 كود 30 يوم", b"gen_code_30"), Button.inline("🔑 كود سنة", b"gen_code_365")],
        [Button.inline("👤 تفعيل VIP", b"activate_vip"), Button.inline("🚫 الغاء VIP", b"deactivate_vip")],
        [Button.inline("📢 اذاعة", b"broadcast"), Button.inline("📊 احصائيات", b"admin_stats")],
        [Button.inline(f"{notif_status} اشعارات الدخول", b"toggle_notifications")],
        [Button.inline("💾 نسخة احتياطية", b"backup_sessions")],
        [Button.inline("🔙 رجوع", b"back_main")]
    ]

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = event.sender_id
    user = get_user_data(uid)

    for channel in REQUIRED_CHANNELS:
        try:
            await bot.get_participant(channel, uid)
        except:
            btns = [[Button.url("📢 اشترك هنا", f"https://t.me/{channel}")], [Button.inline("✅ تحققت", b"check_sub")]]
            await event.reply("🔒 اشترك في القناة الاول:", buttons=btns)
            return

    if not is_subscribed(uid):
        btns = [
            [Button.inline("🔑 تفعيل كود", b"activate")],
            [Button.inline("✨ المميزات", b"features")],
            [Button.url("👨‍💻 المبرمج", DEVELOPER_LINK)]
        ]
        await event.reply("🔒 البوت باشتراك مدفوع", buttons=btns)
        return

    acc_count = len(user['accounts'])
    text = f"<b>🔥 بوت النشر الاحترافي</b> <tg-emoji emoji-id='5368324170671202286'>🔥</tg-emoji>\n\n"
    text += f"📱 الحسابات: {acc_count}/1\n"
    text += f"📤 الرسائل المرسلة: {db['stats']['total_sent']}\n\n"
    text += "اختار القسم اللي عايزه:"

    await event.reply(text, buttons=main_menu(uid))

@bot.on(events.CallbackQuery)
async def callback(event):
    uid = event.sender_id
    data = event.data.decode()

    if data == 'back_main':
        await start(event)

    elif data == 'admin_menu' and uid == ADMIN_ID:
        await event.edit("<b>👑 لوحة المبرمج</b>", buttons=admin_menu())

    elif data == 'activate':
        waiting_for[uid] = 'code'
        await event.edit("🔑 ابعت كود التفعيل:", buttons=[[Button.inline("🔙 رجوع", b"back_main")]])

@bot.on(events.NewMessage)
async def handle_messages(event):
    uid = event.sender_id
    if uid not in waiting_for:
        return

    action = waiting_for[uid]
    text = event.raw_text
    user = get_user_data(uid)

    if action == 'code':
        code = text.strip()
        if code in db['codes']:
            days = db['codes'][code]
            user['sub_end'] = (datetime.now() + timedelta(days=days)).isoformat()
            del db['codes'][code]
            save_db()
            del waiting_for[uid]
            await event.reply(f"✅ تم التفعيل {days} يوم")
            await start(event)
        else:
            await event.reply("❌ كود غلط")

import asyncio
from telethon.tl.types import MessageEntityCustomEmoji

running_tasks = {}
user_clients = {}

def publish_menu(uid):
    user = get_user_data(uid)
    acc = get_account(uid)
    if not acc:
        return [[Button.inline("❌ مفيش حساب محدد", b"accounts_menu")], [Button.inline("🔙 رجوع", b"back_main")]]

    status = "🟢 شغال" if user.get('publish_active') else "🔴 متوقف"

    msg_status = []
    for i, m in enumerate(user['messages']):
        if m['type'] == 'sticker' and m['file_id']:
            msg_status.append("✅ ملصق")
        elif m['text']:
            msg_status.append("✅ نص")
        else:
            msg_status.append("❌")

    return [
        [Button.inline(f"📱 {acc['name']} | {status}", b"accounts_menu")],
        [Button.inline(f"📝 رسالة 1 {msg_status[0]}", b"msg1"), Button.inline(f"📝 رسالة 2 {msg_status[1]}", b"msg2")],
        [Button.inline(f"📝 رسالة 3 {msg_status[2]}", b"msg3"), Button.inline(f"📝 رسالة 4 {msg_status[3]}", b"msg4")],
        [Button.inline(f"⏱️ كل {user['publish_interval']} دقيقة", b"set_interval")],
        [Button.inline("🔄 تشغيل التدوير", b"start_rotate"), Button.inline("📢 نشر الكل الآن", b"publish_all")],
        [Button.inline("⛔ ايقاف النشر", b"stop_publish")],
        [Button.inline("🔙 رجوع", b"back_main")]
    ]

async def start_rotation(uid):
    user = get_user_data(uid)
    acc = get_account(uid)
    key = f"{uid}_{user['current_account']}"

    client = await get_user_client(uid)
    if not client:
        await bot.send_message(uid, "❌ الحساب غير متصل")
        user['publish_active'] = False
        save_db()
        return

    msg_index = 0
    while user['publish_active'] and is_subscribed(uid):
        msgs = user['messages']
        if not acc['groups']:
            await bot.send_message(uid, "⚠️ مفيش جروبات")
            user['publish_active'] = False
            save_db()
            return

        # اختار الرسالة الحالية بالتدوير
        msg_data = None
        for i in range(4):
            check_idx = (msg_index + i) % 4
            if msgs[check_idx]['text'] or msgs[check_idx]['file_id']:
                msg_data = msgs[check_idx]
                msg_index = check_idx + 1
                break

        if not msg_data:
            await asyncio.sleep(user['publish_interval'] * 60)
            continue

        sent = 0
        failed = 0
        for group in acc['groups']:
            if not user['publish_active']:
                break
            try:
                entity = group if group.startswith('@') else int(group)
                if msg_data['type'] == 'sticker' and msg_data['file_id']:
                    await client.send_file(entity, msg_data['file_id'])
                else:
                    entities = build_entities(msg_data.get('entities', []))
                    await client.send_message(entity, msg_data['text'], formatting_entities=entities)

                acc['sent_count'] += 1
                db['stats']['total_sent'] += 1
                sent += 1
                save_db()

                await asyncio.sleep(random.randint(5, 10))

            except Exception as e:
                failed += 1
                if 'FLOOD_WAIT' in str(e):
                    wait = int(re.search(r'\d+', str(e)).group())
                    await bot.send_message(uid, f"⚠️ فلود وايت {wait} ثانية")
                    await asyncio.sleep(wait + 60)

        await bot.send_message(uid, f"✅ تم ارسال الرسالة {msg_index} لـ {sent} جروب | فشل: {failed}")
        await asyncio.sleep(user['publish_interval'] * 60)

async def publish_all_now(uid):
    user = get_user_data(uid)
    acc = get_account(uid)
    client = await get_user_client(uid)
    if not client:
        await bot.send_message(uid, "❌ الحساب غير متصل")
        return

    for msg_data in user['messages']:
        if not (msg_data['text'] or msg_data['file_id']):
            continue
        for group in acc['groups']:
            try:
                entity = group if group.startswith('@') else int(group)
                if msg_data['type'] == 'sticker' and msg_data['file_id']:
                    await client.send_file(entity, msg_data['file_id'])
                else:
                    entities = build_entities(msg_data.get('entities', []))
                    await client.send_message(entity, msg_data['text'], formatting_entities=entities)
                await asyncio.sleep(3)
            except:
                pass
    await bot.send_message(uid, "✅ تم النشر لكل الجروبات")

# ===== Callback Handlers =====
@bot.on(events.CallbackQuery)
async def callback(event):
    uid = event.sender_id
    data = event.data.decode()
    user = get_user_data(uid)
    acc = get_account(uid)

    if data == 'publish_menu':
        await event.edit("<b>📤 قسم النشر</b>", buttons=publish_menu(uid))

    elif data == 'start_rotate':
        if not acc:
            await event.answer("❌ حدد حساب الاول", alert=True)
            return
        if not acc['groups']:
            await event.answer("❌ جلب الجروبات الاول", alert=True)
            return
        if not any(m['text'] or m['file_id'] for m in user['messages']):
            await event.answer("❌ ضيف رسالة على الاقل", alert=True)
            return

        user['publish_active'] = True
        save_db()
        asyncio.create_task(start_rotation(uid))
        await event.answer("✅ بدأ التدوير", alert=True)
        await event.edit("<b>📤 قسم النشر</b>", buttons=publish_menu(uid))

    elif data == 'stop_publish':
        user['publish_active'] = False
        save_db()
        await event.answer("⛔ تم الايقاف", alert=True)
        await event.edit("<b>📤 قسم النشر</b>", buttons=publish_menu(uid))

    elif data == 'publish_all':
        asyncio.create_task(publish_all_now(uid))
        await event.answer("🚀 جاري النشر لكل الجروبات", alert=True)

    elif data == 'set_interval':
        waiting_for[uid] = 'pub_interval'
        await event.edit("⏱️ ابعت الوقت بالدقايق بين كل دورة:\nمثال: 3", buttons=[[Button.inline("🔙 رجوع", b"publish_menu")]])

    elif data in ['msg1', 'msg2', 'msg3', 'msg4']:
        idx = int(data[-1]) - 1
        waiting_for[uid] = f'msg_{idx}'
        await event.edit(f"📝 ابعت الرسالة رقم {idx+1}:\nتقدر تبعت نص + ايموجي بريميوم او ملصق", buttons=[[Button.inline("🔙 رجوع", b"publish_menu")]])

# ===== Handle Messages =====
@bot.on(events.NewMessage)
async def handle_messages(event):
    uid = event.sender_id
    if uid not in waiting_for:
        return

    action = waiting_for[uid]
    text = event.raw_text
    user = get_user_data(uid)

    if action.startswith('msg_'):
        idx = int(action.split('_')[1])
        entities = extract_entities_from_message(event.message)
        if event.sticker:
            user['messages'][idx] = {'text': '', 'entities': [], 'file_id': event.sticker.id, 'type': 'sticker'}
        else:
            user['messages'][idx] = {'text': text, 'entities': entities, 'file_id': None, 'type': 'text'}
        save_db()
        del waiting_for[uid]
        await event.reply(f"✅ تم حفظ الرسالة {idx+1}")
        await event.respond("<b>📤 قسم النشر</b>", buttons=publish_menu(uid))

    elif action == 'pub_interval':
        try:
            interval = int(text.strip())
            if interval < 1:
                await event.reply("❌ اقل حاجة دقيقة واحدة")
                return
            user['publish_interval'] = interval
            save_db()
            del waiting_for[uid]
            await event.reply(f"✅ تم تعيين الوقت: كل {interval} دقيقة")
            await event.respond("<b>📤 قسم النشر</b>", buttons=publish_menu(uid))
        except:
            await event.reply("❌ ابعت رقم صحيح")

# ===== قسم الحماية =====
def protect_menu(uid):
    user = get_user_data(uid)
    flood_level = ["❌ متوقف", "🟡 خفيف", "🟢 متوسط", "🛡️ قوي"][user['flood_protection']]
    stealth = STEALTH_MODES[user['stealth_mode']]['name']

    return [
        [Button.inline(f"🛡️ حماية الفلود: {flood_level}", b"flood_level")],
        [Button.inline(f"🥷 وضع التخفي: {stealth}", b"stealth_mode")],
        [Button.inline("🔒 حماية التجميد: ✅ اشعار فقط", b"freeze_info")],
        [Button.inline("🔙 رجوع", b"back_main")]
    ]

@bot.on(events.CallbackQuery)
async def callback_protect(event):
    uid = event.sender_id
    data = event.data.decode()
    user = get_user_data(uid)

    if data == 'protect_menu':
        await event.edit("<b>🛡️ قسم الحماية</b>", buttons=protect_menu(uid))

    elif data == 'flood_level':
        user['flood_protection'] = (user['flood_protection'] + 1) % 4
        save_db()
        await event.edit("<b>🛡️ قسم الحماية</b>", buttons=protect_menu(uid))

    elif data == 'stealth_mode':
        modes = list(STEALTH_MODES.keys())
        current = modes.index(user['stealth_mode'])
        user['stealth_mode'] = modes[(current + 1) % len(modes)]
        save_db()
        await event.edit("<b>🛡️ قسم الحماية</b>", buttons=protect_menu(uid))

    elif data == 'freeze_info':
        await event.answer("🔒 البوت بيبعتلك اشعار بس لو حصل فلود ويوقف النشر لحد ما يخلص", alert=True)

# ===== قسم التفاعل =====
def interact_menu(uid):
    user = get_user_data(uid)
    welcome_status = "✅ شغال" if user.get('welcome_msg') else "❌ متوقف"
    reply_status = "✅ شغال" if user.get('auto_reply') else "❌ متوقف"
    mention_status = "✅ شغال" if user.get('mention_enabled', True) else "❌ متوقف"

    return [
        [Button.inline(f"👋 الترحيب بالخاص: {welcome_status}", b"set_welcome")],
        [Button.inline(f"🤖 الرد التلقائي: {reply_status}", b"toggle_reply")],
        [Button.inline("✏️ تعيين رسالة الرد", b"set_reply_msg")],
        [Button.inline(f"🔔 المنشن والريبلاي: {mention_status}", b"toggle_mention")],
        [Button.inline("🗑️ مسح قائمة المردود عليهم", b"clear_replied")],
        [Button.inline("🔙 رجوع", b"back_main")]
    ]

@bot.on(events.CallbackQuery)
async def callback_interact(event):
    uid = event.sender_id
    data = event.data.decode()
    user = get_user_data(uid)
    acc = get_account(uid)

    if data == 'interact_menu':
        await event.edit("<b>🤖 قسم التفاعل</b>", buttons=interact_menu(uid))

    elif data == 'set_welcome':
        waiting_for[uid] = 'welcome_msg'
        await event.edit("👋 ابعت رسالة الترحيب بالخاص:\nتقدر تستخدم ايموجي بريميوم", buttons=[[Button.inline("🔙 رجوع", b"interact_menu")]])

    elif data == 'toggle_reply':
        user['auto_reply'] = not user.get('auto_reply', False)
        save_db()
        if user['auto_reply'] and acc and acc['active']:
            asyncio.create_task(start_auto_reply(uid))
        await event.edit("<b>🤖 قسم التفاعل</b>", buttons=interact_menu(uid))

    elif data == 'set_reply_msg':
        waiting_for[uid] = 'reply_msg'
        await event.edit("✏️ ابعت رسالة الرد التلقائي على المنشن والريبلاي:", buttons=[[Button.inline("🔙 رجوع", b"interact_menu")]])

    elif data == 'toggle_mention':
        user['mention_enabled'] = not user.get('mention_enabled', True)
        save_db()
        await event.edit("<b>🤖 قسم التفاعل</b>", buttons=interact_menu(uid))

    elif data == 'clear_replied':
        if acc:
            acc['replied_to'] = []
            save_db()
            await event.answer("✅ تم المسح", alert=True)

# ===== قسم الجروبات =====
def groups_menu(uid):
    acc = get_account(uid)
    if not acc:
        return [[Button.inline("❌ مفيش حساب محدد", b"accounts_menu")], [Button.inline("🔙 رجوع", b"back_main")]]

    acc = get_account_defaults(acc)
    return [
        [Button.inline("🔄 جلب الجروبات", b"fetch_groups")],
        [Button.inline("➕ اضافة جروب يدوي", b"add_group")],
        [Button.inline("🗑️ حذف جروب", b"del_group")],
        [Button.inline("🗑️ تفريغ الكل", b"clear_groups")],
        [Button.inline(f"👥 العدد: {len(acc['groups'])} جروب", b"show_groups")],
        [Button.inline("🔙 رجوع", b"back_main")]
    ]

@bot.on(events.CallbackQuery)
async def callback_groups(event):
    uid = event.sender_id
    data = event.data.decode()
    user = get_user_data(uid)
    acc = get_account(uid)

    if data == 'groups_menu':
        await event.edit("<b>👥 قسم الجروبات</b>", buttons=groups_menu(uid))

    elif data == 'fetch_groups':
        if not acc:
            await event.answer("❌ حدد حساب الاول", alert=True)
            return
        msg = await event.edit("⏳ جاري جلب الجروبات...")
        client = await get_user_client(uid)
        if not client:
            await msg.edit("❌ الحساب غير متصل", buttons=[[Button.inline("🔙 رجوع", b"groups_menu")]])
            return

        groups = []
        async for dialog in client.iter_dialogs():
            if dialog.is_group or getattr(dialog.entity, 'megagroup', False):
                groups.append(f"@{dialog.entity.username}" if dialog.entity.username else f"-100{dialog.entity.id}")

        acc['groups'] = groups
        save_db()
        await msg.edit(f"✅ تم جلب {len(groups)} جروب", buttons=groups_menu(uid))

    elif data == 'add_group':
        waiting_for[uid] = 'add_group'
        await event.edit("➕ ابعت يوزر الجروب او الايدي:\nمثال: @group أو -100123456", buttons=[[Button.inline("🔙 رجوع", b"groups_menu")]])

    elif data == 'del_group':
        waiting_for[uid] = 'del_group'
        await event.edit("🗑️ ابعت رقم الجروب للحذف:\n1. الجروب الاول\n2. الجروب التاني", buttons=[[Button.inline("🔙 رجوع", b"groups_menu")]])

    elif data == 'clear_groups':
        acc['groups'] = []
        save_db()
        await event.answer("✅ تم تفريغ الكل", alert=True)
        await event.edit("<b>👥 قسم الجروبات</b>", buttons=groups_menu(uid))

    elif data == 'show_groups':
        acc = get_account_defaults(acc)
        text = "\n".join([f"{i+1}. `{g}`" for i, g in enumerate(acc['groups'][:20]) or "لا يوجد"
        if len(acc['groups']) > 20:
            text += f"\n... و {len(acc['groups'])-20} اخرين"
        await event.edit(f"<b>👥 الجروبات ({len(acc['groups'])}):</b>\n\n{text}", buttons=[[Button.inline("🔙 رجوع", b"groups_menu")]])

# ===== قسم الجلسات =====
def sessions_menu(uid):
    user = get_user_data(uid)
    return [
        [Button.inline("💾 نسخة احتياطية لكل الجلسات", b"backup_sessions")],
        [Button.inline("📥 نسخة لحساب محدد", b"backup_account")],
        [Button.inline("📱 تسجيل حساب جديد", b"add_account")],
        [Button.inline("🔙 رجوع", b"accounts_menu")]
    ]

@bot.on(events.CallbackQuery)
async def callback_sessions(event):
    uid = event.sender_id
    data = event.data.decode()

    if data == 'sessions_menu':
        await event.edit("<b>💾 قسم الجلسات</b>", buttons=sessions_menu(uid))

    elif data == 'backup_sessions':
        backup_sessions()
        await event.answer("✅ تم عمل نسخة احتياطية", alert=True)

    elif data.startswith('backup_account_'):
        acc_id = data.split('_')[2]
        acc = get_user_data(uid)['accounts'][acc_id]
        session = acc.get('session', '')
        await event.respond(f"💾 <b>سيشن {acc['name']}:</b>\n\n<code>{session}</code>\n\n⚠️ احتفظ بيه في مكان آمن")

# ===== تحليل النشر =====
@bot.on(events.CallbackQuery)
async def callback_analyze(event):
    uid = event.sender_id
    data = event.data.decode()
    user = get_user_data(uid)
    acc = get_account(uid)

    if data == 'analyze':
        if not acc:
            await event.answer("❌ حدد حساب الاول", alert=True)
            return

        client = await get_user_client(uid)
        status = "🟢 سليم" if client else "🔴 محظور"

        text = f"<b>📊 تحليل النشر</b>\n\n"
        text += f"الحساب: <code>{acc['name']}</code>\n"
        text += f"الحالة: {status}\n"
        text += f"الجروبات: {len(acc['groups'])}\n"
        text += f"المرسلة: {acc['sent_count']}\n"
        text += f"النشر كل: {user['publish_interval']} دقيقة\n"
        text += f"وضع التخفي: {STEALTH_MODES[user['stealth_mode']]['name']}\n"
        text += f"حماية الفلود: مستوى {user['flood_protection']}\n"
        text += f"اخر خطأ: {acc.get('last_error') or 'لا يوجد'}\n"

        await event.edit(text, buttons=[[Button.inline("🔙 رجوع", b"back_main")]])

# ===== Handle Messages للمرحلة 3 =====
@bot.on(events.NewMessage)
async def handle_messages_stage3(event):
    uid = event.sender_id
    if uid not in waiting_for:
        return

    action = waiting_for[uid]
    text = event.raw_text
    user = get_user_data(uid)
    acc = get_account(uid)

    if action == 'welcome_msg':
        user['welcome_msg'] = text
        user['welcome_entities'] = extract_entities_from_message(event.message)
        save_db()
        del waiting_for[uid]
        await event.reply("✅ تم حفظ رسالة الترحيب")
        await event.respond("<b>🤖 قسم التفاعل</b>", buttons=interact_menu(uid))

    elif action == 'reply_msg':
        user['auto_reply_msg'] = text
        user['auto_reply_entities'] = extract_entities_from_message(event.message)
        save_db()
        del waiting_for[uid]
        await event.reply("✅ تم حفظ رسالة الرد")
        await event.respond("<b>🤖 قسم التفاعل</b>", buttons=interact_menu(uid))

    elif action == 'add_group':
        group = text.strip()
        acc = get_account_defaults(acc)
        if group not in acc['groups']:
            acc['groups'].append(group)
            save_db()
            await event.reply(f"✅ تم اضافة: {group}")
        else:
            await event.reply("⚠️ موجود بالفعل")
        del waiting_for[uid]
        await event.respond("<b>👥 قسم الجروبات</b>", buttons=groups_menu(uid))

    elif action == 'del_group':
        try:
            idx = int(text.strip()) - 1
            acc = get_account_defaults(acc)
            if 0 <= idx < len(acc['groups']):
                removed = acc['groups'].pop(idx)
                save_db()
                await event.reply(f"✅ تم حذف: {removed}")
        except:
            await event.reply("❌ رقم غلط")
        del waiting_for[uid]
        await event.respond("<b>👥 قسم الجروبات</b>", buttons=groups_menu(uid))

load_db()
print("البوت شغال...")
bot.start(bot_token=BOT_TOKEN)
bot.run_until_disconnected()
