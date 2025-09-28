import asyncio
import html
import json
import logging
import requests
import random
import string
from datetime import datetime, timedelta, date
from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import config
import aiohttp

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# Загрузка данных
def load_data():
    with open('data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

# Сохранение данных
def save_data(data):
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Генерация реферального кода
def generate_ref_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=7))

# Тексты сообщений
START_TEXT = """🚀 <b>Добро пожаловать в PR VANISH!</b>

<b>Здесь вы можете:</b>
<i>✅ Продвигать свои каналы и боты</i>
<i>✅ Получать живых подписчиков от других участников</i>
<i>✅ Зарабатывать на взаимной рекламе</i>

📌 <i>Все действия — прямо в этом боте. Никаких сторонних сайтов!</i>

<b><i>Выбирите кнопку ниже, чтобы перейти в нужный раздел.</i></b>"""

# Функции для создания клавиатур (кешированные)
def create_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Баланс", callback_data="balance"), InlineKeyboardButton(text="📢 Заказать пиар", callback_data="pr")],
            [InlineKeyboardButton(text="Мои оп", callback_data="my_subs"), InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
        ]
    )

def create_back_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="↩️ Назад", callback_data="back")]]
    )

def create_pr_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Канал", callback_data="pr_channel"), InlineKeyboardButton(text="Группу", callback_data="pr_group")],
            [InlineKeyboardButton(text="Пост", callback_data="pr_post"), InlineKeyboardButton(text="Бот", callback_data="pr_bot")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="back")]
        ]
    )

def create_channel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 День", callback_data="channel_1d"), InlineKeyboardButton(text="1 Неделя", callback_data="channel_1w"), InlineKeyboardButton(text="1 Месяц", callback_data="channel_1m")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="back")]
        ]
    )

def create_payment_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Оплатить", callback_data="pay_crypto"), InlineKeyboardButton(text="🔗 Оплатить с VANISH", callback_data="pay_vanish")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="back")]
        ]
    )

def create_confirm_channel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Редактировать", callback_data="edit_channel"), InlineKeyboardButton(text="Подтвердить", callback_data="confirm_channel")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="back")]
        ]
    )

# Кешированные клавиатуры
main_keyboard = create_main_keyboard()
back_keyboard = create_back_keyboard()
pr_keyboard = create_pr_keyboard()
channel_keyboard = create_channel_keyboard()
payment_keyboard = create_payment_keyboard()
confirm_channel_keyboard = create_confirm_channel_keyboard()

prices = {
    'channel': {
        '1d': {'usd': 7, 'vanish': 15, 'period': '1 день'},
        '1w': {'usd': 15, 'vanish': 30, 'period': '1 неделю'},
        '1m': {'usd': 50, 'vanish': 100, 'period': '1 месяц'}
    },
    'group': {
        '1d': {'usd': 7, 'vanish': 15, 'period': '1 день'},
        '1w': {'usd': 15, 'vanish': 30, 'period': '1 неделю'},
        '1m': {'usd': 50, 'vanish': 100, 'period': '1 месяц'}
    },
    'bot': {
        '1d': {'usd': 10, 'vanish': 20, 'period': '1 день'},
        '1w': {'usd': 20, 'vanish': 40, 'period': '1 неделю'},
        '1m': {'usd': 70, 'vanish': 140, 'period': '1 месяц'}
    },
    'post': {
        '1d': {'usd': 8, 'vanish': 16, 'period': '1 день'},
        '1w': {'usd': 12, 'vanish': 24, 'period': '1 неделю'},
        '1m': {'usd': 35, 'vanish': 70, 'period': '1 месяц'}
    }
}

async def check_payment(user_id, invoice_id, period, type_):
    """Улучшенная функция проверки оплаты с автоплатой VANISH"""
    logging.info(f"Starting payment check for user {user_id}, invoice {invoice_id}")
    start_time = asyncio.get_event_loop().time()

    # Типы контента для автоплаты
    content_types = {
        'bot': ('бот', "@myrentbot", "@myrentbot"),
        'post': ('пост', "https://t.me/channel/123", "https://t.me/channel/123"),
        'channel': ('канал', "@mychannel", "@mychannel или https://t.me/mychannel"),
        'group': ('группу', "@mygroup", "@mygroup или https://t.me/mygroup")
    }

    item_text, example, important_example = content_types.get(type_, ('контент', "@example", "@example"))

    while asyncio.get_event_loop().time() - start_time < 180:  # 3 минуты
        try:
            response = await asyncio.get_event_loop().run_in_executor(None, lambda: requests.get(
                f"https://pay.crypt.bot/api/getInvoices?invoice_ids={invoice_id}",
                headers={"Crypto-Pay-API-Token": config.CRYPTOBOT_TOKEN}
            ))

            if response.status_code == 200:
                res = response.json()
                if res.get('ok') and res.get('result', {}).get('items'):
                    invoice_item = res['result']['items'][0]

                    if invoice_item.get('status') == 'paid':
                        logging.info(f"Payment successful for user {user_id}")
                        data = load_data()

                        if str(user_id) in data['users']:
                            msg_id = data['users'][str(user_id)]['message_id']

                            text = f"""✅ Оплата USDT подтверждена!

🎉 Скиньте ссылку на ваш {html.escape(item_text)}

📝 <b>Примеры правильного ввода:</b>
• {html.escape(example)}
• {html.escape(important_example)}

⚠️ <b>Поддерживаемые форматы:</b>
• @username
• https://t.me/username
• http://t.me/username
• t.me/username

<i>Бот автоматически исправит формат, если он введен правильно!</i>"""

                            await send_or_edit_message(user_id, msg_id, text)
                            data['users'][str(user_id)]['current_screen'] = 'enter_channel'
                            data['users'][str(user_id)]['ad_period'] = period
                            data['users'][str(user_id)]['ad_type'] = type_
                            save_data(data)
                        break

            # Проверять каждые 3 секунды вместо 1 для снижения нагрузки
            await asyncio.sleep(3)

        except Exception as e:
            logging.error(f"Error in check_payment: {e}")
            await asyncio.sleep(3)

    logging.info(f"Payment check timeout for user {user_id}, invoice {invoice_id}")

BALANCE_TEXT = """💰 <b>Вы можете заработать VANISH
с помощью приглашений в бота</b>

Ваш баланс: <b>{balance} VANISH</b>

Реферальная ссылка: <code>t.me/{bot_username}?start={ref_code}</code>

<b>Как заработать:</b>
1. Поделитесь своей реферальной ссылкой с друзьями.
2. Когда друг перейдет по ссылке и напишет /start, вам начислятся <b>0.1 VANISH</b>.
3. Деньги приходят <i>мгновенно</i> после регистрации друга."""

PR_TEXT = """📢 Заказать пиар

Выберите тип пиара:
1. Реклама в каналах (10 баллов)
2. Репосты (5 баллов)
3. Обмен подписчиками (2 балла)

Отправьте номер для заказа."""

CHANNELS_TEXT = """👥 Мои каналы

Ваши каналы:
{channels}

Добавить канал: отправьте @username"""

# Реферальная ссылка теперь в балансе

STATS_TEXT = """📊 <b>Статистика PR VANISH</b>

👥 <b>Пользователей за сегодня:</b> {users_today}
👥 <b>Пользователей за весь период:</b> {total_users}
🏘️ <b>Групп с нашим ботом:</b> {total_groups}

<i>Хотите увеличить свою аудиторию? Закажите рекламу прямо сейчас!</i>
📢 <b>Попробуйте наш пиар — и увидите результат!</b>"""

HELP_TEXT = """❓ Помощь

<b>Личные команды:</b>
• 💰 Баланс - посмотреть баланс и реферальную ссылку
• 📢 Заказать пиар - заказать рекламу
• 👥 Мои каналы - управление каналами
• 📊 Статистика - общая статистика
• ❓ Помощь - эта справка

<b>Групповые команды (только для администраторов):</b>
• /setup @channel время - привязать канал с обязательной подпиской к текущей группе
  Пример: /setup @mychannel 1h
• /status - показать статус привязанных каналов
• /unsetup - отвязать все каналы
• /unsetup @username - отвязать конкретный канал
  Пример: /unsetup @mychannel
• /help - показать эту справку (только для админов в группах)

<b>Команды для владельцев групп (в личных сообщениях):</b>
• /setup @group время - привязать @likkerrochat к группе
  Пример: /setup t.me/mygroup 1d

<i>Время: 1h, 6h, 12h, 1d, 3d, 7d</i>"""

ADMIN_TEXT = """Админ-панель

Команды:
 /ban (@username) 1d - бан пользователя в боте
 /stats - полная статистика бота
 /give (@username) (сумма) - выдать баланс
 /addadmin (user_id) - добавить админа
 /rassil - начать рассылку (бот запросит сообщение)
 /stoprassil - остановить рассылку
 /removeall - удалить все активные подписки у пользователей

Отправьте команду."""

admin_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[]
)

# Глобальный кеш для клавиатур и данных
keyboard_cache = {}
data_cache = None
data_cache_time = 0
CACHE_TTL = 30  # 30 секунд

