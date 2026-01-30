import asyncio
import re
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    ChatMemberHandler,
    filters,
    MessageHandler
)
from telegram.error import TelegramError

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class RentalData:
    def __init__(self):
        self.rentals: Dict[int, Dict[int, datetime]] = {}
        self.admins: List[int] = []
        self.bot_channels: Dict[int, str] = {}
        self.channel_members: Dict[int, Dict[int, dict]] = {}
        self.data_file = "rental_data.json"
        self.load_data()

    def save_data(self):
        data = {
            "rentals": {
                str(chat_id): {
                    str(user_id): expire_time.isoformat()
                    for user_id, expire_time in users.items()
                }
                for chat_id, users in self.rentals.items()
            },
            "admins": self.admins,
            "bot_channels": {str(k): v for k, v in self.bot_channels.items()},
            "channel_members": {
                str(chat_id): {
                    str(user_id): member_info
                    for user_id, member_info in members.items()
                }
                for chat_id, members in self.channel_members.items()
            }
        }
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("Data saved successfully")
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    def load_data(self):
        if not os.path.exists(self.data_file):
            logger.info("No data file found, starting fresh")
            return
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.rentals = {
                int(chat_id): {
                    int(user_id): datetime.fromisoformat(expire_time)
                    for user_id, expire_time in users.items()
                }
                for chat_id, users in data.get("rentals", {}).items()
            }
            
            self.admins = data.get("admins", [])
            self.bot_channels = {int(k): v for k, v in data.get("bot_channels", {}).items()}
            self.channel_members = {
                int(chat_id): {
                    int(user_id): member_info
                    for user_id, member_info in members.items()
                }
                for chat_id, members in data.get("channel_members", {}).items()
            }
            
            logger.info(f"Data loaded: {len(self.bot_channels)} channels, {sum(len(u) for u in self.rentals.values())} rentals")
        except Exception as e:
            logger.error(f"Error loading data: {e}")

    def add_rental(self, chat_id: int, user_id: int, expire_time: datetime):
        if chat_id not in self.rentals:
            self.rentals[chat_id] = {}
        self.rentals[chat_id][user_id] = expire_time
        self.save_data()

    def remove_rental(self, chat_id: int, user_id: int):
        if chat_id in self.rentals and user_id in self.rentals[chat_id]:
            del self.rentals[chat_id][user_id]
            if not self.rentals[chat_id]:
                del self.rentals[chat_id]
            self.save_data()

    def get_rental(self, chat_id: int, user_id: int) -> Optional[datetime]:
        return self.rentals.get(chat_id, {}).get(user_id)

    def get_all_rentals(self, chat_id: int) -> Dict[int, datetime]:
        return self.rentals.get(chat_id, {})

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admins

    def add_admin(self, user_id: int):
        if user_id not in self.admins:
            self.admins.append(user_id)
            self.save_data()

    def remove_admin(self, user_id: int):
        if user_id in self.admins:
            self.admins.remove(user_id)
            self.save_data()

    def add_channel(self, chat_id: int, title: str):
        self.bot_channels[chat_id] = title
        if chat_id not in self.channel_members:
            self.channel_members[chat_id] = {}
        self.save_data()

    def remove_channel(self, chat_id: int):
        if chat_id in self.bot_channels:
            del self.bot_channels[chat_id]
        if chat_id in self.rentals:
            del self.rentals[chat_id]
        if chat_id in self.channel_members:
            del self.channel_members[chat_id]
        self.save_data()

    def add_member(self, chat_id: int, user_id: int, username: str, full_name: str, status: str, join_time: str):
        if chat_id not in self.channel_members:
            self.channel_members[chat_id] = {}
        self.channel_members[chat_id][user_id] = {
            "username": username,
            "full_name": full_name,
            "status": status,
            "join_time": join_time,
            "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.save_data()

    def update_member_status(self, chat_id: int, user_id: int, status: str):
        if chat_id in self.channel_members and user_id in self.channel_members[chat_id]:
            self.channel_members[chat_id][user_id]["status"] = status
            self.channel_members[chat_id][user_id]["last_update"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.save_data()

    def remove_member(self, chat_id: int, user_id: int):
        if chat_id in self.channel_members and user_id in self.channel_members[chat_id]:
            del self.channel_members[chat_id][user_id]
            self.save_data()

    def get_members(self, chat_id: int) -> Dict[int, dict]:
        return self.channel_members.get(chat_id, {})

    def get_member_info(self, chat_id: int, user_id: int) -> Optional[dict]:
        return self.channel_members.get(chat_id, {}).get(user_id)

    def search_member(self, query: str) -> List[tuple]:
        results = []
        for chat_id, members in self.channel_members.items():
            for user_id, info in members.items():
                if (query.lower() in info.get("username", "").lower() or
                    query.lower() in info.get("full_name", "").lower() or
                    query in str(user_id)):
                    results.append((chat_id, user_id, info))
        return results

    def get_total_members(self, chat_id: int) -> int:
        return len(self.channel_members.get(chat_id, {}))

    def get_all_stats(self) -> dict:
        stats = {
            "total_channels": len(self.bot_channels),
            "total_members": sum(len(members) for members in self.channel_members.values()),
            "total_rentals": sum(len(rentals) for rentals in self.rentals.values()),
            "total_admins": len(self.admins)
        }
        return stats

rental_data = RentalData()

def parse_time_string(time_str: str) -> Optional[timedelta]:
    pattern = r'^(\d+)([dwmy])$'
    match = re.match(pattern, time_str.lower())
    if not match:
        return None
    
    amount = int(match.group(1))
    unit = match.group(2)
    
    if unit == 'd':
        return timedelta(days=amount)
    elif unit == 'w':
        return timedelta(weeks=amount)
    elif unit == 'm':
        return timedelta(days=amount * 30)
    elif unit == 'y':
        return timedelta(days=amount * 365)
    return None

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False):
    keyboard = [
        [
            InlineKeyboardButton("📋 Danh sách kênh", callback_data="main_menu"),
            InlineKeyboardButton("👥 Members kênh", callback_data="members_menu")
        ],
        [
            InlineKeyboardButton("➕ Thêm thời gian", callback_data="add_time_menu"),
            InlineKeyboardButton("🔄 Gia hạn", callback_data="extend_time_menu")
        ],
        [
            InlineKeyboardButton("🗑️ Xóa thời gian", callback_data="remove_time_menu"),
            InlineKeyboardButton("🔍 Tìm kiếm", callback_data="search_menu")
        ],
        [
            InlineKeyboardButton("📊 Thống kê", callback_data="stats_menu"),
            InlineKeyboardButton("👔 Quản lý Admin", callback_data="admin_menu")
        ],
        [
            InlineKeyboardButton("ℹ️ Hướng dẫn", callback_data="help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "🤖 Bot quản lý thời gian thuê Telegram\n\nChọn chức năng bên dưới:"
    
    if is_callback:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not rental_data.is_admin(user_id):
        rental_data.add_admin(user_id)
        await update.message.reply_text(
            "✅ Chào mừng! Bạn đã được cấp quyền Admin.\n\n"
            "Sử dụng /menu để xem các chức năng."
        )
    else:
        await update.message.reply_text("✅ Bạn đã là Admin!")
    
    await show_main_menu(update, context)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, context)

async def settime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rental_data.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này!")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Sai cú pháp!\n\n"
            "Sử dụng: /settime <time> <@username|id>\n"
            "Ví dụ: /settime 1d @username"
        )
        return

    time_str = context.args[0]
    user_identifier = context.args[1]

    duration = parse_time_string(time_str)
    if not duration:
        await update.message.reply_text("❌ Định dạng thời gian không hợp lệ! (1d, 1w, 1m, 1y)")
        return

    try:
        if user_identifier.startswith('@'):
            user = await context.bot.get_chat(user_identifier)
            user_id = user.id
        else:
            user_id = int(user_identifier)
            user = await context.bot.get_chat(user_id)
    except:
        await update.message.reply_text("❌ Không tìm thấy user!")
        return

    if not rental_data.bot_channels:
        await update.message.reply_text("❌ Bot chưa được thêm vào kênh nào!")
        return

    keyboard = []
    for chat_id, title in rental_data.bot_channels.items():
        keyboard.append([InlineKeyboardButton(
            title,
            callback_data=f"settime_{chat_id}_{user_id}_{time_str}"
        )])
    keyboard.append([InlineKeyboardButton("❌ Hủy", callback_data="back_to_start")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Chọn kênh để thêm thời gian cho user {user.full_name}:",
        reply_markup=reply_markup
    )

async def removetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rental_data.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này!")
        return

    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Sai cú pháp!\n\n"
            "Sử dụng: /removetime <@username|id>\n"
            "Ví dụ: /removetime @username"
        )
        return

    user_identifier = context.args[0]

    try:
        if user_identifier.startswith('@'):
            user = await context.bot.get_chat(user_identifier)
            user_id = user.id
        else:
            user_id = int(user_identifier)
            user = await context.bot.get_chat(user_id)
    except:
        await update.message.reply_text("❌ Không tìm thấy user!")
        return

    keyboard = []
    found_rentals = False
    
    for chat_id, title in rental_data.bot_channels.items():
        if rental_data.get_rental(chat_id, user_id):
            keyboard.append([InlineKeyboardButton(
                f"🗑️ {title}",
                callback_data=f"removetime_{chat_id}_{user_id}"
            )])
            found_rentals = True

    if not found_rentals:
        await update.message.reply_text(f"❌ User {user.full_name} không có thời gian thuê nào!")
        return

    keyboard.append([InlineKeyboardButton("❌ Hủy", callback_data="back_to_start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Chọn kênh để xóa thời gian của {user.full_name}:",
        reply_markup=reply_markup
    )

async def extendtime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rental_data.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này!")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Sai cú pháp!\n\n"
            "Sử dụng: /extendtime <time> <@username|id>\n"
            "Ví dụ: /extendtime 1d @username"
        )
        return

    time_str = context.args[0]
    user_identifier = context.args[1]

    duration = parse_time_string(time_str)
    if not duration:
        await update.message.reply_text("❌ Định dạng thời gian không hợp lệ! (1d, 1w, 1m, 1y)")
        return

    try:
        if user_identifier.startswith('@'):
            user = await context.bot.get_chat(user_identifier)
            user_id = user.id
        else:
            user_id = int(user_identifier)
            user = await context.bot.get_chat(user_id)
    except:
        await update.message.reply_text("❌ Không tìm thấy user!")
        return

    keyboard = []
    found_rentals = False
    
    for chat_id, title in rental_data.bot_channels.items():
        if rental_data.get_rental(chat_id, user_id):
            keyboard.append([InlineKeyboardButton(
                f"🔄 {title}",
                callback_data=f"extendtime_{chat_id}_{user_id}_{time_str}"
            )])
            found_rentals = True

    if not found_rentals:
        await update.message.reply_text(f"❌ User {user.full_name} không có thời gian thuê nào!")
        return

    keyboard.append([InlineKeyboardButton("❌ Hủy", callback_data="back_to_start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Chọn kênh để gia hạn thời gian cho {user.full_name}:",
        reply_markup=reply_markup
    )

async def memberinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rental_data.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này!")
        return

    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Sai cú pháp!\n\n"
            "Sử dụng: /memberinfo <@username|id>\n"
            "Ví dụ: /memberinfo @username"
        )
        return

    user_identifier = context.args[0]

    try:
        if user_identifier.startswith('@'):
            user = await context.bot.get_chat(user_identifier)
            user_id = user.id
        else:
            user_id = int(user_identifier)
            user = await context.bot.get_chat(user_id)
    except:
        await update.message.reply_text("❌ Không tìm thấy user!")
        return

    info_text = f"👤 THÔNG TIN MEMBER\n\n"
    info_text += f"🆔 ID: {user_id}\n"
    info_text += f"👤 Tên: {user.full_name}\n"
    info_text += f"📧 Username: @{user.username if user.username else 'Không có'}\n\n"
    
    found_in_channels = False
    
    for chat_id, title in rental_data.bot_channels.items():
        member_info = rental_data.get_member_info(chat_id, user_id)
        rental_time = rental_data.get_rental(chat_id, user_id)
        
        if member_info or rental_time:
            found_in_channels = True
            info_text += f"📺 Kênh: {title}\n"
            
            if member_info:
                info_text += f"   ✅ Trạng thái: {member_info.get('status', 'N/A')}\n"
                info_text += f"   📅 Tham gia: {member_info.get('join_time', 'N/A')}\n"
            
            if rental_time:
                time_left = rental_time - datetime.now()
                if time_left.total_seconds() > 0:
                    days = time_left.days
                    hours = time_left.seconds // 3600
                    info_text += f"   ⏳ Thuê còn: {days}d {hours}h\n"
                    info_text += f"   📅 Hết hạn: {rental_time.strftime('%Y-%m-%d %H:%M')}\n"
                else:
                    info_text += f"   ⚠️ Đã hết hạn\n"
            
            info_text += "\n"
    
    if not found_in_channels:
        info_text += "❌ User chưa tham gia kênh nào!\n"
    
    await update.message.reply_text(info_text)

async def searchmember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rental_data.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này!")
        return

    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Sai cú pháp!\n\n"
            "Sử dụng: /searchmember <tên|username|id>\n"
            "Ví dụ: /searchmember john"
        )
        return

    query = " ".join(context.args)
    results = rental_data.search_member(query)

    if not results:
        await update.message.reply_text(f"❌ Không tìm thấy member nào với từ khóa '{query}'!")
        return

    text = f"🔍 KẾT QUẢ TÌM KIẾM: '{query}'\n\n"
    
    for chat_id, user_id, info in results[:10]:
        channel_name = rental_data.bot_channels.get(chat_id, "Unknown")
        text += f"📺 {channel_name}\n"
        text += f"   👤 {info.get('full_name', 'N/A')}\n"
        text += f"   📧 {info.get('username', 'N/A')}\n"
        text += f"   🆔 ID: {user_id}\n"
        text += f"   📅 Tham gia: {info.get('join_time', 'N/A')}\n\n"
    
    if len(results) > 10:
        text += f"... và {len(results) - 10} kết quả khác"
    
    await update.message.reply_text(text)

async def removemember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rental_data.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này!")
        return

    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Sai cú pháp!\n\n"
            "Sử dụng: /removemember <@username|id>\n"
            "Ví dụ: /removemember @username"
        )
        return

    user_identifier = context.args[0]

    try:
        if user_identifier.startswith('@'):
            user = await context.bot.get_chat(user_identifier)
            user_id = user.id
        else:
            user_id = int(user_identifier)
            user = await context.bot.get_chat(user_id)
    except:
        await update.message.reply_text("❌ Không tìm thấy user!")
        return

    keyboard = []
    found_members = False
    
    for chat_id, title in rental_data.bot_channels.items():
        if rental_data.get_member_info(chat_id, user_id):
            keyboard.append([InlineKeyboardButton(
                f"🗑️ {title}",
                callback_data=f"removemember_{chat_id}_{user_id}"
            )])
            found_members = True

    if not found_members:
        await update.message.reply_text(f"❌ User {user.full_name} không có trong kênh nào!")
        return

    keyboard.append([InlineKeyboardButton("❌ Hủy", callback_data="back_to_start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Chọn kênh để xóa member {user.full_name}:",
        reply_markup=reply_markup
    )

async def exportmembers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rental_data.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này!")
        return

    if not rental_data.bot_channels:
        await update.message.reply_text("❌ Không có kênh nào!")
        return

    keyboard = []
    for chat_id, title in rental_data.bot_channels.items():
        member_count = rental_data.get_total_members(chat_id)
        keyboard.append([InlineKeyboardButton(
            f"{title} ({member_count} members)",
            callback_data=f"export_{chat_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("📊 Xuất tất cả", callback_data="export_all")])
    keyboard.append([InlineKeyboardButton("❌ Hủy", callback_data="back_to_start")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Chọn kênh để xuất danh sách members:",
        reply_markup=reply_markup
    )

async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rental_data.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này!")
        return

    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Sai cú pháp!\n\n"
            "Sử dụng: /addadmin <@username|id>\n"
            "Ví dụ: /addadmin @username"
        )
        return

    user_identifier = context.args[0]

    try:
        if user_identifier.startswith('@'):
            user = await context.bot.get_chat(user_identifier)
            user_id = user.id
        else:
            user_id = int(user_identifier)
            user = await context.bot.get_chat(user_id)
    except:
        await update.message.reply_text("❌ Không tìm thấy user!")
        return

    if rental_data.is_admin(user_id):
        await update.message.reply_text(f"❌ {user.full_name} đã là admin rồi!")
        return

    rental_data.add_admin(user_id)
    await update.message.reply_text(f"✅ Đã thêm {user.full_name} làm admin!")

async def removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rental_data.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này!")
        return

    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Sai cú pháp!\n\n"
            "Sử dụng: /removeadmin <@username|id>\n"
            "Ví dụ: /removeadmin @username"
        )
        return

    user_identifier = context.args[0]

    try:
        if user_identifier.startswith('@'):
            user = await context.bot.get_chat(user_identifier)
            user_id = user.id
        else:
            user_id = int(user_identifier)
            user = await context.bot.get_chat(user_id)
    except:
        await update.message.reply_text("❌ Không tìm thấy user!")
        return

    if not rental_data.is_admin(user_id):
        await update.message.reply_text(f"❌ {user.full_name} không phải admin!")
        return

    rental_data.remove_admin(user_id)
    await update.message.reply_text(f"✅ Đã xóa {user.full_name} khỏi danh sách admin!")

async def listadmins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rental_data.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này!")
        return

    if not rental_data.admins:
        await update.message.reply_text("❌ Chưa có admin nào!")
        return

    text = "👔 DANH SÁCH ADMIN\n\n"
    
    for admin_id in rental_data.admins:
        try:
            user = await context.bot.get_chat(admin_id)
            username = f"@{user.username}" if user.username else "Không có username"
            text += f"👤 {user.full_name}\n"
            text += f"   📧 {username}\n"
            text += f"   🆔 ID: {admin_id}\n\n"
        except:
            text += f"🆔 ID: {admin_id} (không thể lấy thông tin)\n\n"

    await update.message.reply_text(text)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rental_data.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này!")
        return

    stats_data = rental_data.get_all_stats()
    
    text = "📊 THỐNG KÊ HỆ THỐNG\n\n"
    text += f"📺 Tổng số kênh: {stats_data['total_channels']}\n"
    text += f"👥 Tổng số members: {stats_data['total_members']}\n"
    text += f"⏳ Tổng số thuê: {stats_data['total_rentals']}\n"
    text += f"👔 Tổng số admin: {stats_data['total_admins']}\n\n"
    
    text += "📋 CHI TIẾT TỪNG KÊNH:\n\n"
    
    for chat_id, title in rental_data.bot_channels.items():
        member_count = rental_data.get_total_members(chat_id)
        rental_count = len(rental_data.get_all_rentals(chat_id))
        text += f"📺 {title}\n"
        text += f"   👥 Members: {member_count}\n"
        text += f"   ⏳ Đang thuê: {rental_count}\n\n"

    await update.message.reply_text(text)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        if query.data == "back_to_start":
            await show_main_menu(update, context, is_callback=True)

        elif query.data == "main_menu":
            keyboard = []
            for chat_id, title in rental_data.bot_channels.items():
                rental_count = len(rental_data.get_all_rentals(chat_id))
                keyboard.append([InlineKeyboardButton(
                    f"{title} ({rental_count} users)",
                    callback_data=f"channel_{chat_id}"
                )])
            keyboard.append([InlineKeyboardButton("« Quay lại Menu", callback_data="back_to_start")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("📋 Chọn kênh để xem danh sách:", reply_markup=reply_markup)

        elif query.data == "members_menu":
            keyboard = []
            for chat_id, title in rental_data.bot_channels.items():
                member_count = rental_data.get_total_members(chat_id)
                keyboard.append([InlineKeyboardButton(
                    f"{title} ({member_count} members)",
                    callback_data=f"members_{chat_id}"
                )])
            keyboard.append([InlineKeyboardButton("« Quay lại Menu", callback_data="back_to_start")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("👥 Chọn kênh để xem members:", reply_markup=reply_markup)

        elif query.data == "add_time_menu":
            await query.edit_message_text(
                "➕ Thêm thời gian thuê\n\n"
                "Sử dụng lệnh:\n"
                "/settime <time> <@username|id>\n\n"
                "Ví dụ:\n"
                "/settime 1d @username\n"
                "/settime 1w 123456789\n\n"
                "Time: 1d (ngày), 1w (tuần), 1m (tháng), 1y (năm)",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Quay lại Menu", callback_data="back_to_start")
                ]])
            )

        elif query.data == "extend_time_menu":
            await query.edit_message_text(
                "🔄 Gia hạn thời gian thuê\n\n"
                "Sử dụng lệnh:\n"
                "/extendtime <time> <@username|id>\n\n"
                "Ví dụ:\n"
                "/extendtime 1d @username\n"
                "/extendtime 1w 123456789\n\n"
                "Time: 1d (ngày), 1w (tuần), 1m (tháng), 1y (năm)",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Quay lại Menu", callback_data="back_to_start")
                ]])
            )

        elif query.data == "remove_time_menu":
            await query.edit_message_text(
                "🗑️ Xóa thời gian thuê\n\n"
                "Sử dụng lệnh:\n"
                "/removetime <@username|id>\n\n"
                "Ví dụ:\n"
                "/removetime @username\n"
                "/removetime 123456789",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Quay lại Menu", callback_data="back_to_start")
                ]])
            )

        elif query.data == "search_menu":
            await query.edit_message_text(
                "🔍 Tìm kiếm & Tra cứu\n\n"
                "Các lệnh:\n\n"
                "/searchmember <tên|username|id>\n"
                "   Tìm kiếm member\n\n"
                "/memberinfo <@username|id>\n"
                "   Xem thông tin chi tiết member\n\n"
                "/removemember <@username|id>\n"
                "   Xóa member khỏi hệ thống\n\n"
                "/exportmembers\n"
                "   Xuất danh sách members",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Quay lại Menu", callback_data="back_to_start")
                ]])
            )

        elif query.data == "stats_menu":
            stats_data = rental_data.get_all_stats()
            
            text = "📊 THỐNG KÊ HỆ THỐNG\n\n"
            text += f"📺 Tổng số kênh: {stats_data['total_channels']}\n"
            text += f"👥 Tổng số members: {stats_data['total_members']}\n"
            text += f"⏳ Tổng số thuê: {stats_data['total_rentals']}\n"
            text += f"👔 Tổng số admin: {stats_data['total_admins']}\n\n"
            text += "Sử dụng /stats để xem chi tiết"
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Quay lại Menu", callback_data="back_to_start")
                ]])
            )

        elif query.data == "admin_menu":
            await query.edit_message_text(
                "👔 Quản lý Admin\n\n"
                "Các lệnh:\n\n"
                "/addadmin <@username|id>\n"
                "   Thêm admin mới\n\n"
                "/removeadmin <@username|id>\n"
                "   Xóa admin\n\n"
                "/listadmins\n"
                "   Xem danh sách admin",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Quay lại Menu", callback_data="back_to_start")
                ]])
            )

        elif query.data == "help":
            await query.edit_message_text(
                "ℹ️ Hướng dẫn sử dụng Bot\n\n"
                "1️⃣ Mời bot vào channel/group\n"
                "2️⃣ Cấp quyền admin cho bot\n"
                "3️⃣ Nhắn riêng với bot và dùng /start\n"
                "4️⃣ Sử dụng các chức năng:\n\n"
                "📋 Danh sách kênh - Xem user đã thuê\n"
                "👥 Members kênh - Xem tất cả members\n"
                "➕ Thêm thời gian - Đặt time thuê cho user\n"
                "🔄 Gia hạn - Gia hạn thêm thời gian\n"
                "🗑️ Xóa thời gian - Xóa time thuê của user\n"
                "🔍 Tìm kiếm - Tìm kiếm và tra cứu member\n"
                "📊 Thống kê - Xem thống kê hệ thống\n"
                "👔 Quản lý Admin - Quản lý admin bot\n\n"
                "Bot sẽ tự động:\n"
                "• Theo dõi member mới vào kênh\n"
                "• Thông báo khi có user mới\n"
                "• Kick user khi hết hạn thuê",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Quay lại Menu", callback_data="back_to_start")
                ]])
            )

        elif query.data.startswith("channel_"):
            chat_id = int(query.data.split("_")[1])
            rentals = rental_data.get_all_rentals(chat_id)
            
            if not rentals:
                keyboard = [
                    [InlineKeyboardButton("« Quay lại", callback_data="back_to_channels")],
                    [InlineKeyboardButton("🏠 Menu chính", callback_data="back_to_start")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("Kênh này chưa có user thuê.", reply_markup=reply_markup)
                return

            text = f"📺 Kênh: {rental_data.bot_channels.get(chat_id, 'Unknown')}\n\n"
            for user_id, expire_time in rentals.items():
                try:
                    user = await context.bot.get_chat(user_id)
                    username = f"@{user.username}" if user.username else f"ID: {user_id}"
                except:
                    username = f"ID: {user_id}"
                
                time_left = expire_time - datetime.now()
                if time_left.total_seconds() > 0:
                    days = time_left.days
                    hours = time_left.seconds // 3600
                    status = f"⏳ Còn {days}d {hours}h"
                else:
                    status = "⚠️ Hết hạn"
                
                text += f"👤 {username}\n📅 {expire_time.strftime('%Y-%m-%d %H:%M')}\n{status}\n\n"

            keyboard = [
                [InlineKeyboardButton("« Quay lại", callback_data="back_to_channels")],
                [InlineKeyboardButton("🏠 Menu chính", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup)

        elif query.data.startswith("members_"):
            chat_id = int(query.data.split("_")[1])
            members = rental_data.get_members(chat_id)
            
            if not members:
                keyboard = [
                    [InlineKeyboardButton("« Quay lại", callback_data="members_menu")],
                    [InlineKeyboardButton("🏠 Menu chính", callback_data="back_to_start")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("Kênh này chưa có members.", reply_markup=reply_markup)
                return

            text = f"👥 Members: {rental_data.bot_channels.get(chat_id, 'Unknown')}\n\n"
            text += f"Tổng số: {len(members)} members\n\n"
            
            for user_id, info in list(members.items())[:20]:
                text += f"👤 {info.get('full_name', 'N/A')}\n"
                text += f"   📧 {info.get('username', 'N/A')}\n"
                text += f"   🆔 ID: {user_id}\n"
                text += f"   📅 {info.get('join_time', 'N/A')}\n\n"
            
            if len(members) > 20:
                text += f"... và {len(members) - 20} members khác"

            keyboard = [
                [InlineKeyboardButton("« Quay lại", callback_data="members_menu")],
                [InlineKeyboardButton("🏠 Menu chính", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup)

        elif query.data == "back_to_channels":
            keyboard = []
            for chat_id, title in rental_data.bot_channels.items():
                rental_count = len(rental_data.get_all_rentals(chat_id))
                keyboard.append([InlineKeyboardButton(
                    f"{title} ({rental_count} users)",
                    callback_data=f"channel_{chat_id}"
                )])
            keyboard.append([InlineKeyboardButton("« Quay lại Menu", callback_data="back_to_start")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("📋 Chọn kênh để xem danh sách:", reply_markup=reply_markup)

        elif query.data.startswith("settime_"):
            parts = query.data.split("_")
            chat_id = int(parts[1])
            user_id = int(parts[2])
            time_str = parts[3]
            
            duration = parse_time_string(time_str)
            expire_time = datetime.now() + duration
            
            rental_data.add_rental(chat_id, user_id, expire_time)
            
            try:
                user = await context.bot.get_chat(user_id)
                user_name = user.full_name
            except:
                user_name = f"ID: {user_id}"
            
            channel_name = rental_data.bot_channels.get(chat_id, "Unknown")
            
            await query.edit_message_text(
                f"✅ Đã thêm thời gian thuê!\n\n"
                f"👤 User: {user_name}\n"
                f"📺 Kênh: {channel_name}\n"
                f"⏰ Thời gian: {time_str}\n"
                f"📅 Hết hạn: {expire_time.strftime('%Y-%m-%d %H:%M')}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Menu chính", callback_data="back_to_start")
                ]])
            )

        elif query.data.startswith("removetime_"):
            parts = query.data.split("_")
            chat_id = int(parts[1])
            user_id = int(parts[2])
            
            rental_data.remove_rental(chat_id, user_id)
            
            try:
                user = await context.bot.get_chat(user_id)
                user_name = user.full_name
            except:
                user_name = f"ID: {user_id}"
            
            channel_name = rental_data.bot_channels.get(chat_id, "Unknown")
            
            await query.edit_message_text(
                f"✅ Đã xóa thời gian thuê!\n\n"
                f"👤 User: {user_name}\n"
                f"📺 Kênh: {channel_name}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Menu chính", callback_data="back_to_start")
                ]])
            )

        elif query.data.startswith("extendtime_"):
            parts = query.data.split("_")
            chat_id = int(parts[1])
            user_id = int(parts[2])
            time_str = parts[3]
            
            current_expire = rental_data.get_rental(chat_id, user_id)
            if not current_expire:
                await query.edit_message_text(
                    "❌ User này không có thời gian thuê!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🏠 Menu chính", callback_data="back_to_start")
                    ]])
                )
                return
            
            duration = parse_time_string(time_str)
            
            if current_expire > datetime.now():
                new_expire = current_expire + duration
            else:
                new_expire = datetime.now() + duration
            
            rental_data.add_rental(chat_id, user_id, new_expire)
            
            try:
                user = await context.bot.get_chat(user_id)
                user_name = user.full_name
            except:
                user_name = f"ID: {user_id}"
            
            channel_name = rental_data.bot_channels.get(chat_id, "Unknown")
            
            await query.edit_message_text(
                f"✅ Đã gia hạn thời gian!\n\n"
                f"👤 User: {user_name}\n"
                f"📺 Kênh: {channel_name}\n"
                f"⏰ Thêm: {time_str}\n"
                f"📅 Hết hạn mới: {new_expire.strftime('%Y-%m-%d %H:%M')}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Menu chính", callback_data="back_to_start")
                ]])
            )

        elif query.data.startswith("removemember_"):
            parts = query.data.split("_")
            chat_id = int(parts[1])
            user_id = int(parts[2])
            
            rental_data.remove_member(chat_id, user_id)
            
            try:
                user = await context.bot.get_chat(user_id)
                user_name = user.full_name
            except:
                user_name = f"ID: {user_id}"
            
            channel_name = rental_data.bot_channels.get(chat_id, "Unknown")
            
            await query.edit_message_text(
                f"✅ Đã xóa member khỏi hệ thống!\n\n"
                f"👤 User: {user_name}\n"
                f"📺 Kênh: {channel_name}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Menu chính", callback_data="back_to_start")
                ]])
            )

        elif query.data.startswith("export_"):
            if query.data == "export_all":
                text = "📊 DANH SÁCH TẤT CẢ MEMBERS\n\n"
                
                for chat_id, title in rental_data.bot_channels.items():
                    members = rental_data.get_members(chat_id)
                    text += f"📺 {title} ({len(members)} members)\n"
                    text += "="*40 + "\n\n"
                    
                    for user_id, info in members.items():
                        text += f"👤 {info.get('full_name', 'N/A')}\n"
                        text += f"   📧 {info.get('username', 'N/A')}\n"
                        text += f"   🆔 {user_id}\n"
                        text += f"   📅 {info.get('join_time', 'N/A')}\n\n"
                    
                    text += "\n"
            else:
                chat_id = int(query.data.split("_")[1])
                members = rental_data.get_members(chat_id)
                channel_name = rental_data.bot_channels.get(chat_id, "Unknown")
                
                text = f"📊 DANH SÁCH MEMBERS: {channel_name}\n\n"
                text += f"Tổng số: {len(members)} members\n"
                text += "="*40 + "\n\n"
                
                for user_id, info in members.items():
                    text += f"👤 {info.get('full_name', 'N/A')}\n"
                    text += f"   📧 {info.get('username', 'N/A')}\n"
                    text += f"   🆔 {user_id}\n"
                    text += f"   📅 {info.get('join_time', 'N/A')}\n\n"
            
            if len(text) > 4000:
                with open(f"members_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w", encoding="utf-8") as f:
                    f.write(text)
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=open(f"members_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "rb"),
                    caption="📊 File danh sách members"
                )
                await query.edit_message_text(
                    "✅ Đã xuất danh sách members!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🏠 Menu chính", callback_data="back_to_start")
                    ]])
                )
            else:
                await query.edit_message_text(
                    text,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🏠 Menu chính", callback_data="back_to_start")
                    ]])
                )
            
    except Exception as e:
        logger.error(f"Error in button callback: {e}")
        try:
            await query.answer("Đã xảy ra lỗi, vui lòng thử lại!", show_alert=True)
        except:
            pass

