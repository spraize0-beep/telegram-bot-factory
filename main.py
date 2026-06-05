import os
import json
import asyncio
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.functions.channels import LeaveChannelRequest, GetParticipantRequest
from telethon.tl.functions.messages import DeleteHistoryRequest
from telethon.tl.types import ChannelParticipantCreator, ChannelParticipantAdmin
from telethon.errors import UserNotParticipantError
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEVELOPER = os.getenv("DEVELOPER", "username_dev")
FORCE_CHANNEL = os.getenv("FORCE_CHANNEL", "channel_username")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
user_sessions = {}
DB_FILE = "database.json"

# ===== نظام قاعدة البيانات =====
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"users": {}, "codes": {}, "shop": []}

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

db = load_db()

# ===== نظام النقاط =====
def get_points(user_id):
    return db["users"].get(str(user_id), {}).get("points", 0)

def add_points(user_id, amount):
    uid = str(user_id)
    if uid not in db["users"]:
        db["users"][uid] = {"points": 0, "vip": False}
    db["users"][uid]["points"] = db["users"][uid].get("points", 0) + amount
    save_db(db)

def remove_points(user_id, amount):
    uid = str(user_id)
    if uid in db["users"]:
        db["users"][uid]["points"] = max(0, db["users"][uid].get("points", 0) - amount)
        save_db(db)
        return True
    return False

# ===== نظام VIP =====
def is_vip(user_id):
    if user_id in ADMIN_IDS:
        return True
    user = db["users"].get(str(user_id))
    if not user or not user.get("vip"):
        return False
    expire = datetime.fromisoformat(user["vip_expire"])
    return datetime.now() < expire

def get_vip_expire(user_id):
    user = db["users"].get(str(user_id))
    if user and user.get("vip"):
        return datetime.fromisoformat(user["vip_expire"]).strftime("%Y-%m-%d %H:%M")
    return None

def add_vip(user_id, days=30):
    expire = datetime.now() + timedelta(days=days)
    uid = str(user_id)
    if uid not in db["users"]:
        db["users"][uid] = {}
    db["users"][uid].update({
        "vip": True,
        "vip_expire": expire.isoformat(),
        "added_at": datetime.now().isoformat()
    })
    save_db(db)

def remove_vip(user_id):
    if str(user_id) in db["users"]:
        db["users"][str(user_id)]["vip"] = False
        save_db(db)

def generate_code(days=30):
    import random, string
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    db["codes"][code] = {"days": days, "used": False, "created": datetime.now().isoformat()}
    save_db(db)
    return code

# ===== التحقق من الاشتراك =====
async def check_subscription(user_id):
    try:
        await bot(GetParticipantRequest(FORCE_CHANNEL, user_id))
        add_points(user_id, 1)
        return True
    except UserNotParticipantError:
        return False
    except:
        return True

def force_sub_buttons():
    return [[Button.url("📢 اشترك في القناة", f"https://t.me/{FORCE_CHANNEL}")],
            [Button.inline("✅ تحققت من الاشتراك", b"check_sub")]]

# ===== الأزرار =====
def main_menu(user_id):
    buttons = [
        [Button.inline("➕ إضافة حساب", b"add_account")],
        [Button.inline("🧹 قائمة التنظيف", b"clean_menu")],
        [Button.inline("🎟️ تفعيل الاشتراك", b"activate_vip")],
        [Button.inline("⭐ المميزات", b"features")],
        [Button.inline("💎 متجر VIP", b"vip_shop")]
    ]
    if user_id in ADMIN_IDS:
        buttons.append([Button.inline("👑 لوحة الأدمن", b"admin_panel")])
    buttons.append([Button.url("👨‍💻 المبرمج", f"https://t.me/{DEVELOPER}")])
    return buttons

def clean_menu_buttons():
    return [
        [Button.inline("📢 تنظيف القنوات", b"clean_channels")],
        [Button.inline("👥 تنظيف الجروبات", b"clean_groups")],
        [Button.inline("💬 تنظيف الخاص", b"clean_private")],
        [Button.inline("🤖 تنظيف البوتات", b"clean_bots")],
        [Button.inline("💣 تنظيف الكل", b"clean_all")],
        [Button.inline("🗑️ حذف الحساب", b"del_account")],
        [Button.inline("🔙 رجوع", b"back")]
    ]