# Функция для создания кешированных клавиатур
def get_cached_keyboard(key, keyboard_func):
    if key not in keyboard_cache:
        keyboard_cache[key] = keyboard_func()
    return keyboard_cache[key]

# Оптимизированная загрузка данных с кешированием
def load_data():
    global data_cache, data_cache_time
    current_time = asyncio.get_event_loop().time()

    if data_cache is None or (current_time - data_cache_time) > CACHE_TTL:
        try:
            with open('data.json', 'r', encoding='utf-8') as f:
                data_cache = json.load(f)
                data_cache_time = current_time
        except FileNotFoundError:
            # Создать базовую структуру если файл не существует
            data_cache = {
                'users': {},
                'groups': {},
                'admins': [],
                'stats': {'total_users': 0, 'total_channels': 0, 'total_balance': 0, 'users_today': 0, 'last_reset_date': date.today().isoformat()}
            }
            save_data(data_cache)

        # Сброс users_today ежедневно
        today = date.today().isoformat()
        if 'last_reset_date' not in data_cache['stats'] or data_cache['stats']['last_reset_date'] != today:
            data_cache['stats']['users_today'] = 0
            data_cache['stats']['last_reset_date'] = today
            # Сохранить изменения
            with open('data.json', 'w', encoding='utf-8') as f:
                json.dump(data_cache, f, ensure_ascii=False, indent=4)

    return data_cache

# Оптимизированная функция сохранения данных
def save_data(data):
    global data_cache, data_cache_time
    try:
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        # Обновить кеш
        data_cache = data
        data_cache_time = asyncio.get_event_loop().time()
    except Exception as e:
        logging.error(f"Error saving data: {e}")

