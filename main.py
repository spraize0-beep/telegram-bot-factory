import asyncio
import json
import os
import qrcode
import io
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button

API_ID = 33595004
API_HASH = 'cbd1066ed026997f2f4a7c4323b7bda7'
ADMIN_ID = 154919127
DB_FILE = 'esim_shop_db.json'

PAYMENT_INFO = {
    'ltc': 'LZgafAodZxDmjM9Ri51ygZ6dU8UbxE2cPH',
    'ton': 'UQAarGycIaNnngwNAQ1Tek32I3MGroiaeF6p6MxEadimfszt',
    'usdt_trc20': 'TWunFGpcDDc63GTDdNxyDHjZ4VdPS6AsMh'
}

ADMIN_WALLET = 'TWunFGpcDDc63GTDdNxyDHjZ4VdPS6AsMh'
AUTO_WITHDRAW_LIMIT = 50
LOW_STOCK_ALERT = 3

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        'esims': {
            'usa': [
                {'id': 'US001', 'name': 'أمريكا 5GB - 30 يوم', 'price': 10, 'cost': 6, 'code': 'LPA:1$sm-v4-064-001.gcpa.io$12345', 'used': False},
                {'id': 'US002', 'name': 'أمريكا 10GB - 30 يوم', 'price': 15, 'cost': 9, 'code': 'LPA:1$sm-v4-064-001.gcpa.io$67890', 'used': False}
            ],
            'turkey': [
                {'id': 'TR001', 'name': 'تركيا 3GB - 15 يوم', 'price': 6, 'cost': 4, 'code': 'LPA:1$sm-v4-072-001.gcpa.io$11111', 'used': False}
            ],
            'uae': [
                {'id': 'AE001', 'name': 'الإمارات 2GB - 7 أيام', 'price': 5, 'cost': 3, 'code': 'LPA:1$sm-v4-784-001.gcpa.io$22222', 'used': False}
            ]
        },
        'orders': {},
        'pending': {},
        'stats': {
            'total_sales': 0,
            'total_profit': 0,
            'total_orders': 0,
            'pending_withdraw': 0,
            'withdrawn': 0
        }
    }

def save_db(db):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def generate_qr(code):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(code)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO()
    bio.name = 'esim_qr.png'
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio

async def send_daily_report(bot, db):
    today = datetime.now().strftime('%Y-%m-%d')
    today_orders = [o for o in db['orders'].values() if o['date'].startswith(today)]

    today_sales = sum(o['price'] for o in today_orders)
    today_profit = sum(o['price'] - o.get('cost', 0) for o in today_orders)

    msg = f"📊 **تقرير يومي - {today}**\n\n"
    msg += f"🛒 طلبات اليوم: {len(today_orders)}\n"
    msg += f"💰 مبيعات اليوم: {today_sales}$\n"
    msg += f"💵 أرباح اليوم: {today_profit}$\n\n"
    msg += f"📈 **الإجمالي:**\n"
    msg += f"🛒 كل الطلبات: {db['stats']['total_orders']}\n"
    msg += f"💰 كل المبيعات: {db['stats']['total_sales']}$\n"
    msg += f"💵 كل الأرباح: {db['stats']['total_profit']}$\n"
    msg += f"💎 مسحوب: {db['stats']['withdrawn']}$\n"
    msg += f"⏳ معلق للسحب: {db['stats']['pending_withdraw']}$"

    await bot.send_message(ADMIN_ID, msg)

async def check_stock_alert(bot, db):
    for country, esims in db['esims'].items():
        available = [e for e in esims if not e['used']]
        if len(available) <= LOW_STOCK_ALERT and len(available) > 0:
            await bot.send_message(ADMIN_ID, f"⚠️ **تحذير مخزون**\n\n🌍 {country.upper()}\n📦 باقي: {len(available)} شرائح فقط\n\nضيف مخزون جديد بسرعة!")

async def auto_withdraw(bot, db):
    if db['stats']['pending_withdraw'] >= AUTO_WITHDRAW_LIMIT:
        amount = db['stats']['pending_withdraw']
        db['stats']['withdrawn'] += amount
        db['stats']['pending_withdraw'] = 0
        save_db(db)

        await bot.send_message(ADMIN_ID, f"💸 **سحب تلقائي تم**\n\n💰 المبلغ: {amount}$\n💎 المحفظة: `{ADMIN_WALLET}`\n\n⚠️ حول المبلغ يدوياً من محفظتك الشخصية\n\n📊 إجمالي المسحوب: {db['stats']['withdrawn']}$")

