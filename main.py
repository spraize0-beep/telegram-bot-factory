import asyncio
import json
import os
import subprocess
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button

# --- البيانات الأساسية ---
API_ID = 33595004
API_HASH = 'cbd1066ed026997f2f4a7c4323b7bda7'
ADMIN_ID = 154919127
DB_FILE = 'factory_data.json'
BOTS_FOLDER = 'user_bots'

# سيب دول فاضيين - هنقراهم جوه main()
FACTORY_BOT_TOKEN = None
DEVELOPER_USERNAME = None

# --- بيانات الدفع ---
PAYMENT_INFO = {
    'vodafone': '01105802898',
    'usdt_trc20': 'TWunFGpcDDc63GTDdNxyDHjZ4VdPS6AsMh',
    'ton': 'UQAarGycIaNnngwNAQ1Tek32I3MGroiaeF6p6MxEadimfszt',
    'ltc': 'LZgafAodZxDmjM9Ri51ygZ6dU8UbxE2cPH'
}
PRICE = "6$ - 300EG / شهر"

# --- كود بوت النشر اللي هيتنسخ لكل عميل ---
POSTER_BOT_CODE = '''
import asyncio
import json
import os
import pytz
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.types import Channel, Chat, MessageEntityCustomEmoji
from telethon.errors import SessionPasswordNeededError, FloodWaitError

API_ID = 33595004
API_HASH = 'cbd1066ed026997f2f4a7c4323b7bda7'
BOT_TOKEN = '{BOT_TOKEN}'
ADMIN_ID = {ADMIN_ID}
DEVELOPER_USERNAME = "{DEVELOPER_USERNAME}"
DB_FILE = '{DB_FILE}'

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        'session': None, 'super_groups': [], 'sleep_time': 30, 'msg_delay': 5,
        'msg_texts': ['', '', '', ''], 'current_msg_index': 0, 'msg_stats': [0, 0, 0, 0],
        'send_all_mode': False, 'logs_enabled': True, 'show_time': False,
        'auto_reply_enabled': True, 'auto_reply_text': f'تفضل خاص @{DEVELOPER_USERNAME}',
        'welcome_enabled': True, 'welcome_text': 'أهلاً بيك 🌟', 'welcomed_users': [],
        'use_formatting': True
    }

def save_db():
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

db = load_db()
waiting_for = {}
login_temp = {}
is_posting = False
user_client = None
bot = TelegramClient(f'UserBot_{ADMIN_ID}', API_ID, API_HASH)

def is_admin(uid):
    return uid == ADMIN_ID

def get_current_time():
    if not db.get('show_time', False):
        return ""
    try:
        tz = pytz.timezone('Africa/Cairo')
        now = datetime.now(tz)
        return f"\\n🕐 {now.strftime('%I:%M %p - %d/%m/%Y')}"
    except:
        return ""

async def start_user_client():
    global user_client
    if not db['session'] or not db.get('auto_reply_enabled', True):
        return
    try:
        if user_client and user_client.is_connected():
            await user_client.disconnect()
        user_client = TelegramClient(StringSession(db['session']), API_ID, API_HASH)
        await user_client.start()

        @user_client.on(events.NewMessage(incoming=True))
        async def auto_reply_handler(event):
            if not db.get('auto_reply_enabled', True) or not event.is_group:
                return
            if event.sender_id == (await user_client.get_me()).id:
                return
            me = await user_client.get_me()
            text = event.message.text or ""
            is_mentioned = me.username and f"@{me.username.lower()}" in text.lower()
            if is_mentioned:
                try:
                    await event.reply(db.get('auto_reply_text', f'تفضل خاص @{DEVELOPER_USERNAME}'))
                except:
                    pass
        print(f"✅ الرد التلقائي شغال للعميل {ADMIN_ID}")
    except Exception as e:
        print(f"❌ خطأ: {e}")

def main_menu():
    return [
        [Button.inline("🔑 تسجيل الدخول", b"login_phone")],
        [Button.inline("⚙️ إعدادات النشر", b"settings")],
        [Button.inline("🚀 بدء النشر", b"start_post")],
        [Button.url('👨‍💻 مراسلة المبرمج', f'https://t.me/{DEVELOPER_USERNAME}')]
    ]

def settings_menu():
    status = "🟢 مفعل" if db['session'] else "🔴 غير مربوط"
    groups_count = len(db['super_groups'])
    reply_status = "💬 الرد: مفعل" if db.get('auto_reply_enabled', True) else "💬 الرد: معطل"
    mode_status = "📤 وضع: الكل" if db.get('send_all_mode', False) else "🔄 وضع: تدوير"
    stats = db.get('msg_stats', [0, 0, 0, 0])

    return [
        [Button.inline(status, b"none")],
        [Button.inline(reply_status, b"toggle_reply")],
        [Button.inline(mode_status, b"toggle_mode")],
        [Button.inline(f"📩 ر1 ({stats[0]})", b"add_msg_0"), Button.inline(f"📩 ر2 ({stats[1]})", b"add_msg_1")],
        [Button.inline(f"📩 ر3 ({stats[2]})", b"add_msg_2"), Button.inline(f"📩 ر4 ({stats[3]})", b"add_msg_3")],
        [Button.inline("📥 جلب المجموعات", b"fetch_groups")],
        [Button.inline(f"👥 السوبرات: {groups_count}", b"show_links")],
        [Button.inline("➕ إضافة يدوي", b"add_links"), Button.inline("👤 ربط حساب", b"login_phone")],
        [Button.inline(f"⏱️ وقت الجروب: {db['sleep_time']}ث", b"set_time")],
        [Button.inline("🔴 إيقاف", b"stop_post"), Button.inline("🟢 بدء النشر", b"start_post")],
        [Button.inline("🔙 رجوع", b"back_main")]
    ]

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if not is_admin(event.sender_id):
        return await event.reply("❌ البوت ده خاص")

    if event.is_private and db.get('welcome_enabled', True):
        if str(event.sender_id) not in db.get('welcomed_users', []):
            await event.reply(f"{db.get('welcome_text')}{get_current_time()}")
            db['welcomed_users'].append(str(event.sender_id))
            save_db()
            return

    await event.reply(f"🚀 **بوت النشر الخاص بيك**{get_current_time()}", buttons=main_menu())

@bot.on(events.CallbackQuery)
async def handler(event):
    global is_posting
    data, uid = event.data, event.sender_id

    if not is_admin(uid):
        return await event.answer("البوت ده خاص", alert=True)

    if data == b"back_main":
        await event.edit("🏠 الرئيسية:", buttons=main_menu())
    elif data == b"settings":
        await event.edit("⚙️ الإعدادات:", buttons=settings_menu())
    elif data == b"toggle_reply":
        db['auto_reply_enabled'] = not db.get('auto_reply_enabled', True)
        save_db()
        if db['auto_reply_enabled']:
            asyncio.create_task(start_user_client())
        else:
            if user_client and user_client.is_connected():
                await user_client.disconnect()
        await event.edit("⚙️ الإعدادات:", buttons=settings_menu())
    elif data == b"toggle_mode":
        db['send_all_mode'] = not db.get('send_all_mode', False)
        save_db()
        await event.edit("⚙️ الإعدادات:", buttons=settings_menu())
    elif data == b"stop_post":
        is_posting = False
        await event.answer("🛑 توقف النشر", alert=True)
    elif data == b"start_post":
        if is_posting:
            return await event.answer("🚀 يعمل بالفعل!", alert=True)
        asyncio.create_task(auto_publisher(event))
    elif data == b"login_phone":
        waiting_for[uid] = 'login_phone'
        await event.reply("🔄 أرسل رقم الهاتف مع كود الدولة:")
    elif data.startswith(b"add_msg_"):
        msg_index = int(data.decode().split('_')[-1])
        waiting_for[uid] = f'add_msg_{msg_index}'
        current_msg = db['msg_texts'][msg_index] if db['msg_texts'][msg_index] else "فارغة"
        await event.reply(f"📩 **الرسالة {msg_index + 1} الحالية:**\\n{current_msg}\\n\\n**أرسل النص الجديد:**")
    elif data == b"add_links":
        waiting_for[uid] = 'add_links'
        await event.reply("🔗 **أرسل روابط السوبرات**\\nكل رابط في سطر")
    elif data == b"set_time":
        waiting_for[uid] = 'set_time'
        await event.reply("⏱️ **أدخل مدة الانتظار بالثواني**")

@bot.on(events.NewMessage)
async def inputs(event):
    uid = event.sender_id
    if not is_admin(uid) or not event.text or event.text.startswith('/'):
        return

    step = waiting_for.pop(uid, None)
    if not step:
        return

    text = event.text.strip()

    if step == 'login_phone':
        login_temp[uid] = {'phone': text}
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        try:
            await client.send_code_request(text)
            login_temp[uid]['client'] = client
            waiting_for[uid] = 'login_code'
            await event.reply('📩 أرسل الكود (1-2-3-4-5):')
        except Exception as e:
            await event.reply(f'❌ خطأ: {e}')
            await client.disconnect()
            login_temp.pop(uid, None)
    elif step == 'login_code':
        code = text.replace('-', '')
        temp = login_temp.get(uid)
        if not temp:
            return
        client = temp['client']
        try:
            await client.sign_in(temp['phone'], code)
            db['session'] = client.session.save()
            save_db()
            await event.reply('✅ تم ربط الحساب!')
            asyncio.create_task(start_user_client())
        except SessionPasswordNeededError:
            waiting_for[uid] = 'login_pass'
            login_temp[uid] = client
            await event.reply('🔒 أرسل كلمة مرور التحقق بخطوتين:')
        except Exception as e:
            await event.reply(f'❌ خطأ: {e}')
            await client.disconnect()
            login_temp.pop(uid, None)
    elif step == 'login_pass':
        client = login_temp.get(uid)
        if not client:
            return
        try:
            await client.sign_in(password=text)
            db['session'] = client.session.save()
            save_db()
            await event.reply('✅ تم ربط الحساب!')
            asyncio.create_task(start_user_client())
        except Exception as e:
            await event.reply(f'❌ خطأ: {e}')
        finally:
            await client.disconnect()
            login_temp.pop(uid, None)
    elif step == 'add_links':
        links = [l.strip() for l in text.split('\\n') if l.strip()]
        db['super_groups'].extend(links)
        save_db()
        await event.reply(f'✅ تم إضافة {len(links)} سوبر')
    elif step == 'set_time':
        try:
            db['sleep_time'] = int(text)
            save_db()
            await event.reply(f'✅ تم التحديث إلى {text} ثانية')
        except:
            await event.reply('❌ رقم غير صحيح')
    elif step.startswith('add_msg_'):
        msg_index = int(step.split('_')[-1])
        db['msg_texts'][msg_index] = text
        save_db()
        await event.reply(f'✅ تم حفظ الرسالة {msg_index + 1}')

async def auto_publisher(event):
    global is_posting
    if not db['session']:
        return await event.reply("⚠️ سجل دخول أولاً!")
    available_msgs = [(i, msg) for i, msg in enumerate(db['msg_texts']) if msg.strip()]
    if not available_msgs or not db['super_groups']:
        return await event.reply("⚠️ ضيف رسالة وسوبرات أولاً!")

    is_posting = True
    client = TelegramClient(StringSession(db['session']), API_ID, API_HASH)
    try:
        await client.connect()
        await event.reply(f"✅ **بدء النشر**\\n📊 الجروبات: {len(db['super_groups'])}{get_current_time()}")
        while is_posting:
            for target in db['super_groups']:
                if not is_posting:
                    break
                try:
                    if db.get('send_all_mode', False):
                        for actual_idx, msg_text in available_msgs:
                            if not is_posting:
                                break
                            await client.send_message(int(target), msg_text, parse_mode='markdown')
                            db['msg_stats'][actual_idx] += 1
                            save_db()
                            await asyncio.sleep(db.get('msg_delay', 5))
                    else:
                        msg_idx = db['current_msg_index'] % len(available_msgs)
                        actual_idx, msg_text = available_msgs[msg_idx]
                        await client.send_message(int(target), msg_text, parse_mode='markdown')
                        db['msg_stats'][actual_idx] += 1
                        db['current_msg_index'] = (db['current_msg_index'] + 1) % len(available_msgs)
                        save_db()
                    await asyncio.sleep(db['sleep_time'])
                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds)
                except:
                    continue
            await asyncio.sleep(5)
    except Exception as e:
        await event.reply(f"❌ خطأ: {str(e)}")
    finally:
        is_posting = False
        await client.disconnect()

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    print(f"🚀 بوت العميل {ADMIN_ID} اشتغل!")
    if db['session'] and db.get('auto_reply_enabled', True):
        asyncio.create_task(start_user_client())
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
'''