# Функция для отправки/редактирования сообщения с фото
async def send_or_edit_message(chat_id, message_id, text, photo_url=config.PHOTO_URL, reply_markup=None, parse_mode=None, force_edit=False):
    try:
        if message_id and not force_edit:
            # Попробовать отредактировать существующее сообщение
            try:
                await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=text, parse_mode=parse_mode)
                if reply_markup:
                    await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=reply_markup)
                return message_id
            except Exception as e:
                # Если редактирование не удалось, отправить новое
                logging.warning(f"Failed to edit message {message_id}: {e}")
                pass

        # Отправить новое сообщение
        try:
            # Попробовать отправить по URL
            msg = await bot.send_photo(chat_id=chat_id, photo=photo_url, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e1:
            try:
                # Если не удалось, скачать и отправить как файл
                response = requests.get(photo_url)
                if response.status_code == 200:
                    from aiogram.types import BufferedInputFile
                    photo_file = BufferedInputFile(response.content, filename="photo.jpg")
                    msg = await bot.send_photo(chat_id=chat_id, photo=photo_file, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
                else:
                    # Без фото
                    msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
            except Exception as e2:
                logging.error(f"Failed to send message: {e1}, {e2}")
                # Последняя попытка - отправить без фото
                msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

        return msg.message_id
    except Exception as e:
        logging.error(f"Error in send_or_edit_message: {e}")
        # Fallback - отправить простое текстовое сообщение
        msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return msg.message_id

# Функция для начисления баланса с рефералами (оптимизированная)
def add_balance(user_id, amount):
    data = load_data()
    if user_id not in data['users']:
        return

    old_balance = data['users'][user_id]['balance']
    data['users'][user_id]['balance'] = old_balance + amount
    data['stats']['total_balance'] += amount

    # Реферал
    referrer = data['users'][user_id].get('referrer')
    if referrer and referrer in data['users']:
        ref_bonus = amount * 0.2  # 20% от начисленной суммы
        if ref_bonus > 0:
            data['users'][referrer]['balance'] += ref_bonus
            data['users'][referrer]['earned'] += ref_bonus
            data['users'][referrer]['referrals'] += 1
            data['stats']['total_balance'] += ref_bonus

    save_data(data)

# Хендлер для /start
@dp.message(Command("start"))
async def start_command(message: Message):
    data = load_data()
    user_id = message.from_user.id
    today = date.today().isoformat()
    if str(user_id) not in data['users']:
        ref_code = generate_ref_code()
        data['users'][str(user_id)] = {
            'balance': 0,
            'referrer': None,
            'channels': [],
            'message_id': None,
            'referrals': 0,
            'earned': 0,
            'ref_code': ref_code,
            'username': message.from_user.username.lower() if message.from_user.username else None,
            'last_seen_date': today
        }
        data['stats']['total_users'] += 1
        data['stats']['users_today'] += 1
        save_data(data)
    else:
        # Добавить ref_code если отсутствует
        if 'ref_code' not in data['users'][str(user_id)]:
            data['users'][str(user_id)]['ref_code'] = generate_ref_code()
        # Обновить username
        data['users'][str(user_id)]['username'] = message.from_user.username.lower() if message.from_user.username else None
        # Проверить last_seen_date
        if data['users'][str(user_id)].get('last_seen_date') != today:
            data['stats']['users_today'] += 1
            data['users'][str(user_id)]['last_seen_date'] = today
        save_data(data)
    
    # Обработка реферала
    args = message.text.split()
    if len(args) > 1:
        ref_code = args[1]
        referrer_id = None
        for uid, info in data['users'].items():
            if info.get('ref_code') == ref_code:
                referrer_id = uid
                break
        if referrer_id and referrer_id != str(user_id):
            data['users'][str(user_id)]['referrer'] = referrer_id
            # Начислить 0.1 VANISH рефереру
            data['users'][referrer_id]['balance'] += 0.1
            data['users'][referrer_id]['earned'] += 0.1
            data['users'][referrer_id]['referrals'] += 1
            data['stats']['total_balance'] += 0.1
            save_data(data)
    
    msg_id = await send_or_edit_message(message.chat.id, None, START_TEXT, reply_markup=main_keyboard, parse_mode="HTML")
    data['users'][str(user_id)]['message_id'] = msg_id
    save_data(data)

# Команда для управления каналами (работает в группах и личных сообщениях)
@dp.message(Command("setup"))
async def setup_command(message: Message):
    args = message.text.split()

    # Проверяем минимальное количество аргументов
    if len(args) < 3:
        await message.reply("❌ Неверный формат команды!\n\n📝 <b>Правильное использование:</b>\n/setup @channel_or_group время\n\n📋 <b>Примеры:</b>\n• /setup @mychannel 1h (в группе - привязать канал к текущей группе)\n• /setup t.me/mygroup 1d (в личных - привязать @likkerrochat к группе)\n\n⏰ <b>Доступное время:</b>\n1h, 6h, 12h, 1d, 3d, 7d", parse_mode="HTML")
        return

    channel_or_group = args[1]
    time_str = args[2]

    # Парсинг времени
    def parse_time(time_str):
        if time_str.lower() == 'never':
            return None  # Бессрочное
        if time_str.endswith('h'):
            try:
                hours = int(time_str[:-1])
                return hours
            except ValueError:
                return False
        elif time_str.endswith('d'):
            try:
                days = int(time_str[:-1])
                return days * 24
            except ValueError:
                return False
        else:
            return False

    hours = parse_time(time_str)
    if hours is False:
        await message.reply("❌ Неверный формат времени!\n\n📝 <b>Примеры:</b>\n• 3h - 3 часа\n• 1d - 1 день\n• 5d - 5 дней\n• never - бессрочное\n\n📋 <b>Пример:</b>\n/setup @mychannel 1d", parse_mode="HTML")
        return

    if message.chat.type in ['group', 'supergroup']:
        # В группе: channel_or_group - канал, привязываем к текущей группе
        channel = channel_or_group

        # Обрабатываем формат канала
        if channel.startswith('t.me/'):
            channel = '@' + channel.replace('t.me/', '')
        elif channel.startswith('https://t.me/') or channel.startswith('http://t.me/'):
            channel = '@' + channel.split('/')[-1]
        elif not channel.startswith('@'):
            channel = '@' + channel

        # Проверяем канал
        try:
            channel_username = channel[1:]  # Убираем @
            channel_info = await bot.get_chat(f"@{channel_username}")

            # Проверяем права пользователя в канале
            user_member = await bot.get_chat_member(channel_info.id, message.from_user.id)
            if not user_member.status in ['administrator', 'creator']:
                await message.reply(f"❌ <b>Недостаточно прав!</b>\n\n🚫 Вы должны быть администратором или создателем канала {channel} для управления им.\n\n💡 <b>Получите права администратора</b> в канале.", parse_mode="HTML")
                return

            # Проверяем, что бот добавлен в канал как администратор
            try:
                bot_member = await bot.get_chat_member(channel_info.id, bot.id)
                if bot_member.status not in ['administrator', 'creator']:
                    await message.reply(f"❌ <b>Бот не является администратором канала!</b>\n\n🤖 Бот должен быть добавлен в канал {channel} как администратор для работы с обязательной подпиской.\n\n💡 <b>Добавьте бота в канал как администратора</b>.", parse_mode="HTML")
                    return
            except Exception as e:
                await message.reply(f"❌ <b>Бот не имеет доступа к каналу!</b>\n\n🚫 Добавьте бота в канал {channel} как администратора.\n\n💡 <b>Убедитесь что канал существует и бот добавлен</b>.", parse_mode="HTML")
                return

        except Exception as e:
            await message.reply(f"❌ <b>Ошибка доступа к каналу!</b>\n\n🚫 Канал {channel} не найден или у вас нет доступа к нему.\n\n💡 <b>Убедитесь что:</b>\n• Канал существует\n• Вы являетесь администратором канала\n• Бот добавлен в канал как администратор", parse_mode="HTML")
            return

        # Группа - текущая
        target_group_id = str(message.chat.id)

        # Проверяем, что бот является админом группы
        bot_member = await bot.get_chat_member(message.chat.id, bot.id)
        if not bot_member.status in ['administrator', 'creator']:
            await message.reply("❌ <b>Бот не является администратором группы!</b>\n\n🤖 Бот должен быть администратором группы для работы с обязательной подпиской.\n\n💡 <b>Добавьте бота в администраторы группы</b> с правом удаления сообщений.", parse_mode="HTML")
            return

        if hours is None:
            success_message = f"✅ Канал {channel} привязан к группе с обязательной подпиской навсегда."
        else:
            success_message = f"✅ Канал {channel} привязан к группе с обязательной подпиской на {time_str}."

    else:
        # В личных: channel_or_group - группа, привязываем @likkerrochat к этой группе
        group = channel_or_group

        # Обрабатываем формат группы
        if group.startswith('t.me/'):
            group = '@' + group.replace('t.me/', '')
        elif group.startswith('https://t.me/') or group.startswith('http://t.me/'):
            group = '@' + group.split('/')[-1]
        elif not group.startswith('@'):
            group = '@' + group

        # Проверяем группу
        try:
            group_username = group[1:]  # Убираем @
            group_info = await bot.get_chat(f"@{group_username}")

            # Проверяем, что это группа или супергруппа
            if group_info.type not in ['group', 'supergroup']:
                await message.reply(f"❌ <b>{group} не является группой!</b>\n\n🚫 Укажите группу, а не канал или бота.\n\n💡 <b>Используйте:</b>\n• @groupname\n• t.me/groupname", parse_mode="HTML")
                return

            # Проверяем права пользователя в группе
            user_member = await bot.get_chat_member(group_info.id, message.from_user.id)
            if user_member.status not in ['administrator', 'creator']:
                await message.reply(f"❌ <b>Недостаточно прав!</b>\n\n🚫 Вы должны быть администратором или создателем группы {group} для настройки обязательной подписки.\n\n💡 <b>Получите права администратора</b> в группе.", parse_mode="HTML")
                return

            # Проверяем, что бот является админом группы
            bot_member = await bot.get_chat_member(group_info.id, bot.id)
            if not bot_member.status in ['administrator', 'creator']:
                await message.reply(f"❌ <b>Бот не является администратором группы!</b>\n\n🤖 Бот должен быть администратором группы {group} для работы с обязательной подпиской.\n\n💡 <b>Добавьте бота в администраторы группы</b> с правом удаления сообщений.", parse_mode="HTML")
                return

        except Exception as e:
            await message.reply(f"❌ <b>Ошибка доступа к группе!</b>\n\n🚫 Группа {group} не найдена или у вас нет доступа к ней.\n\n💡 <b>Убедитесь что:</b>\n• Группа существует\n• Вы являетесь администратором группы\n• Бот добавлен в группу как администратор", parse_mode="HTML")
            return

        # Канал - фиксированный @likkerrochat
        channel = '@likkerrochat'

        # Проверяем канал @likkerrochat
        try:
            channel_info = await bot.get_chat(channel)
            bot_member = await bot.get_chat_member(channel_info.id, bot.id)
            if bot_member.status not in ['administrator', 'creator']:
                await message.reply("❌ <b>Бот не является администратором канала @likkerrochat!</b>\n\n🤖 Бот должен быть добавлен в канал @likkerrochat как администратор.", parse_mode="HTML")
                return
        except Exception as e:
            await message.reply("❌ <b>Ошибка доступа к каналу @likkerrochat!</b>\n\n🚫 Канал не найден или бот не имеет доступа.", parse_mode="HTML")
            return

        target_group_id = str(group_info.id)

        if hours is None:
            success_message = f"✅ Канал @likkerrochat привязан к группе {group} с обязательной подпиской навсегда."
        else:
            success_message = f"✅ Канал @likkerrochat привязан к группе {group} с обязательной подпиской на {time_str}."

    # Создаем обязательную подписку
    if hours is None:
        expiry = None
    else:
        expiry = datetime.now() + timedelta(hours=hours)

    data = load_data()
    if target_group_id not in data['groups']:
        data['groups'][target_group_id] = {'channels': {}, 'bots': {}}

    data['groups'][target_group_id]['channels'][channel] = {'expiry': expiry.isoformat() if expiry else None, 'people': 0}

    # Автоматически добавить @likkerrochat если это группа
    if message.chat.type in ['group', 'supergroup']:
        if '@likkerrochat' not in data['groups'][target_group_id]['channels']:
            data['groups'][target_group_id]['channels']['@likkerrochat'] = {'expiry': None, 'people': 0}

    save_data(data)
    await message.reply(success_message, parse_mode="HTML")

@dp.message(Command("status"))
async def status_command(message: Message):
    # Админы бота могут использовать без проверки прав
    if message.from_user.id == config.ADMIN_ID:
        pass  # Пропустить проверку
    # Проверяем права пользователя в группе
    elif message.chat.type in ['group', 'supergroup']:
        try:
            user_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
            if user_member.status not in ['administrator', 'creator']:
                await message.reply("❌ <b>Недостаточно прав!</b>\n\n🚫 Эта команда доступна только администраторам и создателю группы.\n\n💡 <b>Обратитесь к администратору группы</b> для просмотра статуса.", parse_mode="HTML")
                return
        except Exception as e:
            await message.reply("❌ <b>Ошибка проверки прав!</b>\n\nНе удалось проверить ваши права в группе.", parse_mode="HTML")
            return

    data = load_data()

    # Определяем контекст
    if message.chat.type in ['group', 'supergroup']:
        target_group_id = str(message.chat.id)
        context = "группе"

        # Групповой контекст
        if target_group_id not in data['groups'] or not data['groups'][target_group_id]['channels']:
            await message.reply("❌ В этой группе нет привязанных каналов.\n\n💡 <b>Используйте команду:</b>\n/setup @username время\n\n📝 <b>Пример:</b>\n/setup @mychannel 1d", parse_mode="HTML")
            return

        status_text = "📊 <b>Статус каналов в группе:</b>\n\n"
        for channel, info in data['groups'][target_group_id]['channels'].items():
            if info['expiry']:
                expiry = datetime.fromisoformat(info['expiry'])
                expiry_str = expiry.strftime('%Y-%m-%d %H:%M')
            else:
                expiry_str = "навсегда"
            status_text += f"📌 {channel}: истекает {expiry_str}, людей: {info['people']}\n"
        await message.reply(status_text, parse_mode="HTML")
    else:
        # Личные сообщения - показать все привязки пользователя
        user_channels = []
        for gid, group_info in data['groups'].items():
            for channel in group_info['channels'].keys():
                if channel.startswith('@'):
                    try:
                        channel_info = await bot.get_chat(channel)
                        member = await bot.get_chat_member(channel_info.id, message.from_user.id)
                        if member.status in ['administrator', 'creator']:
                            user_channels.extend([(channel, info) for channel, info in group_info['channels'].items() if channel == channel])
                    except:
                        continue

        if not user_channels:
            await message.reply("❌ У вас нет каналов с активными привязками.\n\n💡 <b>Используйте команду:</b>\n/setup @username время", parse_mode="HTML")
            return

        status_text = "📊 <b>Статус ваших каналов:</b>\n\n"
        for channel, info in user_channels:
            expiry = datetime.fromisoformat(info['expiry'])
            status_text += f"📌 {channel}: истекает {expiry.strftime('%Y-%m-%d %H:%M')}, людей: {info['people']}\n"
        await message.reply(status_text, parse_mode="HTML")

@dp.message(Command("ban"))
async def ban_command(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("❌ Неверный формат команды!\n\n📝 <b>Правильное использование:</b>\n/ban @username время\n\n📋 <b>Примеры:</b>\n• /ban @username 1d\n• /ban @baduser 3d\n\n⏰ <b>Доступное время:</b>\n1d, 3d, 7d", parse_mode="HTML")
        return
    target = args[1]
    duration = args[2]
    try:
        data = load_data()
        target_user_id = None
        if target.startswith('@'):
            username = target[1:].lower()
            for uid, info in data['users'].items():
                if info.get('username') == username:
                    target_user_id = uid
                    break
        else:
            target_user_id = target
        if target_user_id and target_user_id in data['users']:
            ban_until = datetime.now() + timedelta(days=1)  # 1d
            data['users'][target_user_id]['banned_until'] = ban_until.isoformat()
            save_data(data)
            await message.reply(f"Пользователь {target} забанен на 1 день.")
        else:
            await message.reply("Пользователь не найден.")
    except:
        await message.reply("Неверный формат.")

@dp.message(Command("stats"))
async def stats_command(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    data = load_data()
    stats = data['stats']
    text = f"""Полная статистика бота:
Всего пользователей: {stats['total_users']}
Пользователей сегодня: {stats.get('users_today', 0)}
Всего каналов: {stats['total_channels']}
Оборот баллов: {stats['total_balance']}"""
    await message.reply(text)

@dp.message(Command("addadmin"))
async def addadmin_command(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    args = message.text.split()
    if len(args) != 2:
        await message.reply("❌ Неверный формат команды!\n\n📝 <b>Правильное использование:</b>\n/addadmin user_id\n\n📋 <b>Примеры:</b>\n• /addadmin 123456789\n• /addadmin 987654321\n\n💡 <b>user_id</b> - числовой ID пользователя в Telegram", parse_mode="HTML")
        return
    try:
        admin_id = int(args[1])
        data = load_data()
        if admin_id not in data['admins']:
            data['admins'].append(admin_id)
            save_data(data)
            await message.reply(f"✅ Админ {admin_id} добавлен")
        else:
            await message.reply("Этот пользователь уже админ")
    except:
        await message.reply("Неверный user_id")

@dp.message(Command("give"))
async def give_command(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("❌ Неверный формат команды!\n\n📝 <b>Правильное использование:</b>\n/give @username сумма\n\n📋 <b>Примеры:</b>\n• /give @user 100\n• /give @testuser 500\n\n💰 <b>Сумма в VANISH</b>", parse_mode="HTML")
        return
    target = args[1]
    amount = args[2]
    try:
        amount = int(amount)
        data = load_data()
        target_user_id = None
        if target.startswith('@'):
            username = target[1:].lower()
            logging.info(f"Searching for username: {username}")
            for uid, info in data['users'].items():
                logging.info(f"User {uid}: {info.get('username')}")
                if info.get('username') == username:
                    target_user_id = uid
                    break
        else:
            target_user_id = target
        if target_user_id and target_user_id in data['users']:
            data['users'][target_user_id]['balance'] += amount
            data['stats']['total_balance'] += amount
            logging.info(f"Updated balance for {target_user_id} to {data['users'][target_user_id]['balance']}")
            save_data(data)
            logging.info("Data saved after give command")
            await message.reply(f"Выдано {amount} VANISH пользователю {target}.")
        else:
            await message.reply("Пользователь не найден.")
    except:
        await message.reply("Неверный формат.")

@dp.message(Command("removeall"))
async def removeall_command(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    data = load_data()
    count = 0
    for uid in data['users']:
        if 'active_ads' in data['users'][uid]:
            count += len(data['users'][uid]['active_ads'])
            data['users'][uid]['active_ads'] = []
    save_data(data)
    await message.reply(f"✅ Удалено {count} активных подписок у всех пользователей.")

@dp.message(Command("rassil"))
async def rassil_command(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    data = load_data()
    data['waiting_for_broadcast'] = True
    save_data(data)
    await message.reply("📝 Отправьте сообщение для рассылки.", parse_mode="HTML")

@dp.message(Command("stoprassil"))
async def stoprassil_command(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    data = load_data()
    if 'broadcast_message' in data:
        del data['broadcast_message']
        save_data(data)
        await message.reply("✅ Рассылка остановлена.", parse_mode="HTML")
    else:
        await message.reply("❌ Рассылка не активна.", parse_mode="HTML")

@dp.message(Command("unsetup"))
async def unsetup_command(message: Message):
    # Админы бота могут использовать без проверки прав
    if message.from_user.id == config.ADMIN_ID:
        pass  # Пропустить проверку
    # Проверяем права пользователя в группе
    elif message.chat.type in ['group', 'supergroup']:
        try:
            user_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
            logging.info(f"User member object: {user_member}")
            logging.info(f"User {message.from_user.id} status in group {message.chat.id}: {user_member.status}")
            if user_member.status not in ['administrator', 'creator']:
                await message.reply("❌ <b>Недостаточно прав!</b>\n\n🚫 Эта команда доступна только администраторам и создателю группы.\n\n💡 <b>Обратитесь к администратору группы</b> для отвязки каналов.", parse_mode="HTML")
                return

            # Проверяем, что бот является админом группы
            bot_member = await bot.get_chat_member(message.chat.id, bot.id)
            if not bot_member.status in ['administrator', 'creator']:
                await message.reply("❌ <b>Бот не является администратором группы!</b>\n\n🤖 Бот должен быть администратором группы для работы с обязательной подпиской.\n\n💡 <b>Добавьте бота в администраторы группы</b> с правом удаления сообщений.", parse_mode="HTML")
                return
        except Exception as e:
            logging.error(f"Error checking rights: {e}")
            await message.reply("❌ <b>Ошибка проверки прав!</b>\n\nНе удалось проверить ваши права в группе.", parse_mode="HTML")
            return

    args = message.text.split()
    data = load_data()

    # Определяем группу для отвязки
    if message.chat.type in ['group', 'supergroup']:
        target_group_id = str(message.chat.id)
        group_context = "группе"
    else:
        # Личные сообщения - пользователь должен быть владельцем канала
        if len(args) < 2:
            await message.reply("❌ Укажите канал для отвязки!\n\n📝 <b>Использование:</b>\n/unsetup @username\n\n📋 <b>Пример:</b>\n/unsetup @mychannel", parse_mode="HTML")
            return

        channel = args[1]
        if not channel.startswith('@'):
            await message.reply("❌ Укажите канал в формате @username")
            return

        try:
            channel_username = channel[1:]
            channel_info = await bot.get_chat(f"@{channel_username}")
            user_member = await bot.get_chat_member(channel_info.id, message.from_user.id)
            if not user_member.status in ['administrator', 'creator']:
                await message.reply(f"❌ <b>Недостаточно прав!</b>\n\n🚫 Вы должны быть администратором или создателем канала {channel}.\n\n💡 <b>Получите права администратора</b> в канале.", parse_mode="HTML")
                return

            target_group_id = str(channel_info.id)
            group_context = "канале"
        except Exception as e:
            await message.reply(f"❌ <b>Ошибка доступа к каналу!</b>\n\n🚫 Канал {channel} не найден или у вас нет доступа к нему.", parse_mode="HTML")
            return

    if target_group_id not in data['groups']:
        await message.reply(f"❌ Нет активных привязок для этого {group_context}.")
        return

    if len(args) == 1:
        # Отвязать все
        channels_count = len(data['groups'][target_group_id]['channels'])
        data['groups'][target_group_id]['channels'] = {}
        save_data(data)
        await message.reply(f"✅ Все каналы отвязаны от этого {group_context}!\n\n📊 <b>Отвязано каналов:</b> {channels_count}", parse_mode="HTML")
    else:
        channel = args[1]
        if channel in data['groups'][target_group_id]['channels']:
            del data['groups'][target_group_id]['channels'][channel]
            save_data(data)
            await message.reply(f"✅ Канал {channel} успешно отвязан от этого {group_context}!")
        else:
            await message.reply(f"❌ Канал {channel} не найден в активных привязках этого {group_context}.\n\n💡 <b>Проверьте правильность написания:</b>\n• Используйте @username\n• Без лишних пробелов", parse_mode="HTML")
        
        # Команда для просмотра статуса канала (для владельцев)
        @dp.message(Command("channel_status"))
        async def channel_status_command(message: Message):
            if message.chat.type not in ['private']:
                return
        
            args = message.text.split()
            if len(args) < 2:
                await message.reply("❌ Укажите канал для проверки!\n\n📝 <b>Использование:</b>\n/channel_status @username\n\n📋 <b>Пример:</b>\n/channel_status @mychannel", parse_mode="HTML")
                return
        
            channel = args[1]
            if not channel.startswith('@'):
                await message.reply("❌ Укажите канал в формате @username")
                return
        
            try:
                channel_username = channel[1:]
                channel_info = await bot.get_chat(f"@{channel_username}")
        
                # Проверяем права пользователя в канале
                user_member = await bot.get_chat_member(channel_info.id, message.from_user.id)
                if not user_member.status in ['administrator', 'creator']:
                    await message.reply(f"❌ Вы должны быть администратором или создателем канала {channel}.")
                    return
        
                data = load_data()
                channel_id = str(channel_info.id)
        
                if channel_id not in data['groups'] or not data['groups'][channel_id]['channels']:
                    await message.reply(f"📊 <b>Статус канала {channel}:</b>\n\n❌ Нет активных привязок к группам.", parse_mode="HTML")
                    return
        
                status_text = f"📊 <b>Статус канала {channel}:</b>\n\n"
                for group_channel, info in data['groups'][channel_id]['channels'].items():
                    if info['expiry']:
                        expiry = datetime.fromisoformat(info['expiry'])
                        expiry_str = expiry.strftime('%Y-%m-%d %H:%M')
                    else:
                        expiry_str = "навсегда"
                    status_text += f"📌 Привязан: истекает {expiry_str}, людей: {info['people']}\n"
        
                await message.reply(status_text, parse_mode="HTML")
        
            except Exception as e:
                await message.reply(f"❌ Ошибка доступа к каналу {channel}.\n\n💡 <b>Убедитесь что:</b>\n• Канал существует\n• Вы являетесь администратором канала", parse_mode="HTML")
        
        # Команда для отвязки канала от всех групп (для владельцев)
        @dp.message(Command("unsetup_channel"))
        async def unsetup_channel_command(message: Message):
            if message.chat.type not in ['private']:
                return
        
            args = message.text.split()
            if len(args) < 2:
                await message.reply("❌ Укажите канал для отвязки!\n\n📝 <b>Использование:</b>\n/unsetup_channel @username\n\n📋 <b>Пример:</b>\n/unsetup_channel @mychannel", parse_mode="HTML")
                return
        
            channel = args[1]
            if not channel.startswith('@'):
                await message.reply("❌ Укажите канал в формате @username")
                return
        
            try:
                channel_username = channel[1:]
                channel_info = await bot.get_chat(f"@{channel_username}")
        
                # Проверяем права пользователя в канале
                user_member = await bot.get_chat_member(channel_info.id, message.from_user.id)
                if not user_member.status in ['administrator', 'creator']:
                    await message.reply(f"❌ Вы должны быть администратором или создателем канала {channel}.")
                    return
        
                data = load_data()
                channel_id = str(channel_info.id)
        
                if channel_id not in data['groups'] or not data['groups'][channel_id]['channels']:
                    await message.reply(f"❌ Канал {channel} не имеет активных привязок.")
                    return
        
                channels_count = len(data['groups'][channel_id]['channels'])
                data['groups'][channel_id]['channels'] = {}
                save_data(data)
        
                await message.reply(f"✅ Канал {channel} успешно отвязан от всех групп!\n\n📊 <b>Отвязано от групп:</b> {channels_count}", parse_mode="HTML")
        
            except Exception as e:
                await message.reply(f"❌ Ошибка доступа к каналу {channel}.")

# Хендлер для callback
@dp.callback_query()
async def handle_callback(callback: CallbackQuery):
    data = load_data()
    user_id = str(callback.from_user.id)
    if user_id not in data['users']:
        return

    # Проверить бан
    banned_until = data['users'][user_id].get('banned_until')
    if banned_until and datetime.fromisoformat(banned_until) > datetime.now():
        return

    msg_id = data['users'][user_id]['message_id']
    cb_data = callback.data

    if cb_data == "back":
        await send_or_edit_message(callback.message.chat.id, msg_id, START_TEXT, reply_markup=main_keyboard, parse_mode="HTML")
    elif cb_data == "balance":
        balance = data['users'][user_id]['balance']
        logging.info(f"Showing balance for {user_id}: {balance}")
        ref_code = data['users'][user_id]['ref_code']
        bot_username = (await bot.get_me()).username
        await send_or_edit_message(callback.message.chat.id, msg_id, BALANCE_TEXT.format(balance=balance, bot_username=bot_username, ref_code=ref_code), reply_markup=back_keyboard, parse_mode="HTML")
        data['users'][user_id]['current_screen'] = 'balance'
        save_data(data)
    elif cb_data == "pr":
        balance = data['users'][user_id]['balance']
        text = f"""<b>📢 Что вы хотите рекламировать?</b>

💳 <b>Баланс:</b> {balance} VANISH

🚀 <i>Выберите тип рекламы и увеличьте свою аудиторию!</i>"""
        await send_or_edit_message(callback.message.chat.id, msg_id, text, reply_markup=pr_keyboard, parse_mode="HTML")
        data['users'][user_id]['current_screen'] = 'pr'
        save_data(data)
    elif cb_data in ["pr_channel", "pr_group", "pr_post", "pr_bot"]:
        type_map = {
            "pr_channel": ("channel", "КАНАЛ", "7$", "15$", "50$", "обязательная подписка на ваш КАНАЛ"),
            "pr_group": ("group", "ГРУППУ", "7$", "15$", "50$", "обязательная подписка на вашу ГРУППУ"),
            "pr_post": ("post", "ПОСТ", "8$", "12$", "35$", "обязательная реакция на ваш ПОСТ"),
            "pr_bot": ("bot", "БОТ", "10$", "20$", "70$", "обязательная подписка на ваш БОТ \nУстанавливается проверка на /start")
        }

        type_, item_upper, price_1d, price_1w, price_1m, description = type_map[cb_data]

        text = f"""<b>🎉 Отличный выбор!</b>

<b>💰 Прайсы:</b>
• 1 День - {price_1d}
• 1 Неделя - {price_1w}
• 1 Месяц - {price_1m}

<i>🔍 Как работает? Все у кого установлен наш бот, в группах/каналах будет установлена {description}</i>

<b>📝 После оплаты вам нужно будет ввести:</b>
• Для канала: <code>@username</code> или <code>https://t.me/username</code>
• Для группы: <code>@groupname</code> или <code>https://t.me/groupname</code>
• Для бота: <code>@botname</code> или <code>https://t.me/botname</code>
• Для поста: <code>https://t.me/channel/123</code>"""

        await send_or_edit_message(callback.message.chat.id, msg_id, text, reply_markup=channel_keyboard, parse_mode="HTML")
        data['users'][user_id]['current_screen'] = 'channel_pr'
        data['users'][user_id]['selected_type'] = type_
        save_data(data)
    elif cb_data in ["channel_1d", "channel_1w", "channel_1m"]:
        period = cb_data.split('_')[1]
        if 'selected_type' not in data['users'][user_id]:
            try:
                await callback.answer("Сначала выберите тип рекламы.")
            except:
                pass
            return
        type_ = data['users'][user_id]['selected_type']
        data['users'][user_id]['selected_period'] = period
        p = prices[type_][period]
        type_text = {'channel': 'канала', 'group': 'группы', 'bot': 'бота', 'post': 'поста'}[type_]
        text = f"""💳 Создан чек на оплату

📋 Детали платежа:
• Сумма: {p['usd']} USTD
• Сумма VANISH: {p['vanish']}
• Срок действия оплаты чека: 3 минуты
• Сервис: реклама {type_text} на {p['period']}
⏰ Ожидание оплаты..."""
        await send_or_edit_message(callback.message.chat.id, msg_id, text, reply_markup=payment_keyboard)
        data['users'][user_id]['current_screen'] = 'payment'
        save_data(data)
    elif cb_data == "pay_crypto":
        try:
            try:
                await callback.answer()
            except:
                pass
        except Exception as e:
            # Игнорируем ошибки старых callback'ов
            logging.info(f"Callback answer error (old query): {e}")
        if 'selected_period' not in data['users'][user_id] or 'selected_type' not in data['users'][user_id]:
            try:
                await callback.answer("Сначала выберите период.")
            except:
                pass
            return
        period = data['users'][user_id]['selected_period']
        type_ = data['users'][user_id]['selected_type']
        p = prices[type_][period]
        type_text = {'channel': 'канала', 'group': 'группы', 'bot': 'бота', 'post': 'поста'}[type_]
        # Сначала показать "Создание чека..."
        temp_text = f"""💳 Создание чека на оплату...

📋 Детали платежа:
• Сумма: {p['usd']} USTD
• Сумма VANISH: {p['vanish']}
• Срок действия оплаты чека: 3 минуты
• Сервис: реклама {type_text} на {p['period']}
⏰ Пожалуйста, подождите..."""
        await send_or_edit_message(callback.message.chat.id, msg_id, temp_text, reply_markup=None)
        # Test API
        test_url = "https://pay.crypt.bot/api/getMe"
        test_response = requests.get(test_url, headers={"Crypto-Pay-API-Token": config.CRYPTOBOT_TOKEN})
        logging.info(f"getMe response: {test_response.status_code} {test_response.text}")
        url = "https://pay.crypt.bot/api/createInvoice"
        headers = {"Crypto-Pay-API-Token": config.CRYPTOBOT_TOKEN, "Content-Type": "application/json"}
        payload = {
            "asset": "USDT",
            "amount": str(p['usd']),
            "description": f"Реклама {type_text} на {p['period']}",
            "hidden_message": "Спасибо за оплату!",
            "paid_btn_name": "openBot",
            "paid_btn_url": f"https://t.me/{(await bot.get_me()).username}"
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        logging.info(f"Payload: {payload}")
        logging.info(f"Response status: {response.status_code}")
        logging.info(f"Response: {response.text}")
        if response.status_code == 200:
            res = response.json()
            if res['ok']:
                invoice_id = res['result']['invoice_id']
                pay_url = res['result']['bot_invoice_url']  # Использовать bot_invoice_url вместо pay_url
                data['users'][user_id]['invoice_id'] = invoice_id
                payment_keyboard_with_url = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔗 Оплатить", url=pay_url), InlineKeyboardButton(text="🔗 Оплатить с VANISH", callback_data="pay_vanish")],
                        [InlineKeyboardButton(text="↩️ Назад", callback_data="back")]
                    ]
                )
                # Пересоздать text
                text = f"""💳 Создан чек на оплату

📋 Детали платежа:
• Сумма: {p['usd']} USTD
• Сумма VANISH: {p['vanish']}
• Срок действия оплаты чека: 3 минуты
• Сервис: реклама {type_text} на {p['period']}
⏰ Ожидание оплаты...
Обновлено: {int(asyncio.get_event_loop().time())}"""
                await send_or_edit_message(callback.message.chat.id, msg_id, text, reply_markup=payment_keyboard_with_url)
                save_data(data)
                # Запустить автоматическую проверку оплаты
                asyncio.create_task(check_payment(int(user_id), invoice_id, period, type_))
            else:
                try:
                    await callback.answer(f"Ошибка: {res.get('error', 'Неизвестная ошибка')}")
                except:
                    pass
        else:
            try:
                await callback.answer(f"Ошибка API: {response.status_code}")
            except:
                pass
    elif cb_data == "pay_vanish":
        if 'selected_period' not in data['users'][user_id] or 'selected_type' not in data['users'][user_id]:
            await callback.answer("Сначала выберите период.")
            return
        period = data['users'][user_id]['selected_period']
        type_ = data['users'][user_id]['selected_type']
        p = prices[type_][period]

        # Проверяем баланс
        if data['users'][user_id]['balance'] < p['vanish']:
            try:
                await callback.answer(f"❌ Недостаточно VANISH! Нужно: {p['vanish']}, У вас: {data['users'][user_id]['balance']}")
            except:
                pass
            return

        # Списываем средства
        data['users'][user_id]['balance'] -= p['vanish']
        data['stats']['total_balance'] -= p['vanish']

        # Определяем тип контента и примеры
        item_text = {'channel': 'канал', 'group': 'группу', 'bot': 'бота', 'post': 'пост'}[type_]
        examples = {
            'post': ("https://t.me/channel/123", "http://t.me/channel/123"),
            'bot': ("@myrentbot", "@myrentbot или https://t.me/myrentbot"),
            'channel': ("@mychannel", "@mychannel или https://t.me/mychannel"),
            'group': ("@mygroup", "@mygroup или https://t.me/mygroup")
        }
        example, important_example = examples.get(type_, ("@example", "@example"))

        text = f"""✅ Оплата VANISH подтверждена!

💰 Списано: {p['vanish']} VANISH
💳 Остаток: {data['users'][user_id]['balance']} VANISH

🎉 Скиньте ссылку на ваш {html.escape(item_text)}

📝 <b>Примеры правильного ввода:</b>
• {html.escape(example)}
• {html.escape(important_example)}

⚠️ <b>Поддерживаемые форматы:</b>
• @username
• https://t.me/username
• http://t.me/username
• t.me/username

<i>Бот автоматически исправит формат, если он введен правильно!</i>"""

        await send_or_edit_message(callback.message.chat.id, msg_id, text)
        data['users'][user_id]['current_screen'] = 'enter_channel'
        data['users'][user_id]['ad_period'] = period
        data['users'][user_id]['ad_type'] = type_
        save_data(data)
    elif cb_data == "edit_channel":
        item_text = {'channel': 'канал', 'group': 'группу', 'bot': 'бота', 'post': 'пост'}[type_]

        # Улучшенные примеры для разных типов
        examples = {
            'post': ("https://t.me/channel/123", "http://t.me/channel/123"),
            'bot': ("@myrentbot", "@myrentbot или https://t.me/myrentbot"),
            'channel': ("@mychannel", "@mychannel или https://t.me/mychannel"),
            'group': ("@mygroup", "@mygroup или https://t.me/mygroup")
        }
        example, important_example = examples.get(type_, ("@example", "@example"))

        text = f"""✅ Оплата VANISH подтверждена!

💰 Списано: {p['vanish']} VANISH
💳 Остаток: {data['users'][user_id]['balance']} VANISH

🎉 Скиньте ссылку на ваш {html.escape(item_text)}

📝 <b>Примеры правильного ввода:</b>
• {html.escape(example)}
• {html.escape(important_example)}

⚠️ <b>Поддерживаемые форматы:</b>
• @username
• https://t.me/username
• http://t.me/username
• t.me/username

<i>Бот автоматически исправит формат, если он введен правильно!</i>"""
        await send_or_edit_message(callback.message.chat.id, msg_id, text)
        # current_screen остается enter_channel
    elif cb_data == "confirm_channel":
        period = data['users'][user_id]['ad_period']
        type_ = data['users'][user_id]['ad_type']
        data = load_data()
        expiry_hours = {'1d': 24, '1w': 168, '1m': 720}
        hours = expiry_hours[period]
        expiry = datetime.now() + timedelta(hours=hours)
        expiry_str = expiry.isoformat() if expiry else None
        if type_ == 'post':
            post = data['users'][user_id]['entered_post']
            post_key = f"{post['chat_id']}_{post['message_id']}"
            for group_id in data['groups']:
                data['groups'][group_id].setdefault('posts', {})[post_key] = {'chat_id': post['chat_id'], 'message_id': post['message_id'], 'expiry': expiry_str, 'people': 0}
            data['users'][user_id].setdefault('active_ads', []).append({'post': post, 'type': type_, 'period': period, 'expiry': expiry_str})
            item = f"{post['chat_id']}/{post['message_id']}"
        else:
            channel = data['users'][user_id]['entered_channel']
            for group_id in data['groups']:
                if channel not in data['groups'][group_id]['channels']:
                    data['groups'][group_id]['channels'][channel] = {'expiry': expiry_str, 'people': 0}
            data['users'][user_id].setdefault('active_ads', []).append({'channel': channel, 'type': type_, 'period': period, 'expiry': expiry_str})
            item = channel
        logging.info(f"Added active ad for {user_id}: {item}")
        save_data(data)
        type_name = {'channel': 'канала', 'group': 'группы', 'bot': 'бота', 'post': 'поста'}[type_]
        await send_or_edit_message(callback.message.chat.id, msg_id, f"✅ Реклама {type_name} {item} активирована на {prices[type_][period]['period']}!", reply_markup=back_keyboard)
        data['users'][user_id]['current_screen'] = None
        del data['users'][user_id]['ad_period']
        del data['users'][user_id]['ad_type']
        if type_ == 'post':
            del data['users'][user_id]['entered_post']
        else:
            del data['users'][user_id]['entered_channel']
        save_data(data)
    elif cb_data == "channels":
        channels = data['users'][user_id]['channels']
        text = "👥 Мои каналы\n\nВаши каналы:"
        if not channels:
            text += "\nНет каналов"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for ch in channels:
            keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"Удалить {ch}", callback_data=f"delete_channel:{ch}")])
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="↩️ Назад", callback_data="back")])
        await send_or_edit_message(callback.message.chat.id, msg_id, text, reply_markup=keyboard)
# Рефералка теперь в балансе
    elif cb_data == "stats":
        total_users = data['stats']['total_users']
        users_today = data['stats'].get('users_today', 0)
        total_groups = len(data['groups'])
        await send_or_edit_message(callback.message.chat.id, msg_id, STATS_TEXT.format(total_users=total_users, users_today=users_today, total_groups=total_groups), reply_markup=back_keyboard, parse_mode="HTML")
    elif cb_data == "help":
        await send_or_edit_message(callback.message.chat.id, msg_id, HELP_TEXT, reply_markup=back_keyboard, parse_mode="HTML")
    elif cb_data == "my_subs":
        active_ads = data['users'][user_id].get('active_ads', [])
        # Очистить истекшие
        now = datetime.now()
        original_count = len(active_ads)
        active_ads[:] = [ad for ad in active_ads if not ad.get('expiry') or datetime.fromisoformat(ad['expiry']) > now]

        # Сохранить только если были изменения
        if len(active_ads) != original_count:
            save_data(data)

        if not active_ads:
            text = "У вас нет активных обязательных подписок."
        else:
            text = "Ваши активные обязательные подписки:\n"
            for ad in active_ads:
                if ad.get('expiry'):
                    expiry_dt = datetime.fromisoformat(ad['expiry'])
                    remaining = expiry_dt - now
                    days = remaining.days
                    hours, remainder = divmod(remaining.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    if days > 0:
                        time_str = f"{days} д {hours} ч"
                    else:
                        time_str = f"{hours} ч {minutes} мин"
                else:
                    time_str = "навсегда"
                type_name = {'channel': 'Канал', 'group': 'Группа', 'bot': 'Бот', 'post': 'Пост'}.get(ad.get('type', 'channel'), 'Канал')
                if 'post' in ad:
                    item = f"{ad['post']['chat_id']}/{ad['post']['message_id']}"
                else:
                    item = ad.get('channel', 'Неизвестно')
                text += f"• {type_name}: {item} - осталось {time_str}\n"
        await send_or_edit_message(callback.message.chat.id, msg_id, text, reply_markup=back_keyboard)
    elif cb_data.startswith("delete_channel:"):
        channel = cb_data.split(":", 1)[1]
        if channel in data['users'][user_id]['channels']:
            data['users'][user_id]['channels'].remove(channel)
            save_data(data)
        # Обновить сообщение
        channels = data['users'][user_id]['channels']
        text = "👥 Мои каналы\n\nВаши каналы:"
        if not channels:
            text += "\nНет каналов"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for ch in channels:
            keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"Удалить {ch}", callback_data=f"delete_channel:{ch}")])
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="↩️ Назад", callback_data="back")])
        await send_or_edit_message(callback.message.chat.id, msg_id, text, reply_markup=keyboard)

    await callback.answer()