def admin_panel_buttons():
    return [
        [Button.inline("➕ توليد كود", b"gen_code")],
        [Button.inline("👤 تفعيل VIP", b"add_vip")],
        [Button.inline("❌ إلغاء VIP", b"del_vip")],
        [Button.inline("💎 إضافة عرض", b"add_offer")],
        [Button.inline("🗑️ حذف عرض", b"del_offer")],
        [Button.inline("💰 إضافة نقاط", b"add_points")],
        [Button.inline("📊 الإحصائيات", b"stats")],
        [Button.inline("📢 إذاعة", b"broadcast")],
        [Button.inline("🔙 رجوع", b"back")]
    ]

async def check_account(event):
    uid = event.sender_id
    if not await check_subscription(uid):
        await event.edit(
            "<b>⚠️ اشتراك إجباري</b>\n\n"
            f"لازم تشترك في @{FORCE_CHANNEL} الأول",
            buttons=force_sub_buttons(),
            parse_mode='html'
        )
        return None
    if not is_vip(uid):
        await event.edit(
            "<b>🔒 البوت باشتراك مدفوع</b>\n\n"
            "لازم تفعل كود اشتراك أو تشتري من المتجر\n"
            "كلم المطور عشان تشتري كود",
            buttons=[[Button.inline("🎟️ تفعيل كود", b"activate_vip")],
                    [Button.inline("💎 متجر VIP", b"vip_shop")],
                    [Button.url("👨‍💻 المبرمج", f"https://t.me/{DEVELOPER}")]],
            parse_mode='html'
        )
        return None
    if uid not in user_sessions:
        await event.answer("ضيف حسابك الأول", alert=True)
        return None
    return user_sessions[uid]["client"]

# ===== أوامر البوت =====
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if not await check_subscription(event.sender_id):
        return await event.respond(
            "<b>⚠️ اشتراك إجباري</b>\n\n"
            f"لازم تشترك في @{FORCE_CHANNEL} الأول",
            buttons=force_sub_buttons(),
            parse_mode='html'
        )

    user = await event.get_sender()
    name_user = user.first_name
    vip_status = "VIP مفعل" if is_vip(event.sender_id) else "غير مفعل"
    points = get_points(event.sender_id)
    expire = get_vip_expire(event.sender_id)
    expire_text = f"\n<b>⏰ ينتهي:</b> {expire}" if expire else ""

    welcome_text = (
        f'<b><tg-emoji emoji-id="5798482080421649554">🔒</tg-emoji> اهلا بك ‹ {name_user} › في بوت تنظيف الحساب <tg-emoji emoji-id="5796526727840669257">🎲</tg-emoji></b>\n\n'
        f'<b><tg-emoji emoji-id="5796499583647359561">📌</tg-emoji> حالة اشتراكك: {vip_status} <tg-emoji emoji-id="5798941981224737816">🚀</tg-emoji></b>{expire_text}\n'
        f'<b><tg-emoji emoji-id="5798482080421649554">🔒</tg-emoji> نقاطك: {points} <tg-emoji emoji-id="5798941981224737816">🚀</tg-emoji></b>\n\n'
        f'<b><tg-emoji emoji-id="5796499583647359561">📌</tg-emoji> ضيف حسابك وابدأ التنظيف بضغطة زر <tg-emoji emoji-id="5798941981224737816">🚀</tg-emoji></b>'
    )

    await event.respond(welcome_text, buttons=main_menu(event.sender_id), parse_mode='html')

@bot.on(events.CallbackQuery(data=b"check_sub"))
async def check_sub(event):
    if await check_subscription(event.sender_id):
        add_points(event.sender_id, 5)
        await event.edit("<b>✅ تم التحقق من الاشتراك</b>\n+5 نقاط هدية 🎁", buttons=main_menu(event.sender_id), parse_mode='html')
    else:
        await event.answer("❌ لسه مشتركتش في القناة", alert=True)

