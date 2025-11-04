import asyncio
import aiohttp
import telebot
from telebot import types
from utils.config import BOT_TOKEN, CHANNEL_USERNAME
from utils.storage import init_db, get_seen, update_seen
from utils.auth import is_member
from utils.channel import create_seen_button

# ================== BOT CONFIG ==================
init_db()
bot = telebot.AsyncTeleBot(BOT_TOKEN)

LAST_POSTS = []  # آخرین 3 پست کانال

# ================== Core placeholder ==================
def core_main(user_id, message):
    bot.loop.create_task(bot.send_message(user_id, "🎉 تمام 3 پست دیده شد! اکنون می‌توانید از ربات استفاده کنید."))

# ================== Get last 3 posts (optimized) ==================
async def get_last_3_posts():
    global LAST_POSTS
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat?chat_id={CHANNEL_USERNAME}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            chat_info = await resp.json()

    # حالا با getChatHistory آخرین پیام‌ها را می‌گیریم
    url_history = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatHistory?chat_id={CHANNEL_USERNAME}&limit=3"
    async with aiohttp.ClientSession() as session:
        async with session.get(url_history) as resp:
            history = await resp.json()

    posts = []
    for msg in history.get('result', []):
        posts.append(msg['message_id'])

    LAST_POSTS = posts
    return LAST_POSTS

# ================== Start command ==================
@bot.message_handler(commands=['start'])
async def start(message):
    user_id = message.from_user.id

    if not is_member(bot, user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("عضویت در کانال ✅", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        await bot.reply_to(message, "برای استفاده از ربات ابتدا عضو کانال شوید:", reply_markup=markup)
        return

    last_posts = await get_last_3_posts()
    seen = get_seen(user_id)
    remaining = [p for p in last_posts if p not in seen]

    if not remaining:
        core_main(user_id, message)
        await bot.reply_to(message, "✅ شما می‌توانید از ربات استفاده کنید (Core فعال شد)")
    else:
        await bot.reply_to(message, f"👀 شما هنوز {len(remaining)} از 3 پست آخر را مشاهده نکرده‌اید.")
        for post_id in remaining:
            btn_markup = create_seen_button(post_id)
            await bot.send_message(user_id, f"پست شماره {post_id}", reply_markup=btn_markup)

# ================== Seen button callback ==================
@bot.callback_query_handler(func=lambda c: c.data.startswith("seen_"))
async def callback_seen(call):
    user_id = call.from_user.id
    post_id = int(call.data.replace("seen_", ""))
    update_seen(user_id, post_id)
    await bot.answer_callback_query(call.id, "✅ ثبت شد")

    last_posts = await get_last_3_posts()
    seen = get_seen(user_id)
    remaining = [p for p in last_posts if p not in seen]

    if not remaining:
        core_main(user_id, call.message)
    else:
        await bot.send_message(user_id, f"👀 هنوز {len(remaining)} پست مانده برای مشاهده")

# ================== Start bot ==================
print("Bot is running...")
bot.infinity_polling()