# Команда /help для групп и каналов
@dp.message(Command("help"))
async def help_command(message: Message):
    if message.chat.type in ['group', 'supergroup']:
        # Админы бота могут использовать без проверки прав
        if message.from_user.id != config.ADMIN_ID:
            # Проверяем права пользователя в группе
            try:
                user_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
                if user_member.status not in ['administrator', 'creator']:
                    await message.reply("❌ <b>Недостаточно прав!</b>\n\n🚫 Эта команда доступна только администраторам и создателю группы.\n\n💡 <b>Обратитесь к администратору группы</b> для получения справки.", parse_mode="HTML")
                    return
            except Exception as e:
                await message.reply("❌ <b>Ошибка проверки прав!</b>\n\nНе удалось проверить ваши права в группе.", parse_mode="HTML")
                return

        # Показать команды для групп
        help_text = """🤖 <b>Команды для групп:</b>

<b>Для администраторов:</b>
• /setup @username время - привязать канал с обязательной подпиской
• /status - показать статус привязанных каналов
• /unsetup - отвязать все каналы
• /unsetup @username - отвязать конкретный канал

<b>Примеры:</b>
• /setup @mychannel 1d
• /unsetup @mychannel
• /status

<i>Время: любое число + h/d, например 3h, 4d, или never для бессрочного</i>"""
        await message.reply(help_text, parse_mode="HTML")
    elif message.chat.type == 'private':
        # Показать команды для личных сообщений
        await message.reply(HELP_TEXT, reply_markup=back_keyboard, parse_mode="HTML")
    return