# ===== متجر VIP =====
@bot.on(events.CallbackQuery(data=b"vip_shop"))
async def vip_shop(event):
    points = get_points(event.sender_id)
    shop_text = f"<b>💎 متجر VIP</b>\n\nنقاطك: {points} 💎\n\n"

    if not db["shop"]:
        shop_text += "<b>لا توجد عروض حالياً</b>"
        buttons = [[Button.inline("🔙 رجوع", b"back")]]
    else:
        buttons = []
        for i, offer in enumerate(db["shop"]):
            shop_text += f"<b>{i+1}. {offer['name']}</b>\n"
            shop_text += f" المدة: {offer['days']} يوم\n"
            shop_text += f" السعر: {offer['price']} نقطة\n\n"
            buttons.append([Button.inline(f"شراء - {offer['price']} 💎", f"buy_{i}")])
        buttons.append([Button.inline("🔙 رجوع", b"back")])

    await event.edit(shop_text, buttons=buttons, parse_mode='html')

@bot.on(events.CallbackQuery(pattern=b"buy_"))
async def buy_offer(event):
    idx = int(event.data.decode().split("_")[1])
    if idx >= len(db["shop"]):
        return await event.answer("❌ عرض غير موجود", alert=True)

    offer = db["shop"][idx]
    points = get_points(event.sender_id)

    if points < offer["price"]:
        return await event.answer(f"❌ نقاطك مش كفاية\nمحتاج {offer['price']} نقطة", alert=True)

    remove_points(event.sender_id, offer["price"])
    add_vip(event.sender_id, offer["days"])
    await event.edit(
        f"<b>✅ تم الشراء بنجاح</b>\n\n"
        f"العرض: {offer['name']}\n"
        f"المدة: {offer['days']} يوم\n"
        f"نقاطك المتبقية: {get_points(event.sender_id)} 💎",
        buttons=main_menu(event.sender_id),
        parse_mode='html'
    )

# ===== نظام VIP =====
@bot.on(events.CallbackQuery(data=b"activate_vip"))
async def activate_vip(event):
    async with bot.conversation(event.sender_id, timeout=120) as conv:
        await conv.send_message("<b>🎟️ ابعت كود التفعيل:</b>", parse_mode='html')
        code_msg = await conv.get_response()
        code = code_msg.text.strip().upper()

        if code in db["codes"] and not db["codes"][code]["used"]:
            days = db["codes"][code]["days"]
            add_vip(event.sender_id, days)
            add_points(event.sender_id, 50)
            db["codes"][code]["used"] = True
            db["codes"][code]["used_by"] = event.sender_id
            save_db(db)
            await conv.send_message(
                f"<b>✅ تم تفعيل الاشتراك بنجاح</b>\nالمدة: {days} يوم\n+50 نقطة هدية 🎁",
                buttons=main_menu(event.sender_id),
                parse_mode='html'
            )
        else:
            await conv.send_message("<b>❌ كود خاطئ أو مستخدم قبل كده</b>", buttons=main_menu(event.sender_id), parse_mode='html')

# ===== لوحة الأدمن =====
@bot.on(events.CallbackQuery(data=b"admin_panel"))
async def admin_panel(event):
    if event.sender_id not in ADMIN_IDS:
        return await event.answer("❌ مش أدمن", alert=True)
    await event.edit("<b>👑 لوحة تحكم الأدمن</b>", buttons=admin_panel_buttons(), parse_mode='html')

@bot.on(events.CallbackQuery(data=b"gen_code"))
async def gen_code(event):
    if event.sender_id not in ADMIN_IDS:
        return
    async with bot.conversation(event.sender_id, timeout=60) as conv:
        await conv.send_message("<b>اكتب عدد الأيام:</b>\nمثال: 30", parse_mode='html')
        days_msg = await conv.get_response()
        try:
            days = int(days_msg.text)
            code = generate_code(days)
            await conv.send_message(f"<b>✅ تم توليد الكود:</b>\n\n<code>{code}</code>\n\nالمدة: {days} يوم\n\nاضغط على الكود للنسخ", parse_mode='html')
        except:
            await conv.send_message("<b>❌ رقم غير صحيح</b>", parse_mode='html')