bot = TelegramClient('Factory_Bot', API_ID, API_HASH)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        'clients': {},
        'pending': {},
        'processes': {}
    }

def save_db():
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

db = load_db()
waiting_for = {}

if not os.path.exists(BOTS_FOLDER):
    os.makedirs(BOTS_FOLDER)

def is_sub(uid):
    uid = str(uid)
    if uid in db.get('clients', {}):
        client = db['clients'][uid]
        if client['active']:
            try:
                expiry = datetime.strptime(client['expiry'], '%Y-%m-%d')
                return expiry > datetime.now()
            except:
                pass
    return False

def main_menu(uid):
    btns = []
    if is_sub(uid):
        btns.append([Button.inline("🤖 بوتاتي", b"my_bots")])
        btns.append([Button.inline("📊 حالة البوت", b"bot_status")])
    else:
        btns.append([Button.inline("💳 اشترك الآن - 300 جنيه", b"payment")])

    if uid == ADMIN_ID:
        btns.append([Button.inline("🔐 لوحة الأدمن", b"admin_panel")])

    btns.append([Button.url('👨‍💻 المبرمج', f'https://t.me/{DEVELOPER_USERNAME}')])
    return btns

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = event.sender_id
    msg = "🏭 **مصنع بوتات النشر التلقائي**\n\n"

    if is_sub(uid):
        client = db['clients'][str(uid)]
        msg += f"✅ **اشتراكك مفعل**\n📅 ينتهي: {client['expiry']}\n\n"
        msg += "تقدر تشغل بوت النشر الخاص بيك من الزراير تحت 👇"
    else:
        msg += "💡 **إزاي يشتغل؟**\n"
        msg += "1. اعمل بوت من @BotFather وخد التوكن\n"
        msg += "2. ادفع الاشتراك\n"
        msg += "3. حط التوكن بتاعك\n"
        msg += "4. مبروك بوتك اشتغل 24/7 🔥\n\n"
        msg += f"💰 **السعر:** {PRICE}"

    await event.reply(msg, buttons=main_menu(uid))