# Проверка подписки в группах
@dp.message(lambda message: message.chat.type in ['group', 'supergroup'])
async def check_subscription(message: Message):

    logging.info(f"Checking subscription for user {message.from_user.id} in group {message.chat.id}")
    data = load_data()
    if message.from_user.id in data['admins']:
        return  # Админы не проверяются
    group_id = str(message.chat.id)
    if group_id not in data['groups']:
        data['groups'][group_id] = {'channels': {}, 'bots': {}}

    # Проверить, что бот может удалять сообщения
    bot_member = await bot.get_chat_member(message.chat.id, bot.id)
    if not bot_member.can_delete_messages:
        # Отправить предупреждение админам
        admins = await bot.get_chat_administrators(message.chat.id)
        for admin in admins:
            if admin.user.id != bot.id:
                try:
                    await bot.send_message(admin.user.id, f"Бот не может удалять сообщения в группе {message.chat.title}. Включите право 'Удалять сообщения' для бота.")
                except:
                    pass
        return  # Бот не может удалять сообщения

    # Автоматически добавить @likkerrochat если бот админ
    if bot_member.status in ['administrator', 'creator'] and '@likkerrochat' not in data['groups'][group_id]['channels']:
        data['groups'][group_id]['channels']['@likkerrochat'] = {'expiry': None, 'people': 0}
        save_data(data)

    # Очистить истекшие каналы
    for channel in list(data['groups'][group_id]['channels'].keys()):
        expiry_str = data['groups'][group_id]['channels'][channel]['expiry']
        if expiry_str and datetime.fromisoformat(expiry_str) < datetime.now():
            del data['groups'][group_id]['channels'][channel]
            logging.info(f"Removed expired channel {channel} from group {group_id}")
    save_data(data)
    if not data['groups'][group_id]['channels']:
        return  # Нет привязанных каналов

    user_id = message.from_user.id
    for channel in data['groups'][group_id]['channels']:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            logging.info(f"User {user_id} status in {channel}: {member.status}")
            if member.status not in ['member', 'administrator', 'creator']:
                # Не подписан, удалить сообщение
                await message.delete()
                # Отправить предупреждение
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="Канал", url=f"https://t.me/{channel[1:]}")]]
                )
                username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
                try:
                    await message.answer(
                        f"Пользователь {username} написал сообщение, но чтобы писать в чат, необходимо подписаться на канал: {channel}",
                        reply_markup=keyboard
                    )
                except Exception as e:
                    logging.error(f"Error sending subscription message: {e}")
                    # Отправить простое сообщение без форматирования
                    try:
                        await message.answer(
                            f"Пользователь {username} написал сообщение, но чтобы писать в чат, необходимо подписаться на канал: {channel}",
                            reply_markup=keyboard
                        )
                    except:
                        pass
                return
        except Exception as e:
            logging.error(f"Error checking subscription for {channel}: {e}")
            # Если канал не найден или бот не имеет доступа (например, приватный канал), пропустить проверку
            continue
    # Проверка подписки на каналы постов (отключена)
    # for post_key, post_info in data['groups'][group_id].get('posts', {}).items():
    #     ...