@bot.on(events.CallbackQuery(data=b"add_vip"))
async def add_vip_cmd(event):
    if event.sender_id not in ADMIN_IDS:
        return
    async with bot.conversation(event.sender_id, timeout=120) as conv:
        await conv.send_message("<b>ابعت ID المستخدم:</b>", parse_mode='html')
        uid_msg = await conv.get_response()
        await conv.send_message("<b>عدد الأيام:</b>", parse_mode='html')
        days_msg = await conv.get_response()
        try:
            uid = int(uid_msg.text)
            days = int(days_msg.text)
            add_vip(uid, days)
            await conv.send_message(f"<b>✅ تم تفعيل VIP للمستخدم {uid}</b>\nالمدة: {days} يوم", parse_mode='html')
        except:
            await conv.send_message("<b>❌ بيانات خاطئة</b>", parse_mode='html')

@bot.on(events.CallbackQuery(data=b"del_vip"))
async def del_vip_cmd(event):
    if event.sender_id not in ADMIN_IDS:
        return
    async with bot.conversation(event.sender_id, timeout=60) as conv:
        await conv.send_message("<b>ابعت ID المستخدم:</b>", parse_mode='html')
        uid_msg = await conv.get_response()
        try:
            uid = int(uid_msg.text)
            remove_vip(uid)
            await conv.send_message(f"<b>✅ تم إلغاء VIP للمستخدم {uid}</b>", parse_mode='html')
        except:
            await conv.send_message("<b>❌ ID خاطئ</b>", parse_mode='html')

@bot.on(events.CallbackQuery(data=b"add_offer"))
async def add_offer(event):
    if event.sender_id not in ADMIN_IDS:
        return
    async with bot.conversation(event.sender_id, timeout=180) as conv:
        await conv.send_message("<b>اسم العرض:</b>\nمثال: VIP شهر", parse_mode='html')
        name_msg = await conv.get_response()
        await conv.send_message("<b>عدد الأيام:</b>", parse_mode='html')
        days_msg = await conv.get_response()
        await conv.send_message("<b>السعر بالنقاط:</b>", parse_mode='html')
        price_msg = await conv.get_response()
        try:
            offer = {
                "name": name_msg.text,
                "days": int(days_msg.text),
                "price": int(price_msg.text)
            }
            db["shop"].append(offer)
            save_db(db)
            await conv.send_message("<b>✅ تم إضافة العرض للمتجر</b>", parse_mode='html')
        except:
            await conv.send_message("<b>❌ بيانات خاطئة</b>", parse_mode='html')

@bot.on(events.CallbackQuery(data=b"del_offer"))
async def del_offer(event):
    if event.sender_id not in ADMIN_IDS:
        return
    if not db["shop"]:
        return await event.answer("❌ مفيش عروض", alert=True)
    async with bot.conversation(event.sender_id, timeout=60) as conv:
        offers_text = "<b>العروض الحالية:</b>\n\n"
        for i, offer in enumerate(db["shop"]):
            offers_text += f"{i+1}. {offer['name']} - {offer['days']} يوم - {offer['price']} نقطة\n"
        offers_text += "\n<b>ابعت رقم العرض للحذف:</b>"
        await conv.send_message(offers_text, parse_mode='html')
        idx_msg = await conv.get_response()
        try:
            idx = int(idx_msg.text) - 1
            if 0 <= idx < len(db["shop"]):
                del db["shop"][idx]
                save_db(db)
                await conv.send_message("<b>✅ تم حذف العرض</b>", parse_mode='html')
            else:
                await conv.send_message("<b>❌ رقم غير صحيح</b>", parse_mode='html')
        except:
            await conv.send_message("<b>❌ رقم غير صحيح</b>", parse_mode='html')