async def run_esim_bot():
    BOT_TOKEN = os.environ.get('ESIM_BOT_TOKEN')
    if not BOT_TOKEN:
        print("❌ ضيف ESIM_BOT_TOKEN في Variables")
        return

    db = load_db()
    waiting_for = {}
    bot = TelegramClient('ESIM_Bot', API_ID, API_HASH)

    def main_menu():
        return [
            [Button.inline("🛒 شراء شريحة eSIM", b"buy_esim")],
            [Button.inline("📦 طلباتي", b"my_orders")],
            [Button.inline("❓ طريقة التفعيل", b"how_to")],
            [Button.url('👨‍💻 الدعم الفني', 'https://t.me/AzefDev')]
        ]

    def countries_menu():
        btns = []
        for country, esims in db['esims'].items():
            available = sum(1 for e in esims if not e['used'])
            if available > 0:
                flag = {'usa': '🇺🇸', 'turkey': '🇹🇷', 'uae': '🇦🇪'}.get(country, '🌍')
                btns.append([Button.inline(f"{flag} {country.upper()} ({available} متاح)", f"country_{country}")])
        btns.append([Button.inline("🔙 رجوع", b"back_main")])
        return btns

    def packages_menu(country):
        btns = []
        for esim in db['esims'].get(country, []):
            if not esim['used']:
                btns.append([Button.inline(f"{esim['name']} - {esim['price']}$", f"buy_{country}_{esim['id']}")])
        btns.append([Button.inline("🔙 رجوع", b"buy_esim")])
        return btns

    def admin_menu():
        return [
            [Button.inline("📊 الإحصائيات", b"stats")],
            [Button.inline("📦 المخزون", b"stock")],
            [Button.inline("➕ إضافة eSIM", b"add_esim")],
            [Button.inline("💸 سحب الأرباح", b"withdraw")],
            [Button.inline("🔙 رجوع", b"back_main")]
        ]

    @bot.on(events.NewMessage(pattern='/start'))
    async def start(event):
        if event.sender_id == ADMIN_ID:
            await event.reply("🔐 **لوحة تحكم الأدمن**", buttons=admin_menu())
        else:
            await event.reply(
                "🌍 **متجر شرائح eSIM الرقمية**\n\n"
                "✅ تسليم فوري تلقائي\n"
                "⚡ تفعيل في دقيقتين\n"
                "🔒 آمن 100%\n\n"
                "اختار اللي محتاجه 👇",
                buttons=main_menu()
            )

    @bot.on(events.CallbackQuery)
    async def handler(event):
        data, uid = event.data, event.sender_id
        uid_str = str(uid)

        if data == b"back_main":
            if uid == ADMIN_ID:
                await event.edit("🔐 **لوحة تحكم الأدمن**", buttons=admin_menu())
            else:
                await event.edit("🌍 **متجر شرائح eSIM**", buttons=main_menu())

        elif data == b"buy_esim":
            await event.edit("🌍 **اختار الدولة:**", buttons=countries_menu())

        elif data.startswith(b"country_"):
            country = data.decode().split('_')[1]
            await event.edit(f"📦 **باقات {country.upper()}:**", buttons=packages_menu(country))

        elif data.startswith(b"buy_"):
            parts = data.decode().split('_')
            country, esim_id = parts[1], parts[2]

            esim = None
            for e in db['esims'][country]:
                if e['id'] == esim_id and not e['used']:
                    esim = e
                    break

            if not esim:
                return await event.answer("❌ الباقة دي خلصت", alert=True)

            db['pending'][uid_str] = {
                'country': country,
                'esim_id': esim_id,
                'price': esim['price'],
                'cost': esim.get('cost', 0),
                'name': esim['name'],
                'time': datetime.now().strftime('%Y-%m-%d %H:%M')
            }
            save_db(db)

            msg = f"💳 **تفاصيل الطلب**\n\n"
            msg += f"📦 الباقة: {esim['name']}\n"
            msg += f"💰 السعر: {esim['price']}$\n\n"
            msg += f"**طرق الدفع:**\n\n"
            msg += f"⚡ LTC: `{PAYMENT_INFO['ltc']}`\n\n"
            msg += f"💎 TON: `{PAYMENT_INFO['ton']}`\n\n"
            msg += f"💵 USDT TRC20: `{PAYMENT_INFO['usdt_trc20']}`\n\n"
            msg += "بعد التحويل ابعت سكرين هنا وهيوصلك الكود فوراً ✅"

            await event.edit(msg, buttons=[[Button.inline("❌ إلغاء", b"cancel_order")]])

            user = await event.get_sender()
            username = f"@{user.username}" if user.username else "بدون"
            await bot.send_message(ADMIN_ID, f"🛒 **طلب جديد**\n\n👤 {user.first_name}\n🔗 {username}\n🆔 `{uid}`\n\n📦 {esim['name']}\n💰 {esim['price']}$")

        elif data == b"cancel_order":
            if uid_str in db['pending']:
                del db['pending'][uid_str]
                save_db(db)
            await event.edit("❌ تم إلغاء الطلب", buttons=main_menu())

        elif data == b"my_orders":
            orders = [o for o in db['orders'].values() if o['user_id'] == uid]
            if not orders:
                return await event.answer("مفيش طلبات", alert=True)
            msg = "📦 **طلباتك:**\n\n"
            for o in orders[-5:]:
                msg += f"🔸 {o['name']}\n📅 {o['date']}\n\n"
            await event.edit(msg, buttons=[[Button.inline("🔙 رجوع", b"back_main")]])

        elif data == b"how_to":
            msg = "❓ **طريقة تفعيل eSIM:**\n\n"
            msg += "1️⃣ افتح الإعدادات > خلوي\n"
            msg += "2️⃣ اضغط إضافة شريحة eSIM\n"
            msg += "3️⃣ امسح الـ QR Code\n"
            msg += "4️⃣ فعل الشريحة\n\n"
            msg += "⚠️ لازم يكون موبايلك بيدعم eSIM"
            await event.edit(msg, buttons=[[Button.inline("🔙 رجوع", b"back_main")]])

        # لوحة الأدمن
        elif data == b"stats" and uid == ADMIN_ID:
            stats = db['stats']
            msg = f"📊 **الإحصائيات**\n\n"
            msg += f"🛒 إجمالي الطلبات: {stats['total_orders']}\n"
            msg += f"💰 إجمالي المبيعات: {stats['total_sales']}$\n"
            msg += f"💵 إجمالي الأرباح: {stats['total_profit']}$\n\n"
            msg += f"💎 مسحوب: {stats['withdrawn']}$\n"
            msg += f"⏳ معلق للسحب: {stats['pending_withdraw']}$\n\n"
            msg += f"📦 **المخزون:**\n"
            for country, esims in db['esims'].items():
                available = sum(1 for e in esims if not e['used'])
                msg += f"🌍 {country.upper()}: {available} متاح\n"
            await event.edit(msg, buttons=[[Button.inline("🔙 رجوع", b"back_main")]])

        elif data == b"stock" and uid == ADMIN_ID:
            msg = "📦 **المخزون التفصيلي:**\n\n"
            for country, esims in db['esims'].items():
                available = [e for e in esims if not e['used']]
                msg += f"🌍 **{country.upper()}:** {len(available)} متاح\n"
                for e in available[:3]:
                    msg += f" • {e['name']} - {e['price']}$\n"
            await event.edit(msg, buttons=[[Button.inline("🔙 رجوع", b"back_main")]])

        elif data == b"withdraw" and uid == ADMIN_ID:
            amount = db['stats']['pending_withdraw']
            if amount < 10:
                return await event.answer(f"❌ أقل مبلغ للسحب 10$\nالمتاح: {amount}$", alert=True)
            db['stats']['withdrawn'] += amount
            db['stats']['pending_withdraw'] = 0
            save_db(db)
            await event.edit(f"✅ **تم السحب**\n\n💰 المبلغ: {amount}$\n💎 المحفظة: `{ADMIN_WALLET}`\n\n⚠️ حول المبلغ يدوياً من محفظتك", buttons=[[Button.inline("🔙 رجوع", b"back_main")]])

        elif data == b"add_esim" and uid == ADMIN_ID:
            waiting_for[uid] = 'add_esim'
            await event.edit("📝 **إضافة eSIM جديدة**\n\nابعت بالشكل ده:\n\n`الدولة|الاسم|السعر|التكلفة|الكود`\n\nمثال:\n`usa|أمريكا 5GB|10|6|LPA:1$test$12345`")

    @bot.on(events.NewMessage)
    async def handle_messages(event):
        uid = event.sender_id
        uid_str = str(uid)

        # استلام سكرين الدفع
        if event.photo and uid_str in db['pending']:
            order = db['pending'][uid_str]

            esim = None
            for e in db['esims'][order['country']]:
                if e['id'] == order['esim_id'] and not e['used']:
                    esim = e
                    break

            if not esim:
                del db['pending'][uid_str]
                save_db(db)
                return await event.reply("❌ عذراً الباقة خلصت، هيتم استرداد فلوسك")

            # علمها مستخدمة
            esim['used'] = True
            esim['sold_to'] = uid
            esim['sold_date'] = datetime.now().strftime('%Y-%m-%d %H:%M')

            # سجل الطلب
            order_id = f"ORD{len(db['orders']) + 1:05d}"
            profit = esim['price'] - esim.get('cost', 0)

            db['orders'][order_id] = {
                'user_id': uid,
                'esim_id': esim['id'],
                'name': esim['name'],
                'price': esim['price'],
                'cost': esim.get('cost', 0),
                'profit': profit,
                'code': esim['code'],
                'date': esim['sold_date']
            }

            # حدث الإحصائيات
            db['stats']['total_orders'] += 1
            db['stats']['total_sales'] += esim['price']
            db['stats']['total_profit'] += profit
            db['stats']['pending_withdraw'] += profit

            del db['pending'][uid_str]
            save_db(db)

            # ابعت الـ QR Code
            qr_img = generate_qr(esim['code'])
            caption = f"✅ **تم التسليم بنجاح!**\n\n"
            caption += f"📦 الباقة: {esim['name']}\n"
            caption += f"🔢 رقم الطلب: `{order_id}`\n\n"
            caption += f"**كود التفعيل:**\n`{esim['code']}`\n\n"
            caption += "📱 امسح الـ QR أو انسخ الكود\n"
            caption += "⚡ التفعيل في دقيقتين"

            await event.reply(caption, file=qr_img)

            # إشعار للأدمن
            user = await event.get_sender()
            username = f"@{user.username}" if user.username else "بدون"
            await bot.send_message(ADMIN_ID, f"✅ **تم التسليم تلقائي**\n\n👤 {user.first_name}\n🔗 {username}\n🆔 `{uid}`\n\n📦 {esim['name']}\n💰 {esim['price']}$\n💵 ربح: {profit}$\n🔢 {order_id}", file=event.photo)

            # تحقق من المخزون والسحب التلقائي
            await check_stock_alert(bot, db)
            await auto_withdraw(bot, db)
            return

        # إضافة eSIM من الأدمن
        step = waiting_for.get(uid)
        if step == 'add_esim' and uid == ADMIN_ID:
            try:
                parts = event.text.strip().split('|')
                country, name, price, cost, code = parts[0].strip(), parts[1].strip(), int(parts[2].strip()), int(parts[3].strip()), parts[4].strip()

                if country not in db['esims']:
                    db['esims'][country] = []

                new_id = f"{country.upper()}{len(db['esims'][country]) + 1:03d}"
                db['esims'][country].append({
                    'id': new_id,
                    'name': name,
                    'price': price,
                    'cost': cost,
                    'code': code,
                    'used': False
                })
                save_db(db)

                await event.reply(f"✅ **تمت الإضافة**\n\n🌍 {country}\n📦 {name}\n💰 السعر: {price}$\n💵 التكلفة: {cost}$\n📊 الربح: {price-cost}$\n🆔 {new_id}")
                waiting_for.pop(uid, None)
            except:
                await event.reply("❌ الصيغة غلط\n\nاستخدم:\n`الدولة|الاسم|السعر|التكلفة|الكود`")

    # مهمة يومية للتقرير
    async def daily_task():
        while True:
            now = datetime.now()
            if now.hour == 0 and now.minute == 0:
                await send_daily_report(bot, db)
                await asyncio.sleep(60)
            await asyncio.sleep(30)

    asyncio.create_task(daily_task())

    await bot.start(bot_token=BOT_TOKEN)
    print("🌍 متجر eSIM اشتغل!")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(run_esim_bot())