# Обработка текстовых команд в личных сообщениях
@dp.message()
async def handle_text(message: Message):
    if message.chat.type != 'private':
        return  # Игнорировать групповые сообщения, кроме команд

    data = load_data()
    user_id = str(message.from_user.id)
    if user_id not in data['users']:
        return

    # Обновить username
    data['users'][user_id]['username'] = message.from_user.username.lower() if message.from_user.username else None
    save_data(data)

    # Проверить бан
    banned_until = data['users'][user_id].get('banned_until')
    if banned_until and datetime.fromisoformat(banned_until) > datetime.now():
        return
    
    msg_id = data['users'][user_id]['message_id']
    text = message.text.strip()
    
    if text == "↩️ Назад":
        await send_or_edit_message(message.chat.id, msg_id, START_TEXT, reply_markup=main_keyboard, parse_mode="HTML")
    elif text == "/admin":
        logging.info(f"User {message.from_user.id} sent /admin, username: {message.from_user.username}, is_admin: {message.from_user.id == config.ADMIN_ID or message.from_user.username == 'LIKKERRO'}")
        if message.from_user.id == config.ADMIN_ID or message.from_user.username == "LIKKERRO":
            data['users'][user_id]['current_screen'] = None  # Сброс
            save_data(data)
            await bot.send_message(message.chat.id, ADMIN_TEXT, reply_markup=admin_keyboard)
        else:
            await bot.send_message(message.chat.id, "Вы не админ.")
    elif text == "💰 Баланс":
        balance = data['users'][user_id]['balance']
        ref_code = data['users'][user_id]['ref_code']
        bot_username = (await bot.get_me()).username
        await send_or_edit_message(message.chat.id, msg_id, BALANCE_TEXT.format(balance=balance, bot_username=bot_username, ref_code=ref_code), reply_markup=back_keyboard, parse_mode="HTML")
        data['users'][user_id]['current_screen'] = 'balance'
        save_data(data)
    elif text == "💎 Пополнить через TON" and data['users'][user_id].get('current_screen') == 'balance':
        deposit_text = """💎 Пополнение через TON

Отправьте сумму в TON (минимум 0.1 TON = 10 баллов)

Пример: 0.5

После оплаты баланс будет начислен автоматически.

↩️ Назад"""
        await send_or_edit_message(message.chat.id, msg_id, deposit_text)
        data['users'][user_id]['current_screen'] = 'deposit'
        save_data(data)
    elif data['users'][user_id].get('current_screen') == 'deposit' and text.replace('.', '').isdigit():
        try:
            amount_ton = float(text)
            if amount_ton < 0.1:
                await send_or_edit_message(message.chat.id, msg_id, "❌ Минимум 0.1 TON")
                return
            balance_add = int(amount_ton * 100)  # 1 TON = 100 баллов
            # Симуляция: сразу начислить
            add_balance(user_id, balance_add)
            await send_or_edit_message(message.chat.id, msg_id, f"✅ Баланс пополнен на {balance_add} баллов!")
        except:
            await send_or_edit_message(message.chat.id, msg_id, "❌ Неверная сумма")
    elif text == "📢 Заказать пиар":
        balance = data['users'][user_id]['balance']
        text_msg = f"""<b>📢 Что вы хотите рекламировать?</b>

💳 <b>Баланс:</b> {balance} VANISH

🚀 <i>Выберите тип рекламы и увеличьте свою аудиторию!</i>"""
        await send_or_edit_message(message.chat.id, msg_id, text_msg, reply_markup=pr_keyboard, parse_mode="HTML")
        data['users'][user_id]['current_screen'] = 'pr'
        save_data(data)
    elif text in ["1", "2", "3"] and data['users'][user_id].get('current_screen') == 'pr':
        costs = {'1': 10, '2': 5, '3': 2}
        cost = costs[text]
        if data['users'][user_id]['balance'] >= cost:
            data['users'][user_id]['balance'] -= cost
            save_data(data)
            await send_or_edit_message(message.chat.id, msg_id, f"✅ Пиар заказан! Списано {cost} баллов.")
        else:
            await send_or_edit_message(message.chat.id, msg_id, f"❌ Недостаточно баллов. Нужно {cost}.")
    elif text.startswith("@") and data['users'][user_id].get('current_screen') == 'channels':
        channel = text
        if channel not in data['users'][user_id]['channels']:
            data['users'][user_id]['channels'].append(channel)
            save_data(data)
        await send_or_edit_message(message.chat.id, msg_id, CHANNELS_TEXT.format(channels="\n".join(data['users'][user_id]['channels'])), reply_markup=back_keyboard)
        try:
            await message.delete()
        except:
            pass  # Если не может удалить
    elif text == "📊 Общая статистика" and message.from_user.id == config.ADMIN_ID:
        stats = data['stats']
        text_stats = f"Всего пользователей: {stats['total_users']}\nВсего каналов: {stats['total_channels']}\nОборот баллов: {stats['total_balance']}"
        await send_or_edit_message(message.chat.id, msg_id, text_stats)
    elif text == "💸 Начисление баллов" and message.from_user.id == config.ADMIN_ID:
        await send_or_edit_message(message.chat.id, msg_id, "Отправьте: user_id amount")
        data['users'][user_id]['current_screen'] = 'admin_add_balance'
        save_data(data)
    elif text == "🚫 Блокировка пользователя" and message.from_user.id == config.ADMIN_ID:
        await send_or_edit_message(message.chat.id, msg_id, "Отправьте user_id для блокировки")
        data['users'][user_id]['current_screen'] = 'admin_block'
        save_data(data)
    elif text == "📢 Рассылка" and message.from_user.id == config.ADMIN_ID:
        await send_or_edit_message(message.chat.id, msg_id, "Отправьте текст рассылки")
        data['users'][user_id]['current_screen'] = 'admin_broadcast'
        save_data(data)
    elif text == "🔧 Тарифы" and message.from_user.id == config.ADMIN_ID:
        await send_or_edit_message(message.chat.id, msg_id, "Тарифы: 1-10, 2-5, 3-2\nИзменить: отправьте новый тариф")
    elif text == "👤 Админы" and message.from_user.id == config.ADMIN_ID:
        admins = "\n".join(str(a) for a in data['admins'])
        await send_or_edit_message(message.chat.id, msg_id, f"Админы:\n{admins}\n\nДобавить: user_id\nУдалить: -user_id")
        data['users'][user_id]['current_screen'] = 'admin_admins'
        save_data(data)
    elif data['users'][user_id].get('current_screen') == 'admin_add_balance' and message.from_user.id == config.ADMIN_ID:
        try:
            target_id, amount = text.split()
            amount = int(amount)
            if target_id in data['users']:
                data['users'][target_id]['balance'] += amount
                data['stats']['total_balance'] += amount
                save_data(data)
                await send_or_edit_message(message.chat.id, msg_id, f"✅ Начислено {amount} баллов пользователю {target_id}")
            else:
                await bot.send_message(message.chat.id, "❌ Пользователь не найден")
        except:
            await bot.send_message(message.chat.id, "❌ Неверный формат")
    elif data['users'][user_id].get('current_screen') == 'admin_block' and message.from_user.id == config.ADMIN_ID:
        if text in data['users']:
            data['users'][text]['blocked'] = True
            save_data(data)
            await send_or_edit_message(message.chat.id, msg_id, f"✅ Пользователь {text} заблокирован")
        else:
            await bot.send_message(message.chat.id, "❌ Пользователь не найден")
    elif data['users'][user_id].get('current_screen') == 'admin_broadcast' and message.from_user.id == config.ADMIN_ID:
        for uid in data['users']:
            if not data['users'][uid].get('blocked'):
                try:
                    await bot.send_message(int(uid), f"📢 Рассылка:\n{text}")
                except:
                    pass
        await send_or_edit_message(message.chat.id, msg_id, "✅ Рассылка отправлена")
    elif data['users'][user_id].get('current_screen') == 'admin_admins' and message.from_user.id == config.ADMIN_ID:
        if text.startswith('-'):
            aid = text[1:]
            if int(aid) in data['admins']:
                data['admins'].remove(int(aid))
                save_data(data)
                await send_or_edit_message(message.chat.id, msg_id, f"✅ Админ {aid} удалён")
        elif text.isdigit():
            data['admins'].append(int(text))
            save_data(data)
            await send_or_edit_message(message.chat.id, msg_id, f"✅ Админ {text} добавлен")
        else:
            await bot.send_message(message.chat.id, "❌ Неверный формат")
    elif text == "👥 Мои каналы":
        channels = data['users'][user_id]['channels']
        text = "👥 Мои каналы\n\nВаши каналы:"
        if not channels:
            text += "\nНет каналов"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for ch in channels:
            keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"Удалить {ch}", callback_data=f"delete_channel:{ch}")])
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="↩️ Назад", callback_data="back")])
        await send_or_edit_message(message.chat.id, msg_id, text, reply_markup=keyboard)
        data['users'][user_id]['current_screen'] = 'channels'
        save_data(data)
