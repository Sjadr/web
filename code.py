import os
import json
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from PIL import Image
import requests
from io import BytesIO
from threading import Timer
from datetime import datetime

# ---------------- CONFIGURATION FILES ----------------
CONFIG_FILE = 'config.json'
USERS_FILE = 'users.json'
IMAGES_FOLDER = 'images'
BACKUP_FILE = 'backup_config.json'

os.makedirs(IMAGES_FOLDER, exist_ok=True)

# Load or initialize config
def load_config():
    if os.path.exists(CONFIG_FILE):
        return json.load(open(CONFIG_FILE, 'r', encoding='utf-8'))
    return {
        'developer_id': 651561282,
        'admins': [],
        'banned_users': [],
        'sticker_label': 'ستيكرات المطور',
        'sticker_url': 'https://t.me/addstickers/emg_s'
    }
config = load_config()

# Load or initialize users
def load_users():
    if os.path.exists(USERS_FILE):
        raw = json.load(open(USERS_FILE, 'r', encoding='utf-8'))
    else:
        raw = []
    users = []
    for u in raw:
        if isinstance(u, int):
            users.append({'id': u, 'username': ''})
        elif isinstance(u, dict) and 'id' in u:
            users.append({'id': u['id'], 'username': u.get('username', '')})
    return users
users = load_users()

# Save helpers
def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
def save_config():
    save_json(CONFIG_FILE, config)
def save_users():
    save_json(USERS_FILE, users)
def backup_config():
    save_json(BACKUP_FILE, {'config': config, 'users': users})
def restore_config():
    if os.path.exists(BACKUP_FILE):
        data = json.load(open(BACKUP_FILE, 'r', encoding='utf-8'))
        save_json(CONFIG_FILE, data['config'])
        save_json(USERS_FILE, data['users'])
        return True
    return False

# Bot initialization
TOKEN = '6472606496:AAGmgLlNWpX_ZJDldgvAZpm2Uy9254RYdDQ'
bot = telebot.TeleBot(TOKEN)

# State containers
images_to_color = {}
broadcast_context = {}
permissions = {}
sticker_context = {}
welcome_context = {}
messages_from_users = {}

# Privilege levels
LEVELS = {'basic': 0, 'operator': 1, 'admin': 2, 'owner': 3}
def level(uid):
    if uid == config['developer_id']:
        return LEVELS['owner']
    if uid in config['admins']:
        return LEVELS['admin']
    return permissions.get(uid, LEVELS['basic'])

# ---------------- COMMAND HANDLERS ----------------
@bot.message_handler(commands=['start'])
def cmd_start(message):
    uid = message.chat.id
    uname = message.from_user.username or ''
    existing = next((u for u in users if u['id'] == uid), None)
    if not existing:
        users.append({'id': uid, 'username': uname})
        save_users()
    elif existing['username'] != uname:
        existing['username'] = uname
        save_users()
    text = f"مرحبًا بك {message.from_user.first_name} في بوت توسيط الصور. أرسل صورة أو استخدم الأزرار أدناه."
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(config['sticker_label'], url=config['sticker_url']))
    kb.add(
        InlineKeyboardButton('تلوين', callback_data='colorize'),
        InlineKeyboardButton('تواصل', callback_data='contact_developer')
    )
    bot.send_message(uid, text, reply_markup=kb)

@bot.message_handler(commands=['admin'])
def basic_admin_panel(message):
    uid = message.chat.id
    if level(uid) < LEVELS['admin']:
        bot.send_message(uid, '🚫 لا تمتلك صلاحية.')
        return
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('❌ حظر مستخدم', callback_data='ban_user'),
        InlineKeyboardButton('✅ إلغاء حظر', callback_data='unban_user'),
        InlineKeyboardButton('📢 اذاعة بدون تثبيت', callback_data='broadcast_no_pin'),
        InlineKeyboardButton('📌 اذاعة وتثبيت', callback_data='broadcast_with_pin'),
        InlineKeyboardButton('➕ إضافة آدمن', callback_data='add_admin'),
        InlineKeyboardButton('➖ إزالة آدمن', callback_data='remove_admin'),
        InlineKeyboardButton('🖼️ استعراض الصور', callback_data='view_images'),
        InlineKeyboardButton('👥 المستخدمون', callback_data='view_users'),
        InlineKeyboardButton('⚙️ إعدادات', callback_data='edit_config'),
        InlineKeyboardButton('🛠️ الإعدادات المتقدمة', callback_data='advanced_settings')
    )
    bot.send_message(uid, '🎛️ لوحة التحكم:', reply_markup=kb)

