import asyncio
import json
import os
import qrcode
import io
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button

API_ID = 33595004
API_HASH = 'cbd1066ed026997f2f4a7c4323b7bda7'
ADMIN_ID = 6771222119
DB_FILE = 'esim_shop_db.json'

PAYMENT_INFO = {
    'ltc': 'LZgafAodZxDmjM9Ri51ygZ6dU8UbxE2cPH',
    'ton': 'UQAarGycIaNnngwNAQ1Tek32I3MGroiaeF6p6MxEadimfszt',
    'usdt_trc20': 'TWunFGpcDDc63GTDdNxyDHjZ4VdPS6AsMh'
}

CRYPTO_PRICES = {
    'ltc': 70,
    'ton': 5,
    'usdt': 1
}

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

def calculate_crypto_amount(usd_price, crypto):
    crypto_price = CRYPTO_PRICES.get(crypto, 1)
    return round(usd_price / crypto_price, 6)

async def deliver_esim(bot, db, uid, esim_id, tx_hash="Manual"):
    """يسلم الشريحة بعد موافقة الأدمن"""
    esim = None
    for country, esims in db['esims'].items():
        for e in esims:
            if e['id'] == esim_id and not e['used']:
                esim = e
                break
        if esim:
            break

    if not esim:
        await bot.send_message(uid, "❌ عذراً الباقة خلصت، كلمني @AzefDev")
        return False

    # علمها مستخدمة
    esim['used'] = True
    esim['sold_to'] = uid
    esim['sold_date'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    esim['tx_hash'] = tx_hash

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
        'date': esim['sold_date'],
        'tx_hash': tx_hash
    }

    # حدث الإحصائيات
    db['stats']['total_orders'] += 1
    db['stats']['total_sales'] += esim['price']
    db['stats']['total_profit'] += profit
    db['stats']['pending_withdraw'] += profit

    save_db(db)

    # ابعت الـ QR Code
    qr_img = generate_qr(esim['code'])
    caption = f"✅ **تم التسليم بنجاح!**\n\n"
    caption += f"📦 الباقة: {esim['name']}\n"
    caption += f"🔢 رقم الطلب: `{order_id}`\n\n"
    caption += f"**كود التفعيل:**\n`{esim['code']}`\n\n"
    caption += "📱 امسح الـ QR أو انسخ الكود\n"
    caption += "⚡ التفعيل في دقيقتين"

    await bot.send_message(uid, caption, file=qr_img)
    return True