@bot.on(events.CallbackQuery(data=b"add_points"))
async def add_points_cmd(event):
    if event.sender_id not in ADMIN_IDS:
        return
    async with bot.conversation(event.sender_id, timeout=120) as conv:
        await conv.send_message("<b>ابعت ID المستخدم:</b>", parse_mode='html')
        uid_msg = await conv.get_response()
        await conv.send_message("<b>عدد النقاط:</b>", parse_mode='html')
        points_msg = await conv.get_response()
        try:
            uid = int(uid_msg.text)
            points = int(points_msg.text)
            add_points(uid, points)
            await conv.send_message(f"<b>✅ تم إضافة {points} نقطة للمستخدم {uid}</b>", parse_mode='html')
        except:
            await conv.send_message("<b>❌ بيانات خاطئة</b>", parse_mode='html')

@bot.on(events.CallbackQuery(data=b"stats"))
async def stats(event):
    if event.sender_id not in ADMIN_IDS:
        return
    total_users = len(db["users"])
    vip_users = sum(1 for u in db["users"].values() if u.get("vip"))
    total_codes = len(db["codes"])
    used_codes = sum(1 for c in db["codes"].values() if c["used"])
    total_points = sum(u.get("points", 0) for u in db["users"].values())

    stats_text = (
        f"<b>📊 إحصائيات البوت:</b>\n\n"
        f"👥 إجمالي المستخدمين: {total_users}\n"
        f"⭐ المشتركين VIP: {vip_users}\n"
        f"🎟️ الأكواد الكلية: {total_codes}\n"
        f"✅ الأكواد المستخدمة: {used_codes}\n"
        f"💎 إجمالي النقاط: {total_points}\n"
        f"📱 الحسابات المضافة: {len(user_sessions)}\n"
        f"🛍️ العروض في المتجر: {len(db['shop'])}"
    )
    await event.edit(stats_text, buttons=[[Button.inline("🔙 رجوع", b"admin_panel")]], parse_mode='html')

@bot.on(events.CallbackQuery(data=b"broadcast"))
async def broadcast(event):
    if event.sender_id not in ADMIN_IDS:
        return
    async with bot.conversation(event.sender_id, timeout=300) as conv:
        await conv.send_message("<b>📢 ابعت الرسالة للإذاعة:</b>", parse_mode='html')
        msg = await conv.get_response()
        count = 0
        for uid in db["users"].keys():
            try:
                await bot.send_message(int(uid), msg.text, parse_mode='html')
                count += 1
                await asyncio.sleep(0.5)
            except: pass
        await conv.send_message(f"<b>✅ تم الإرسال لـ {count} مستخدم</b>", parse_mode='html')

@bot.on(events.CallbackQuery(data=b"features"))
async def features(event):
    features_text = (
        "<b>⭐ مميزات البوت:</b>\n\n"
        "🔒 <b>أمان كامل:</b> تأخير تلقائي بين العمليات\n"
        "🚀 <b>سرعة عالية:</b> تنظيف مئات المحادثات بدقايق\n"
        "📌 <b>ذكي:</b> بيتخطى الجروبات اللي انت أدمن فيها\n"
        "🎲 <b>شامل:</b> قنوات + جروبات + خاص + بوتات\n"
        "💎 <b>نظام نقاط:</b> اكسب نقاط على كل استخدام\n"
        "🛍️ <b>متجر VIP:</b> اشتري اشتراك بالنقاط\n"
        "🔒 <b>حذف من الطرفين:</b> للرسايل الجديدة في الخاص\n"
        "⭐ <b>نظام VIP:</b> باشتراك شهري\n"
        "🚀 <b>واجهة سهلة:</b> كل حاجة بضغطة زر\n\n"
        "<b>⚠️ تنبيه:</b> استخدم البوت بحذر"
    )
    await event.edit(features_text, buttons=[[Button.inline("🔙 رجوع", b"back")]], parse_mode='html')