# Advanced panel function
def advanced_panel(uid):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('📊 إحصائيات', callback_data='stats'),
        InlineKeyboardButton('✏️ تعديل ترحيب', callback_data='edit_welcome'),
        InlineKeyboardButton('⏰ جدولة بث', callback_data='schedule_broadcast'),
        InlineKeyboardButton('💾 نسخ احتياطي', callback_data='backup'),
        InlineKeyboardButton('♻️ استعادة', callback_data='restore'),
        InlineKeyboardButton('🔑 صلاحيات', callback_data='manage_perms'),
        InlineKeyboardButton('⬅️ رجوع', callback_data='view_basic')
    )
    bot.send_message(uid, '🎛️ الإعدادات المتقدمة:', reply_markup=kb)

# ---------------- CALLBACK HANDLER ----------------
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    data = call.data
    # User actions
    if data == 'colorize':
        images_to_color[uid] = True
        bot.send_message(uid, 'أرسل الصورة للتلوين.')
        return
    if data == 'contact_developer':
        bot.send_message(uid, 'أرسل رسالتك للمطور.')
        messages_from_users[call.message.message_id] = uid
        return
    # Panel switching
    if data == 'view_basic':
        return basic_admin_panel(call.message)
    if data == 'advanced_settings' and level(uid) >= LEVELS['admin']:
        return advanced_panel(uid)
    # Advanced actions
    if data == 'stats' and level(uid) >= LEVELS['operator']:
        stats_text = f"📊 إحصائيات:\n- مستخدمين: {len(users)}\n- آدمنات: {len(config['admins'])}\n- صور: {len(os.listdir(IMAGES_FOLDER))}"
        bot.send_message(uid, stats_text)
        return
    if data == 'edit_welcome' and level(uid) >= LEVELS['operator']:
        welcome_context[uid] = {}
        bot.send_message(uid, '✏️ ادخل رسالة الترحيب الجديدة:')
        return
    if data == 'schedule_broadcast' and level(uid) >= LEVELS['operator']:
        broadcast_context[uid] = {'pin': False}
        bot.send_message(uid, '⏰ ارسل وقت البث بصيغة YYYY-MM-DD HH:MM')
        return
    if data == 'backup' and level(uid) >= LEVELS['admin']:
        backup_config()
        bot.send_message(uid, '💾 تم النسخ الاحتياطي')
        return
    if data == 'restore' and level(uid) >= LEVELS['admin']:
        ok = restore_config()
        bot.send_message(uid, '✅ تم الاستعادة' if ok else '❌ لا يوجد نسخة')
        return
    if data == 'manage_perms' and level(uid) >= LEVELS['owner']:
        bot.send_message(uid, '🔑 تحت التطوير')
        return
    # Admin actions
    if level(uid) < LEVELS['admin']:
        bot.answer_callback_query(call.id, '🚫 ما عندك صلاحية.')
        return
    if data == 'ban_user':
        msg = bot.send_message(uid, 'ادخل ايدي الحظر:')
        bot.register_next_step_handler(msg, process_ban)
        return
    if data == 'unban_user':
        msg = bot.send_message(uid, 'ادخل ايدي فك الحظر:')
        bot.register_next_step_handler(msg, process_unban)
        return
    if data in ['broadcast_no_pin', 'broadcast_with_pin']:
        broadcast_context[uid] = {'pin': data == 'broadcast_with_pin'}
        msg = bot.send_message(uid, 'ارسل الآن النص/الوسائط للإذاعة:')
        bot.register_next_step_handler(msg, process_broadcast_message)
        return
    if data == 'add_admin':
        msg = bot.send_message(uid, 'ادخل ايدي لمنح آدمن:')
        bot.register_next_step_handler(msg, process_add_admin)
        return
    if data == 'remove_admin':
        msg = bot.send_message(uid, 'ادخل ايدي لإزالة آدمن:')
        bot.register_next_step_handler(msg, process_remove_admin)
        return
    if data == 'view_images':
        imgs = os.listdir(IMAGES_FOLDER)
        if not imgs:
            bot.send_message(uid, 'لا توجد صور.')
            return
        for img in imgs:
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton('حذف', callback_data=f'del_img:{img}'))
            bot.send_photo(uid, open(os.path.join(IMAGES_FOLDER, img), 'rb'), caption=img, reply_markup=kb)
        return
    if data.startswith('del_img:'):
        img = data.split(':', 1)[1]
        path = os.path.join(IMAGES_FOLDER, img)
        if os.path.exists(path): os.remove(path)
        bot.answer_callback_query(call.id, '🗑️ حذف!')
        return
    if data == 'view_users':
        lines = [f"- {u['id']} (@{u['username']})" for u in users]
        bot.send_message(uid, '👥 المستخدمون:\n' + ('\n'.join(lines) if lines else 'لا مستخدمين'))
        return
    if data == 'edit_config':
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton('👤 تغيير مطور', callback_data='edit_dev'),
            InlineKeyboardButton('🎟️ تعديل ستيكر', callback_data='edit_sticker'),
            InlineKeyboardButton('🗑️ مسح جميع الصور', callback_data='clear_images'),
            InlineKeyboardButton('👥 عرض آدمنات', callback_data='list_admins'),
            InlineKeyboardButton('🚫 عرض محظورين', callback_data='list_banned'),
            InlineKeyboardButton('⬅️ رجوع', callback_data='view_basic')
        )
        bot.send_message(uid, '⚙️ الإعدادات:', reply_markup=kb)
        return
    if data == 'clear_images':
        for f in os.listdir(IMAGES_FOLDER): os.remove(os.path.join(IMAGES_FOLDER, f))
        bot.send_message(uid, '🗑️ مسحت جميع الصور على السيرفر.')
        return
    if data == 'list_admins':
        bot.send_message(uid, '👥 آدمنات:\n' + ('\n'.join(map(str, config['admins'])) or 'لا يوجد'))
        return
    if data == 'list_banned':
        bot.send_message(uid, '🚫 محظورين:\n' + ('\n'.join(map(str, config['banned_users'])) or 'لا يوجد'))
        return
    if data == 'edit_sticker':
        msg = bot.send_message(uid, '📥 ادخل نص الزر الجديد:')
        sticker_context[uid] = {}
        bot.register_next_step_handler(msg, process_sticker_label)
        return
    if data == 'edit_dev':
        msg = bot.send_message(uid, 'أدخل ايدي المطور:')
        bot.register_next_step_handler(msg, process_edit_dev)
        return