async def run_esim_bot():
    BOT_TOKEN = os.environ.get('ESIM_BOT_TOKEN')
    if not BOT_TOKEN:
        print("❌ ضيف ESIM_BOT_TOKEN في Variables")
        return

    db = load_db()
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

    def payment_menu(country, esim_id):
        return [
            [Button.inline("⚡ LTC - Litecoin", f"pay_ltc_{country}_{esim_id}")],
            [Button.inline("💎 TON - Toncoin", f"pay_ton_{country}_{esim_id}")],
            [Button.inline("💵 USDT TRC20", f"pay_usdt_{country}_{esim_id}")],
            [Button.inline("🔙 رجوع", b"buy_esim")]
        ]

    @bot.on(events.NewMessage(pattern='/start'))
    async def start(event):
        if event.sender_id == ADMIN_ID:
            stats = db['stats']
            pending_count = len([p for p in db['pending'].values() if p.get('waiting_approval')])
            msg = f"🔐 **لوحة تحكم الأدمن**\n\n"
            msg += f"⏳ طلبات معلقة: {pending_count}\n"
            msg += f"🛒 الطلبات: {stats['total_orders']}\n"
            msg += f"💰 المبيعات: {stats['total_sales']}$\n"
            msg += f"💵 الأرباح: {stats['total_profit']}$\n"
            msg += f"⏳ معلق للسحب: {stats['pending_withdraw']}$"
            await event.reply(msg, buttons=[
                [Button.inline("⏳ الطلبات المعلقة", b"pending_orders")],
                [Button.inline("📦 المخزون", b"stock")],
                [Button.inline("➕ إضافة eSIM", b"add_esim")],
                [Button.inline("📊 الإحصائيات", b"stats")]
            ])
        else:
            await event.reply(
                "🌍 **متجر شرائح eSIM الرقمية**\n\n"
                "✅ تسليم بعد التأكيد\n"
                "⚡ تفعيل في دقيقتين\n"
                "🔒 دفع كريبتو آمن\n\n"
                "اختار اللي محتاجه 👇",
                buttons=main_menu()
            )

    @bot.on(events.CallbackQuery)
    async def handler(event):
        data, uid = event.data, event.sender_id
        uid_str = str(uid)

        if data == b"back_main":
            if uid == ADMIN_ID:
                await start(event)
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

            await event.edit(
                f"📦 **{esim['name']}**\n\n💰 السعر: **{esim['price']}$**\n\nاختار طريقة الدفع:",
                buttons=payment_menu(country, esim_id)
            )

        elif data.startswith(b"pay_"):
            parts = data.decode().split('_')
            crypto, country, esim_id = parts[1], parts[2], parts[3]

            esim = None
            for e in db['esims'][country]:
                if e['id'] == esim_id and not e['used']:
                    esim = e
                    break

            if not esim:
                return await event.answer("❌ الباقة خلصت", alert=True)

            amount = calculate_crypto_amount(esim['price'], crypto)
            address = PAYMENT_INFO[f"{crypto}_trc20" if crypto == 'usdt' else crypto]

            db['pending'][uid_str] = {
                'country': country,
                'esim_id': esim_id,
                'price': esim['price'],
                'crypto': crypto,
                'amount': amount,
                'address': address,
                'time': datetime.now().isoformat(),
                'waiting_approval': True
            }
            save_db(db)

            msg = f"💳 **الدفع بـ {crypto.upper()}**\n\n"
            msg += f"📦 الباقة: {esim['name']}\n"
            msg += f"💰 المبلغ: **{amount} {crypto.upper()}**\n\n"
            msg += f"**العنوان:**\n`{address}`\n\n"
            msg += "⚠️ **خطوات:**\n"
            msg += "1️⃣ حول المبلغ بالظبط\n"
            msg += "2️⃣ ابعت سكرين التحويل هنا\n"
            msg += "3️⃣ هنأكد الدفع ونسلمك فوراً\n\n"
            msg += "⏳ في انتظار السكرين..."

            await event.edit(msg, buttons=[[Button.inline("❌ إلغاء", b"cancel_order")]])

            # إشعار للأدمن
            user = await event.get_sender()
            username = f"@{user.username}" if user.username else "بدون"
            await bot.send_message(ADMIN_ID, f"🛒 **طلب جديد معلق**\n\n👤 {user.first_name}\n🔗 {username}\n🆔 `{uid}`\n\n📦 {esim['name']}\n💰 {amount} {crypto.upper()}\n\n⏳ في انتظار السكرين")

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

        # أدمن
        elif data == b"pending_orders" and uid == ADMIN_ID:
            pending = {k: v for k, v in db['pending'].items() if v.get('waiting_approval')}
            if not pending:
                return await event.answer("مفيش طلبات معلقة", alert=True)

            msg = "⏳ **الطلبات المعلقة:**\n\n"
            btns = []
            for user_id, order in pending.items():
                esim_name = "غير معروف"
                for e in db['esims'][order['country']]:
                    if e['id'] == order['esim_id']:
                        esim_name = e['name']
                        break
                msg += f"👤 `{user_id}`\n📦 {esim_name}\n💰 {order['amount']} {order['crypto'].upper()}\n\n"
                btns.append([Button.inline(f"✅ موافقة {user_id}", f"approve_{user_id}")])
                btns.append([Button.inline(f"❌ رفض {user_id}", f"reject_{user_id}")])

            btns.append([Button.inline("🔙 رجوع", b"back_main")])
            await event.edit(msg, buttons=btns)

        elif data.startswith(b"approve_") and uid == ADMIN_ID:
            user_id = data.decode().split('_')[1]
            if user_id not in db['pending']:
                return await event.answer("الطلب مش موجود", alert=True)

            order = db['pending'][user_id]
            success = await deliver_esim(bot, db, int(user_id), order['esim_id'], "Manual")

            if success:
                del db['pending'][user_id]
                save_db(db)
                await event.answer("✅ تم التسليم", alert=True)
                await event.edit("✅ تم تسليم الشريحة للعميل", buttons=[[Button.inline("🔙 رجوع", b"back_main")]])

        elif data.startswith(b"reject_") and uid == ADMIN_ID:
            user_id = data.decode().split('_')[1]
            if user_id in db['pending']:
                del db['pending'][user_id]
                save_db(db)
                await bot.send_message(int(user_id), "❌ **تم رفض الطلب**\n\nكلمني @AzefDev للتفاصيل")
                await event.answer("❌ تم الرفض", alert=True)
                await event.edit("❌ تم رفض الطلب", buttons=[[Button.inline("🔙 رجوع", b"back_main")]])

        elif data == b"stock" and uid == ADMIN_ID:
            msg = "📦 **المخزون:**\n\n"
            for country, esims in db['esims'].items():
                available = [e for e in esims if not e['used']]
                msg += f"🌍 **{country.upper()}:** {len(available)} متاح\n"
                for e in available[:3]:
                    msg += f" • {e['name']} - {e['price']}$\n"
            await event.edit(msg, buttons=[[Button.inline("🔙 رجوع", b"back_main")]])

        elif data == b"stats" and uid == ADMIN_ID:
            stats = db['stats']
            msg = f"📊 **الإحصائيات**\n\n"
            msg += f"🛒 الطلبات: {stats['total_orders']}\n"
            msg += f"💰 المبيعات: {stats['total_sales']}$\n"
            msg += f"💵 الأرباح: {stats['total_profit']}$\n"
            msg += f"💎 مسحوب: {stats['withdrawn']}$\n"
            msg += f"⏳ معلق: {stats['pending_withdraw']}$"
            await event.edit(msg, buttons=[[Button.inline("🔙 رجوع", b"back_main")]])

        elif data == b"add_esim" and uid == ADMIN_ID:
            await event.answer("ابعت: الدولة|الاسم|السعر|التكلفة|الكود", alert=True)

    @bot.on(events.NewMessage)
    async def handle_messages(event):
        uid = event.sender_id
        uid_str = str(uid)

        # استلام سكرين الدفع
        if event.photo and uid_str in db['pending'] and db['pending'][uid_str].get('waiting_approval'):
            order = db['pending'][uid_str]
            esim_name = "غير معروف"
            for e in db['esims'][order['country']]:
                if e['id'] == order['esim_id']:
                    esim_name = e['name']
                    break

            # ابعت للأدمن للموافقة
            user = await event.get_sender()
            username = f"@{user.username}" if user.username else "بدون"

            await bot.send_message(
                ADMIN_ID,
                f"📸 **سكرين دفع جديد**\n\n"
                f"👤 {user.first_name}\n"
                f"🔗 {username}\n"
                f"🆔 `{uid}`\n\n"
                f"📦 {esim_name}\n"
                f"💰 {order['amount']} {order['crypto'].upper()}\n"
                f"⏰ {order['time'][:16]}\n\n"
                f"راجع السكرين واضغط موافقة:",
                file=event.photo,
                buttons=[
                    [Button.inline("✅ موافقة وتسليم", f"approve_{uid}")],
                    [Button.inline("❌ رفض", f"reject_{uid}")]
                ]
            )

            await event.reply("✅ **وصل السكرين**\n\n⏳ جاري المراجعة... هنسلمك الشريحة خلال دقايق بعد التأكيد")
            return

        # إضافة eSIM من الأدمن
        if uid == ADMIN_ID and '|' in event.text:
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
            except:
                await event.reply("❌ الصيغة غلط\n\nاستخدم:\n`الدولة|الاسم|السعر|التكلفة|الكود`")

    await bot.start(bot_token=BOT_TOKEN)
    print("🌍 متجر eSIM اشتغل!")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(run_esim_bot())