async def check_expired_rentals(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    for chat_id in list(rental_data.bot_channels.keys()):
        rentals = rental_data.get_all_rentals(chat_id).copy()
        for user_id, expire_time in rentals.items():
            if now >= expire_time:
                try:
                    await context.bot.ban_chat_member(chat_id, user_id)
                    await context.bot.unban_chat_member(chat_id, user_id)
                    rental_data.remove_rental(chat_id, user_id)
                    logger.info(f"Kicked user {user_id} from chat {chat_id}")
                    
                    for admin_id in rental_data.admins:
                        try:
                            channel_name = rental_data.bot_channels.get(chat_id, "Unknown")
                            user_info = rental_data.get_member_info(chat_id, user_id)
                            user_name = user_info.get('full_name', f'ID: {user_id}') if user_info else f'ID: {user_id}'
                            
                            await context.bot.send_message(
                                chat_id=admin_id,
                                text=f"⚠️ THÔNG BÁO HẾT HẠN\n\n"
                                     f"👤 User: {user_name}\n"
                                     f"📺 Kênh: {channel_name}\n"
                                     f"🆔 ID: {user_id}\n"
                                     f"📅 Đã bị kick do hết hạn thuê"
                            )
                        except Exception as e:
                            logger.error(f"Error notifying admin {admin_id}: {e}")
                            
                except TelegramError as e:
                    logger.error(f"Error kicking user {user_id}: {e}")

async def track_bot_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    my_chat_member = update.my_chat_member
    chat = my_chat_member.chat
    new_status = my_chat_member.new_chat_member.status

    if new_status in ['administrator', 'member']:
        if chat.type in ['channel', 'group', 'supergroup']:
            rental_data.add_channel(chat.id, chat.title)
            logger.info(f"Bot added to {chat.title} (ID: {chat.id})")
            
            for admin_id in rental_data.admins:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"✅ Bot đã được thêm vào kênh mới!\n\n"
                             f"📺 Kênh: {chat.title}\n"
                             f"🆔 ID: {chat.id}"
                    )
                except Exception as e:
                    logger.error(f"Error notifying admin {admin_id}: {e}")
                    
    elif new_status in ['left', 'kicked']:
        rental_data.remove_channel(chat.id)
        logger.info(f"Bot removed from chat {chat.id}")