# ---------------- CONTEXT HANDLERS ----------------
def process_ban(message):
    try:
        x = int(message.text)
        config['banned_users'].append(x)
        save_config()
        bot.send_message(message.chat.id, '✅ تم حظر')
    except:
        bot.send_message(message.chat.id, '❌ خطأ')

def process_unban(message):
    try:
        x = int(message.text)
        config['banned_users'].remove(x)
        save_config()
        bot.send_message(message.chat.id, '✅ تم فك الحظر')
    except:
        bot.send_message(message.chat.id, '❌ خطأ')

def process_add_admin(message):
    try:
        x = int(message.text)
        config['admins'].append(x)
        save_config()
        bot.send_message(message.chat.id, '✅ آدمن مضاف')
    except:
        bot.send_message(message.chat.id, '❌ خطأ')

def process_remove_admin(message):
    try:
        x = int(message.text)
        config['admins'].remove(x)
        save_config()
        bot.send_message(message.chat.id, '✅ آدمن محذوف')
    except:
        bot.send_message(message.chat.id, '❌ خطأ')

@bot.message_handler(func=lambda m: m.chat.id in welcome_context)
def set_welcome(message):
    config['welcome_message'] = message.text
    save_config()
    welcome_context.pop(message.chat.id, None)
    bot.send_message(message.chat.id, '✅ تم تحديث الترحيب')