@bot.on(events.CallbackQuery)
async def handler(event):
    data, uid = event.data, event.sender_id

    if data == b"payment":
        msg = f"💳 **الاشتراك الشهري**\n\n"
        msg += "**الأسعار:**\n"
        msg += "📱 فودافون كاش: **300 جنيه**\n"
        msg += "💵 USDT: **6 دولار**\n"
        msg += "💎 TON: **5 TON**\n"
        msg += "⚡ LTC: **6 LTC**\n\n"
        msg += "**دوس على الزر عشان تنسخ العنوان:**"
        await event.edit(msg, buttons=[
            [Button.inline("📱 نسخ فودافون كاش", b"copy_voda")],
            [Button.inline("💵 نسخ USDT TRC20", b"copy_usdt")],
            [Button.inline("💎 نسخ TON", b"copy_ton")],
            [Button.inline("⚡ نسخ Litecoin", b"copy_ltc")],
            [Button.inline("✅ أرسلت المبلغ", b"send_proof")],
            [Button.inline("🔙 رجوع", b"back_main")]
        ])
        return

    # أزرار النسخ
    if data == b"copy_voda":
        await event.answer("📱 رقم فودافون كاش:", alert=True)
        await event.respond(f"`{PAYMENT_INFO['vodafone']}`\n\nدوس على الرقم عشان تنسخه 👆")
        return
    if data == b"copy_usdt":
        await event.answer("💵 عنوان USDT TRC20:", alert=True)
        await event.respond(f"`{PAYMENT_INFO['usdt_trc20']}`\n\nدوس على العنوان عشان تنسخه 👆")
        return
    if data == b"copy_ton":
        await event.answer("💎 عنوان TON:", alert=True)
        await event.respond(f"`{PAYMENT_INFO['ton']}`\n\nدوس على العنوان عشان تنسخه 👆")
        return
    if data == b"copy_ltc":
        await event.answer("⚡ عنوان Litecoin:", alert=True)
        await event.respond(f"`{PAYMENT_INFO['ltc']}`\n\nدوس على العنوان عشان تنسخه 👆")
        return

    if data == b"send_proof":
        db['pending'][str(uid)] = {'time': datetime.now().strftime('%Y-%m-%d %H:%M')}
        save_db()
        await event.edit("📸 **ابعت سكرين شوت التحويل**\n\nبعد التأكيد هطلب منك توكن البوت")
        return

    if data == b"my_bots":
        if not is_sub(uid):
            return await event.answer("اشترك أولاً", alert=True)
        client = db['clients'][str(uid)]
        status = "🟢 شغال" if str(uid) in db.get('processes', {}) else "🔴 متوقف"
        await event.edit(f"🤖 **بوتك**\n\nالحالة: {status}\nينتهي: {client['expiry']}", buttons=[[Button.inline("🔙 رجوع", b"back_main")]])
        return

    if data == b"admin_panel" and uid == ADMIN_ID:
        total = len(db['clients'])
        active = len([c for c in db['clients'].values() if c['active']])
        pending = len(db['pending'])
        msg = f"🔐 **لوحة التحكم**\n\n👥 العملاء: {total}\n🟢 النشطين: {active}\n⏳ معلق: {pending}"
        await event.edit(msg, buttons=[
            [Button.inline("⏳ المدفوعات المعلقة", b"show_pending")],
            [Button.inline("👥 كل العملاء", b"show_clients")],
            [Button.inline("🔙 رجوع", b"back_main")]
        ])
        return

    if data == b"show_pending" and uid == ADMIN_ID:
        pending = db.get('pending', {})
        if not pending:
            return await event.answer("لا يوجد", alert=True)
        msg = "⏳ **المدفوعات المعلقة:**\n\n"
        btns = []
        for user_id in pending.keys():
            msg += f"👤 `{user_id}`\n"
            btns.append([Button.inline(f"✅ تفعيل {user_id}", f"approve_{user_id}")])
        btns.append([Button.inline("🔙 رجوع", b"admin_panel")])
        await event.edit(msg, buttons=btns)
        return

    if data.startswith(b'approve_') and uid == ADMIN_ID:
        user_id = data.decode().split('_')[1]
        db['pending'].pop(user_id, None)
        await event.edit(f"✅ تم التأكيد\n\nاطلب من `{user_id}` يبعت توكن البوت")
        await bot.send_message(int(user_id), "✅ **تم تأكيد الدفع!**\n\nدلوقتي ابعت توكن البوت بتاعك من @BotFather")
        waiting_for[int(user_id)] = 'paid_token'
        save_db()
        return

    if data == b"back_main":
        await event.edit("🏭 **المصنع**", buttons=main_menu(uid))