# ===== إضافة حساب =====
@bot.on(events.CallbackQuery(data=b"add_account"))
async def add_account(event):
    if not await check_subscription(event.sender_id):
        return await event.edit(
            "<b>⚠️ اشتراك إجباري</b>\n\n"
            f"لازم تشترك في @{FORCE_CHANNEL} الأول",
            buttons=force_sub_buttons(),
            parse_mode='html'
        )

    if not is_vip(event.sender_id):
        return await event.answer("🔒 لازم تفعل اشتراك VIP الأول", alert=True)

    async with bot.conversation(event.sender_id, timeout=300) as conv:
        await conv.send_message("ابعت رقم الحساب مع كود الدولة: `+2010xxxxxxx`\n\nلإلغاء العملية ابعت /cancel")
        phone_msg = await conv.get_response()
        if phone_msg.text == '/cancel':
            return await conv.send_message("تم الإلغاء", buttons=main_menu(event.sender_id))

        phone = phone_msg.text
        await conv.send_message("تمام. دلوقتي ابعت كود التفعيل اللي وصلك:")

        client = TelegramClient(StringSession(), API_ID, API_HASH)
        client._init_request.app_version = "iPhone 17 Pro"
        client._init_request.device_model = "iPhone 17 Pro"
        client._init_request.system_version = "iOS 18.0"

        await client.connect()
        try:
            await client.send_code_request(phone)
        except Exception as e:
            return await conv.send_message(f"خطأ: {e}\nاتأكد من الرقم", buttons=main_menu(event.sender_id))

        code = (await conv.get_response()).text
        try:
            await client.sign_in(phone, code)
        except:
            await conv.send_message("فيه تحقق بخطوتين؟ ابعت الباسورد:")
            password = (await conv.get_response()).text
            await client.sign_in(password=password)

        me = await client.get_me()
        user_sessions[event.sender_id] = {"client": client, "phone": phone, "user_id": me.id}
        add_points(event.sender_id, 10)
        await conv.send_message(
            f"✅ تم إضافة الحساب بنجاح\nالرقم: `{phone}`\n+10 نقاط هدية 🎁",
            buttons=clean_menu_buttons()
        )

@bot.on(events.CallbackQuery(data=b"clean_menu"))
async def clean_menu(event):
    client = await check_account(event)
    if not client: return
    add_points(event.sender_id, 2)
    await event.edit("<b>اختر عملية التنظيف:</b>", buttons=clean_menu_buttons(), parse_mode='html')

# ===== دوال التنظيف مع النقاط =====
@bot.on(events.CallbackQuery(data=b"clean_channels"))
async def clean_channels(event):
    client = await check_account(event)
    if not client: return
    msg = await event.edit("<b>جاري فحص القنوات...</b>", parse_mode='html')
    count_left, count_skipped = 0, 0
    async for dialog in client.iter_dialogs():
        if dialog.is_channel and not dialog.is_group:
            if dialog.entity.username and dialog.entity.username.lower() == FORCE_CHANNEL.lower():
                continue
            try:
                participant = await client(GetParticipantRequest(dialog.id, 'me'))
                if isinstance(participant.participant, (ChannelParticipantCreator, ChannelParticipantAdmin)):
                    count_skipped += 1
                    continue
                await client(LeaveChannelRequest(dialog.id))
                count_left += 1
                add_points(event.sender_id, 1)
                await msg.edit(f"<b>تنظيف القنوات</b>\nخرجت من: {count_left}\nتخطيت: {count_skipped}", parse_mode='html')
                await asyncio.sleep(2)
            except: pass
    await msg.edit(f"<b>✅ خلصنا تنظيف القنوات</b>\nخرجت من: {count_left}\nسبت: {count_skipped} كأدمن/مالك\n+{count_left} نقطة 💎", buttons=clean_menu_buttons(), parse_mode='html')

@bot.on(events.CallbackQuery(data=b"clean_groups"))
async def clean_groups(event):
    client = await check_account(event)
    if not client: return
    msg = await event.edit("<b>جاري فحص الجروبات...</b>", parse_mode='html')
    count_left, count_skipped = 0, 0
    async for dialog in client.iter_dialogs():
        if dialog.is_group:
            try:
                participant = await client(GetParticipantRequest(dialog.id, 'me'))
                if isinstance(participant.participant, (ChannelParticipantCreator, ChannelParticipantAdmin)):
                    count_skipped += 1
                    continue
                await client(LeaveChannelRequest(dialog.id))
                count_left += 1
                add_points(event.sender_id, 1)
                await msg.edit(f"<b>تنظيف الجروبات</b>\nخرجت من: {count_left}\nتخطيت: {count_skipped}", parse_mode='html')
                await asyncio.sleep(2)
            except: pass
    await msg.edit(f"<b>✅ خلصنا تنظيف الجروبات</b>\nخرجت من: {count_left}\nسبت: {count_skipped} كأدمن/مالك\n+{count_left} نقطة 💎", buttons=clean_menu_buttons(), parse_mode='html')