@bot.message_handler(func=lambda m: m.text and m.chat.id in broadcast_context)
def schedule_broadcast(message):
    try:
        dt = datetime.strptime(message.text, '%Y-%m-%d %H:%M')
        delta = (dt - datetime.now()).total_seconds()
        if delta < 0:
            raise ValueError()
        t = Timer(delta, send_scheduled, args=[message.chat.id])
        scheduled.append(t)
        t.start()
        bot.send_message(message.chat.id, '⏰ تم جدولة البث')
    except:
        bot.send_message(message.chat.id, '❌ صيغة خاطئة')
def send_scheduled(uid):
    bot.send_message(uid, '⏰ ارسل المحتوى الآن للبث المجدول')

@bot.message_handler(func=lambda m: m.chat.id in broadcast_context)
def process_broadcast_message(message):
    ctx = broadcast_context.pop(message.chat.id)
    pin = ctx.get('pin', False)
    count = 0
    for u in users:
        if u['id'] in config['banned_users']:
            continue
        try:
            if message.content_type == 'text': sent = bot.send_message(u['id'], message.text)
            elif message.content_type == 'photo': sent = bot.send_photo(u['id'], message.photo[-1].file_id, caption=message.caption)
            elif message.content_type == 'audio': sent = bot.send_audio(u['id'], message.audio.file_id, caption=message.caption)
            elif message.content_type == 'document': sent = bot.send_document(u['id'], message.document.file_id, caption=message.caption)
            else: continue
            if pin:
                bot.pin_chat_message(u['id'], sent.message_id)
            count += 1
        except:
            pass
    bot.send_message(message.chat.id, f'⚙️ أرسلت إلى {count} مستخدمين.')

def process_sticker_label(message):
    sticker_context[message.chat.id] = {'label': message.text}
    msg = bot.send_message(message.chat.id, '📥 الآن، ادخل رابط الستكر:')
    bot.register_next_step_handler(msg, process_sticker_url)

def process_sticker_url(message):
    ctx = sticker_context.pop(message.chat.id, {})
    config['sticker_label'] = ctx.get('label', config['sticker_label'])
    config['sticker_url'] = message.text
    save_config()
    bot.send_message(message.chat.id, '✅ تم تحديث زر الاستيكر.')

def process_edit_dev(message):
    try:
        config['developer_id'] = int(message.text)
        save_config()
        bot.send_message(message.chat.id, '✅ تم تغيير المطور')
    except:
        bot.send_message(message.chat.id, '❌ خطأ')

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if message.chat.id in config['banned_users']:
        return
    uid = message.chat.id
    info = bot.get_file(message.photo[-1].file_id)
    fn = os.path.join(IMAGES_FOLDER, f"{uid}_{message.message_id}.jpg")
    open(fn, 'wb').write(requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{info.file_path}").content)
    if images_to_color.pop(uid, False):
        img = Image.open(fn).convert('L')
    else:
        img = Image.open(fn)
        w, h = img.size
        canvas = Image.new('RGB', (w, h+250), (255, 255, 255))
        canvas.paste(img, (0, 125))
        img = canvas
    out = BytesIO()
    img.save(out, 'JPEG')
    out.seek(0)
    bot.send_photo(uid, out)

@bot.message_handler(content_types=['new_chat_members'])
def new_member(msg):
    for m in msg.new_chat_members:
        if not any(u['id'] == m.id for u in users):
            users.append({'id': m.id, 'username': m.username or ''})
            save_users()
        bot.send_message(config['developer_id'], f"🆕 عضو: {m.first_name} ({m.id})")

@bot.message_handler(func=lambda m: True)
def handle_msg(m):
    if m.chat.id != config['developer_id'] and m.text:
        bot.send_message(config['developer_id'], f"رسالة من @{m.from_user.username}: {m.text}")
        messages_from_users[m.message_id] = m.chat.id
    elif m.chat.id == config['developer_id'] and m.reply_to_message and m.text:
        to = messages_from_users.get(m.reply_to_message.message_id)
        bot.send_message(to, f"رد المطور: {m.text}")

print("Bot is running...")
bot.polling(none_stop=True)