# Рефералка в балансе
    elif text == "📊 Статистика":
        total_users = data['stats']['total_users']
        users_today = data['stats'].get('users_today', 0)
        total_groups = len(data['groups'])
        await send_or_edit_message(message.chat.id, msg_id, STATS_TEXT.format(total_users=total_users, users_today=users_today, total_groups=total_groups), reply_markup=back_keyboard, parse_mode="HTML")
    elif text == "❓ Помощь":
        await send_or_edit_message(message.chat.id, msg_id, HELP_TEXT, reply_markup=back_keyboard, parse_mode="HTML")
    elif data.get('waiting_for_broadcast') and message.from_user.id == config.ADMIN_ID:
        data['broadcast_message'] = {'chat_id': message.chat.id, 'message_id': message.message_id}
        data['waiting_for_broadcast'] = False
        save_data(data)
        # Мгновенная рассылка
        msg = data['broadcast_message']
        for group_id in data['groups']:
            try:
                await bot.forward_message(chat_id=int(group_id), from_chat_id=msg['chat_id'], message_id=msg['message_id'])
            except Exception as e:
                logging.error(f"Error forwarding to {group_id}: {e}")
        await message.reply("✅ Рассылка начата. Сообщение отправлено сразу во все группы и будет повторяться каждые 2.5 минуты.", parse_mode="HTML")
    elif data['users'][user_id].get('current_screen') == 'enter_channel':
        selected_type = data['users'][user_id].get('selected_type', '')

        if selected_type == 'post':
            # Обработка постов
            if not (text.startswith('https://t.me/') or text.startswith('http://t.me/')):
                await send_or_edit_message(message.chat.id, msg_id, "❌ Отправьте ссылку на пост в формате:\n\n📝 <b>Примеры:</b>\n• https://t.me/channel/123\n• http://t.me/channel/123\n\n<i>Где 123 - номер сообщения</i>", reply_markup=back_keyboard, parse_mode="HTML")
                return
            parts = text.replace('http://t.me/', '').replace('https://t.me/', '').split('/')
            if len(parts) != 2 or not parts[1].isdigit():
                await send_or_edit_message(message.chat.id, msg_id, "❌ Неверный формат ссылки!\n\n📝 <b>Правильный формат:</b>\nhttps://t.me/channel/123\n\n<i>Где:</i>\n• <b>channel</b> - username канала\n• <b>123</b> - номер сообщения", reply_markup=back_keyboard, parse_mode="HTML")
                return
            channel = '@' + parts[0]
            message_id = int(parts[1])
            data['users'][user_id]['entered_post'] = {'chat_id': channel, 'message_id': message_id}
            text_msg = f"✅ Ваш пост принят: {html.escape(text)}\n\n📝 <b>Проверьте правильность ссылки</b> и нажмите 'Подтвердить' для активации рекламы.\n\n<i>Формат: https://t.me/channel/123</i>"

        elif selected_type in ['channel', 'group', 'bot']:
            # Обработка каналов, групп и ботов
            channel = text.strip()

            # Поддержка различных форматов
            if channel.startswith('@'):
                # Уже правильный формат @username
                pass
            elif channel.startswith('https://t.me/') or channel.startswith('http://t.me/'):
                # Ссылка https://t.me/username
                channel = '@' + channel.split('/')[-1]
            elif channel.startswith('t.me/'):
                # Ссылка t.me/username
                channel = '@' + channel.replace('t.me/', '')
            elif not channel.startswith('@'):
                # Если пользователь ввел просто username без @
                channel = '@' + channel

            data['users'][user_id]['entered_channel'] = channel
            channel_type = {'channel': 'канал', 'group': 'группу', 'bot': 'бот'}[selected_type]
            text_msg = f"✅ Ваш {html.escape(channel_type)} принят: {html.escape(channel)}\n\n📝 <b>Проверьте правильность</b> и нажмите 'Подтвердить' для активации рекламы.\n\n<i>Если формат неверный, нажмите 'Редактировать'</i>"
        else:
            await send_or_edit_message(message.chat.id, msg_id, "Произошла ошибка. Попробуйте снова.", reply_markup=back_keyboard)
            return

        save_data(data)
        await send_or_edit_message(message.chat.id, msg_id, text_msg, reply_markup=confirm_channel_keyboard)
        try:
            await message.delete()
        except:
            pass

async def send_broadcast():
    while True:
        data = load_data()
        if 'broadcast_message' in data:
            msg = data['broadcast_message']
            for group_id in data['groups']:
                try:
                    await bot.forward_message(chat_id=int(group_id), from_chat_id=msg['chat_id'], message_id=msg['message_id'])
                except Exception as e:
                    logging.error(f"Error forwarding to {group_id}: {e}")
        await asyncio.sleep(150)  # 2.5 минуты

# Запуск бота
async def main():
    asyncio.create_task(send_broadcast())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())