async def track_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.chat_member:
        return
    
    chat_member_update = update.chat_member
    chat = chat_member_update.chat
    user = chat_member_update.new_chat_member.user
    old_status = chat_member_update.old_chat_member.status
    new_status = chat_member_update.new_chat_member.status
    
    if chat.id not in rental_data.bot_channels:
        return
    
    if old_status in ['left', 'kicked'] and new_status in ['member', 'administrator', 'creator']:
        username = f"@{user.username}" if user.username else "Không có username"
        full_name = user.full_name or "Không có tên"
        join_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        rental_data.add_member(chat.id, user.id, username, full_name, new_status, join_time)
        
        notification_text = (
            f"🔔 THÔNG BÁO MEMBER MỚI\n\n"
            f"📺 Kênh: {chat.title}\n"
            f"👤 Tên: {full_name}\n"
            f"🆔 ID: {user.id}\n"
            f"📧 Username: {username}\n"
            f"🕐 Thời gian: {join_time}\n"
        )
        
        for admin_id in rental_data.admins:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=notification_text
                )
            except Exception as e:
                logger.error(f"Error notifying admin {admin_id}: {e}")
        
        logger.info(f"New member {user.id} joined {chat.title}")
    
    elif new_status in ['member', 'administrator', 'creator'] and old_status in ['member', 'administrator', 'creator']:
        rental_data.update_member_status(chat.id, user.id, new_status)
        logger.info(f"Member {user.id} status updated to {new_status}")
    
    elif old_status in ['member', 'administrator', 'creator'] and new_status in ['left', 'kicked']:
        rental_data.remove_member(chat.id, user.id)
        logger.info(f"Member {user.id} left {chat.title}")

def main():
    TOKEN = "8502835156:AAEgehzrk98kZUEx2rlL0gkovxQYgSnAmsI"
    
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("settime", settime, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("removetime", removetime, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("extendtime", extendtime, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("menu", menu, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("memberinfo", memberinfo, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("searchmember", searchmember, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("removemember", removemember, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("exportmembers", exportmembers, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("addadmin", addadmin, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("removeadmin", removeadmin, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("listadmins", listadmins, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("stats", stats, filters=filters.ChatType.PRIVATE))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(ChatMemberHandler(track_bot_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(ChatMemberHandler(track_chat_members, ChatMemberHandler.CHAT_MEMBER))

    job_queue = application.job_queue
    job_queue.run_repeating(check_expired_rentals, interval=60, first=10)

    logger.info("Bot đang chạy...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()