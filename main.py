import asyncio
import os
import json
import time
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import *
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChannelParticipant, ChannelParticipantCreator, ChannelParticipantAdmin
from dotenv import load_dotenv

load_dotenv()

# ==================== الإعدادات ====================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION = os.getenv("SESSION_STRING")  # جلسة حسابك
FORCE_CHANNEL = os.getenv("FORCE_CHANNEL")  # @YourChannel
FORCE_GROUP = os.getenv("FORCE_GROUP", None)  # @YourGroup اختياري

# رسالة الاشتراك الاجباري
FORCE_MESSAGE = """
• **مرحبا 👋**

• **للتواصل معي يجب الاشتراك أولاً**

**اضغط بالأسفل للاشتراك**
• **اشترك هنا : ‹@Programmer_error1› .**
• **اشترك هنا : ‹@Programmer_error2› .**

• **بعد الاشتراك ارسل كلمة "تم" عشان اقدر ارد عليك**
"""

DB_FILE = "database.json"

# ==================== قاعدة البيانات ====================
def load_db():
    if not os.path.exists(DB_FILE):
        return {"whitelist": [], "blocked": [], "verified": []}
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_db():
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

db = load_db()

# ==================== تشغيل اليوزربوت ====================
client = TelegramClient(
    StringSession(SESSION),
    API_ID,
    API_HASH,
    device_model="iPhone 17 Pro",
    system_version="iOS 17.5",
    app_version="10.9.2",
    lang_code="ar",
    system_lang_code="ar"
)

# ==================== فحص الاشتراك ====================
async def is_subscribed(user_id):
    # لو في الوايت ليست عديه
    if user_id in db['whitelist']:
        return True

    # لو متحقق منه قبل كدا عديه
    if user_id in db['verified']:
        return True

    try:
        channel = await client.get_entity(FORCE_CHANNEL)
        await client(GetParticipantRequest(channel, user_id))

        # لو في جروب اجباري كمان
        if FORCE_GROUP:
            group = await client.get_entity(FORCE_GROUP)
            await client(GetParticipantRequest(group, user_id))

        # ضيفه للمتحقق منهم عشان ميفحصش كل مرة
        if user_id not in db['verified']:
            db['verified'].append(user_id)
            save_db()

        return True
    except UserNotParticipantError:
        return False
    except:
        return True  # لو في خطأ عدي عشان ميوقفش البوت

async def get_force_buttons():
    btns = [
        [Button.url("اشترك في القناة", f"https://t.me/{FORCE_CHANNEL.replace('@', '')}")]
    ]
    if FORCE_GROUP:
        btns.append([Button.url("اشترك في الجروب", f"https://t.me/{FORCE_GROUP.replace('@', '')}")])
    btns.append([Button.inline("تحققت من الاشتراك", b"check_sub")])
    return btns

# ==================== فلتر الرسايل الخاصة ====================
@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def auto_force_subscribe(event):
    sender = await event.get_sender()
    uid = sender.id

    # تجاهل نفسك والبوتات والجهات الرسمية
    if sender.is_self or sender.bot or sender.verified:
        return

    # تجاهل الوايت ليست
    if uid in db['whitelist']:
        return

    # تجاهل المحظورين
    if uid in db['blocked']:
        await event.delete()
        return

    # لو بعت "تم" او "done" تحقق من الاشتراك
    if event.text and event.text.lower() in ['تم', 'done', 'donee', 'خلاص', 'اشتركت']:
        if await is_subscribed(uid):
            await event.reply("**تم التحقق بنجاح**\n\nتقدر تتواصل معايا دلوقتي")
            return
        else:
            await event.reply(
                "**لم تشترك بعد**\n\nاشترك في القناة والجروب ثم ارسل تم",
                buttons=await get_force_buttons()
            )
            return

    # فحص الاشتراك
    if not await is_subscribed(uid):
        try:
            await event.reply(
                FORCE_MESSAGE,
                buttons=await get_force_buttons()
            )
            # احذف رسالته عشان متوصلكش
            await event.delete()
        except:
            pass
        return

# ==================== زر التحقق ====================
@client.on(events.CallbackQuery(data=b"check_sub"))
async def check_subscription_button(event):
    uid = event.sender_id

    if await is_subscribed(uid):
        await event.answer("تم التحقق بنجاح", alert=True)
        await event.delete()
        await client.send_message(uid, "**تم التحقق**\n\nتقدر تتواصل معايا دلوقتي")
    else:
        await event.answer("لم تشترك بعد في القناة", alert=True)

# ==================== اوامر التحكم ====================
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.اضافة (.+)'))
async def add_whitelist(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1))
        if user.id not in db['whitelist']:
            db['whitelist'].append(user.id)
            save_db()
            await event.edit(f"**تم اضافة {user.first_name} للوايت ليست**")
        else:
            await event.edit("**موجود بالفعل في الوايت ليست**")
    except:
        await event.edit("**يوزر غلط**")
    await asyncio.sleep(3)
    await event.delete()

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.حظر (.+)'))
async def block_user(event):
    try:
        user = await client.get_entity(event.pattern_match.group(1))
        if user.id not in db['blocked']:
            db['blocked'].append(user.id)
            save_db()
            await event.edit(f"**تم حظر {user.first_name}**")
        else:
            await event.edit("**محظور بالفعل**")
    except:
        await event.edit("**يوزر غلط**")
    await asyncio.sleep(3)
    await event.delete()

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.ايقاف'))
async def stop_force(event):
    db['force_enabled'] = False
    save_db()
    await event.edit("**تم ايقاف الاشتراك الاجباري**")
    await asyncio.sleep(3)
    await event.delete()

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.تشغيل'))
async def start_force(event):
    db['force_enabled'] = True
    save_db()
    await event.edit("**تم تفعيل الاشتراك الاجباري**")
    await asyncio.sleep(3)
    await event.delete()

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.مسح'))
async def clear_verified(event):
    db['verified'] = []
    save_db()
    await event.edit("**تم مسح قائمة المتحقق منهم**")
    await asyncio.sleep(3)
    await event.delete()

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.اوامر'))
async def help_cmd(event):
    text = """
**اوامر اليوزربوت:**

`.اضافة @يوزر` - اضافة للوايت ليست
`.حظر @يوزر` - حظر مستخدم
`.ايقاف` - ايقاف الاشتراك الاجباري
`.تشغيل` - تفعيل الاشتراك الاجباري
`.مسح` - مسح المتحقق منهم
`.اوامر` - عرض الاوامر

**اليوزربوت شغال تلقائي على كل الرسايل الخاصة**
"""
    await event.edit(text)

# ==================== التشغيل ====================
async def main():
    await client.start()
    me = await client.get_me()
    print(f"اليوزربوت شغال على حساب: {me.first_name}")
    print(f"الجهاز: iPhone 17 Pro")
    print(f"القناة الاجباري: {FORCE_CHANNEL}")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