@bot.on(events.NewMessage)
async def inputs(event):
    uid = event.sender_id
    if not event.text or event.text.startswith('/'):
        return

    step = waiting_for.get(uid)
    if not step:
        return

    text = event.text.strip()

    if step == 'paid_token':
        if ':' not in text or len(text) < 40:
            return await event.reply("❌ التوكن غلط!")

        expiry = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        await create_client_bot(uid, text, expiry)
        waiting_for.pop(uid, None)
        return

async def create_client_bot(user_id, bot_token, expiry):
    uid = str(user_id)

    db['clients'][uid] = {
        'token': bot_token,
        'expiry': expiry,
        'active': True,
        'trial': False
    }
    save_db()

    bot_file = os.path.join(BOTS_FOLDER, f'bot_{uid}.py')
    bot_db_file = os.path.join(BOTS_FOLDER, f'db_{uid}.json')

    code = POSTER_BOT_CODE.format(
        BOT_TOKEN=bot_token,
        ADMIN_ID=user_id,
        DEVELOPER_USERNAME=DEVELOPER_USERNAME,
        DB_FILE=bot_db_file
    )

    with open(bot_file, 'w', encoding='utf-8') as f:
        f.write(code)

    try:
        process = subprocess.Popen(['python', bot_file])
        db['processes'][uid] = process.pid
        save_db()

        await bot.send_message(
            user_id,
            f"🎉 **مبروك! بوتك اشتغل**\n\n"
            f"✅ التوكن: `{bot_token[:20]}...`\n"
            f"📅 ينتهي: {expiry}\n"
            f"💳 اشتراك مدفوع\n\n"
            f"روح لبوتك وابعت /start عشان تبدأ 🚀",
            buttons=main_menu(user_id)
        )

        await bot.send_message(ADMIN_ID, f"🆕 **عميل جديد**\n\n👤 {user_id}\n📅 {expiry}")

    except Exception as e:
        await bot.send_message(user_id, f"❌ خطأ في تشغيل البوت: {str(e)}")
        await bot.send_message(ADMIN_ID, f"❌ خطأ في بوت {user_id}: {str(e)}")

async def main():
    global FACTORY_BOT_TOKEN, DEVELOPER_USERNAME
    FACTORY_BOT_TOKEN = os.environ.get('FACTORY_BOT_TOKEN')
    DEVELOPER_USERNAME = os.environ.get('DEVELOPER_USERNAME')
    
    if not FACTORY_BOT_TOKEN:
        print("❌ FACTORY_BOT_TOKEN مش موجود في Variables")
        return
    if not DEVELOPER_USERNAME:
        print("❌ DEVELOPER_USERNAME مش موجود في Variables")
        return
        
    await bot.start(bot_token=FACTORY_BOT_TOKEN)
    print("🏭 مصنع البوتات اشتغل!")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