@bot.on(events.CallbackQuery(data=b"clean_private"))
async def clean_private(event):
    client = await check_account(event)
    if not client: return
    msg = await event.edit("<b>جاري حذف المحادثات الخاصة...</b>", parse_mode='html')
    count = 0
    async for dialog in client.iter_dialogs():
        if dialog.is_user and not dialog.entity.bot:
            try:
                await client(DeleteHistoryRequest(peer=dialog.id, max_id=0, just_clear=False, revoke=True))
                count += 1
                add_points(event.sender_id, 1)
                await msg.edit(f"<b>تنظيف الخاص</b>\nتم حذف: {count} محادثة", parse_mode='html')
                await asyncio.sleep(1.5)
            except: pass
    await msg.edit(f"<b>✅ خلصنا تنظيف الخاص</b>\nتم حذف: {count} محادثة\n+{count} نقطة 💎", buttons=clean_menu_buttons(), parse_mode='html')

@bot.on(events.CallbackQuery(data=b"clean_bots"))
async def clean_bots(event):
    client = await check_account(event)
    if not client: return
    msg = await event.edit("<b>جاري حذف البوتات...</b>", parse_mode='html')
    count = 0
    async for dialog in client.iter_dialogs():
        if dialog.is_user and dialog.entity.bot:
            try:
                await client(DeleteHistoryRequest(peer=dialog.id, max_id=0, just_clear=False, revoke=True))
                count += 1
                add_points(event.sender_id, 1)
                await msg.edit(f"<b>تنظيف البوتات</b>\nتم حذف: {count} بوت", parse_mode='html')
                await asyncio.sleep(1)
            except: pass
    await msg.edit(f"<b>✅ خلصنا تنظيف البوتات</b>\nتم حذف: {count} بوت\n+{count} نقطة 💎", buttons=clean_menu_buttons(), parse_mode='html')

@bot.on(events.CallbackQuery(data=b"clean_all"))
async def clean_all(event):
    client = await check_account(event)
    if not client: return
    buttons = [[Button.inline("✅ متأكد، نفذ", b"confirm_all")], [Button.inline("❌ إلغاء", b"clean_menu")]]
    await event.edit("<b>تحذير: تنظيف الكل هيحذف كل حاجة</b>\nالقنوات + الجروبات + الخاص + البوتات\n\nمتأكد؟", buttons=buttons, parse_mode='html')

@bot.on(events.CallbackQuery(data=b"confirm_all"))
async def confirm_all(event):
    await event.edit("<b>بدء التنظيف الكامل...</b>", parse_mode='html')
    await clean_channels(event)
    await asyncio.sleep(3)
    await clean_groups(event)
    await asyncio.sleep(3)
    await clean_private(event)
    await asyncio.sleep(3)
    await clean_bots(event)
    await event.respond("<b>💣 تم الانتهاء من تنظيف الكل</b>", buttons=clean_menu_buttons(), parse_mode='html')

@bot.on(events.CallbackQuery(data=b"del_account"))
async def del_account(event):
    if event.sender_id in user_sessions:
        await user_sessions[event.sender_id]["client"].disconnect()
        del user_sessions[event.sender_id]
        await event.edit("✅ تم حذف الحساب من البوت", buttons=main_menu(event.sender_id))
    else:
        await event.answer("مفيش حساب مضاف", alert=True)

@bot.on(events.CallbackQuery(data=b"back"))
async def back(event):
    await event.edit("<b>القائمة الرئيسية:</b>", buttons=main_menu(event.sender_id), parse_mode='html')

print("Bot is running...")
bot.run_until_disconnected()
