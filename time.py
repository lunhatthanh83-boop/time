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
    filters
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
            "join_time": join_time
        }
        self.save_data()

    def remove_member(self, chat_id: int, user_id: int):
        if chat_id in self.channel_members and user_id in self.channel_members[chat_id]:
            del self.channel_members[chat_id][user_id]
            self.save_data()

    def get_members(self, chat_id: int) -> Dict[int, dict]:
        return self.channel_members.get(chat_id, {})

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
            InlineKeyboardButton("🗑️ Xóa thời gian", callback_data="remove_time_menu")
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
    rental_data.add_admin(user_id)
    await show_main_menu(update, context, False)

async def settime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rental_data.is_admin(update.effective_user.id):
        await update.message.reply_text("Bạn không có quyền sử dụng lệnh này.")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Sử dụng: /settime <time> <@username|id>\n"
            "Ví dụ: /settime 1d @user hoặc /settime 1w 123456789"
        )
        return

    time_str = context.args[0]
    user_identifier = context.args[1]

    delta = parse_time_string(time_str)
    if not delta:
        await update.message.reply_text("Định dạng thời gian không hợp lệ. Sử dụng: 1d, 1w, 1m, 1y")
        return

    expire_time = datetime.now() + delta

    user_id = None
    if user_identifier.startswith('@'):
        username = user_identifier[1:]
        for chat_id in rental_data.bot_channels.keys():
            try:
                chat = await context.bot.get_chat(chat_id)
                member_count = await context.bot.get_chat_member_count(chat_id)
                if member_count < 200:
                    administrators = await context.bot.get_chat_administrators(chat_id)
                    for member in administrators:
                        if member.user.username == username:
                            user_id = member.user.id
                            break
                if user_id:
                    break
            except:
                continue
        
        if not user_id:
            await update.message.reply_text(f"Không tìm thấy user @{username} trong các kênh bot quản lý.")
            return
    else:
        try:
            user_id = int(user_identifier)
        except ValueError:
            await update.message.reply_text("ID không hợp lệ.")
            return

    added_channels = []
    for chat_id in rental_data.bot_channels.keys():
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status not in ['left', 'kicked']:
                rental_data.add_rental(chat_id, user_id, expire_time)
                added_channels.append(rental_data.bot_channels[chat_id])
        except TelegramError:
            continue

    if added_channels:
        await update.message.reply_text(
            f"Đã đặt thời gian thuê {time_str} cho user {user_identifier}\n"
            f"Hết hạn: {expire_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Trong các kênh: {', '.join(added_channels)}"
        )
    else:
        await update.message.reply_text(f"User {user_identifier} không có trong kênh nào bot quản lý.")

async def removetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rental_data.is_admin(update.effective_user.id):
        await update.message.reply_text("Bạn không có quyền sử dụng lệnh này.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Sử dụng: /removetime <@username|id>")
        return

    user_identifier = context.args[0]
    
    user_id = None
    if user_identifier.startswith('@'):
        username = user_identifier[1:]
        for chat_id in rental_data.bot_channels.keys():
            try:
                administrators = await context.bot.get_chat_administrators(chat_id)
                for member in administrators:
                    if member.user.username == username:
                        user_id = member.user.id
                        break
                if user_id:
                    break
            except:
                continue
    else:
        try:
            user_id = int(user_identifier)
        except ValueError:
            await update.message.reply_text("ID không hợp lệ.")
            return

    if not user_id:
        await update.message.reply_text("Không tìm thấy user.")
        return

    removed_from = []
    for chat_id in list(rental_data.bot_channels.keys()):
        if rental_data.get_rental(chat_id, user_id):
            rental_data.remove_rental(chat_id, user_id)
            removed_from.append(rental_data.bot_channels[chat_id])

    if removed_from:
        await update.message.reply_text(
            f"Đã xóa thời gian thuê của {user_identifier}\n"
            f"Từ các kênh: {', '.join(removed_from)}"
        )
    else:
        await update.message.reply_text(f"User {user_identifier} không có thời gian thuê nào.")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rental_data.is_admin(update.effective_user.id):
        await update.message.reply_text("Bạn không có quyền sử dụng lệnh này.")
        return

    keyboard = []
    for chat_id, title in rental_data.bot_channels.items():
        rental_count = len(rental_data.get_all_rentals(chat_id))
        keyboard.append([InlineKeyboardButton(
            f"{title} ({rental_count} users)",
            callback_data=f"channel_{chat_id}"
        )])

    if not keyboard:
        keyboard = [[InlineKeyboardButton("« Quay lại Menu", callback_data="back_to_start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Bot chưa được thêm vào kênh nào.", reply_markup=reply_markup)
        return

    keyboard.append([InlineKeyboardButton("« Quay lại Menu", callback_data="back_to_start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📋 Chọn kênh để xem danh sách:", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    try:
        await query.answer()
    except:
        pass

    if not rental_data.is_admin(query.from_user.id):
        await query.answer("Bạn không có quyền sử dụng!", show_alert=True)
        return

    try:
        if query.data == "back_to_start":
            await show_main_menu(update, context, True)

        elif query.data == "main_menu":
            keyboard = []
            for chat_id, title in rental_data.bot_channels.items():
                rental_count = len(rental_data.get_all_rentals(chat_id))
                keyboard.append([InlineKeyboardButton(
                    f"{title} ({rental_count} users)",
                    callback_data=f"channel_{chat_id}"
                )])

            if not keyboard:
                keyboard = [[InlineKeyboardButton("« Quay lại Menu", callback_data="back_to_start")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("Bot chưa được thêm vào kênh nào.", reply_markup=reply_markup)
                return

            keyboard.append([InlineKeyboardButton("« Quay lại Menu", callback_data="back_to_start")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("📋 Chọn kênh để xem danh sách:", reply_markup=reply_markup)

        elif query.data == "members_menu":
            keyboard = []
            for chat_id, title in rental_data.bot_channels.items():
                keyboard.append([InlineKeyboardButton(
                    f"👥 {title}",
                    callback_data=f"members_{chat_id}"
                )])

            if not keyboard:
                keyboard = [[InlineKeyboardButton("« Quay lại Menu", callback_data="back_to_start")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("Bot chưa được thêm vào kênh nào.", reply_markup=reply_markup)
                return

            keyboard.append([InlineKeyboardButton("« Quay lại Menu", callback_data="back_to_start")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("👥 Chọn kênh để xem members:", reply_markup=reply_markup)

        elif query.data.startswith("members_"):
            chat_id = int(query.data.split("_")[1])
            
            await query.edit_message_text("⏳ Đang tải thông tin kênh...")
            
            try:
                chat = await context.bot.get_chat(chat_id)
                member_count = await context.bot.get_chat_member_count(chat_id)
                
                admins = []
                regular_members = []
                rental_users = []
                
                administrators = await context.bot.get_chat_administrators(chat_id)
                for member in administrators:
                    user = member.user
                    username = f"@{user.username}" if user.username else "Không có username"
                    full_name = user.full_name or "Không có tên"
                    
                    member_info = f"👤 {full_name}\n   ID: {user.id}\n   {username}"
                    
                    if member.status == "creator":
                        member_info += " [OWNER]"
                    else:
                        member_info += " [ADMIN]"
                    
                    admins.append(member_info)
                
                tracked_members = rental_data.get_members(chat_id)
                for user_id, member_info in tracked_members.items():
                    username = member_info.get('username', 'Không có username')
                    full_name = member_info.get('full_name', 'Không có tên')
                    status = member_info.get('status', 'member')
                    join_time = member_info.get('join_time', 'N/A')
                    
                    if status not in ['creator', 'administrator']:
                        info_text = f"👤 {full_name}\n   ID: {user_id}\n   {username}\n   🕐 Tham gia: {join_time}"
                        regular_members.append(info_text)
                
                rentals = rental_data.get_all_rentals(chat_id)
                for user_id, expire_time in rentals.items():
                    try:
                        user = await context.bot.get_chat(user_id)
                        username = f"@{user.username}" if user.username else "Không có username"
                        full_name = user.full_name or "Không có tên"
                        
                        time_left = expire_time - datetime.now()
                        if time_left.total_seconds() > 0:
                            days = time_left.days
                            hours = time_left.seconds // 3600
                            status = f"⏳ Còn {days}d {hours}h"
                        else:
                            status = "⚠️ Hết hạn"
                        
                        rental_info = f"👤 {full_name}\n   ID: {user_id}\n   {username}\n   {status}"
                        rental_users.append(rental_info)
                    except:
                        rental_info = f"👤 ID: {user_id}\n   ⏳ Còn {(expire_time - datetime.now()).days}d"
                        rental_users.append(rental_info)
                
                text = f"📺 Kênh: {chat.title}\n"
                text += f"📢 Tổng số members: {member_count}\n"
                text += f"👑 Số admin: {len(admins)}\n"
                text += f"👥 Số member thường: {len(regular_members)}\n"
                text += f"🎫 Số user thuê: {len(rental_users)}\n\n"
                
                if admins:
                    text += "═══════════════════\n"
                    text += "👑 DANH SÁCH ADMIN:\n"
                    text += "═══════════════════\n\n"
                    text += "\n\n".join(admins)
                
                if regular_members:
                    text += "\n\n═══════════════════\n"
                    text += "👥 MEMBERS THƯỜNG:\n"
                    text += "═══════════════════\n\n"
                    text += "\n\n".join(regular_members)
                
                if rental_users:
                    text += "\n\n═══════════════════\n"
                    text += "🎫 USER ĐANG THUÊ:\n"
                    text += "═══════════════════\n\n"
                    text += "\n\n".join(rental_users)
                
                if len(text) > 4000:
                    text = text[:3900] + "\n\n... (Danh sách quá dài, chỉ hiển thị một phần)"
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Tải lại", callback_data=f"members_{chat_id}")],
                    [InlineKeyboardButton("« Quay lại", callback_data="back_to_members")],
                    [InlineKeyboardButton("🏠 Menu chính", callback_data="back_to_start")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text, reply_markup=reply_markup)
                
            except Exception as e:
                logger.error(f"Error getting members: {e}")
                keyboard = [
                    [InlineKeyboardButton("🔄 Thử lại", callback_data=f"members_{chat_id}")],
                    [InlineKeyboardButton("« Quay lại", callback_data="back_to_members")],
                    [InlineKeyboardButton("🏠 Menu chính", callback_data="back_to_start")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    f"❌ Không thể lấy thông tin kênh\n\n"
                    f"Lỗi: {str(e)}",
                    reply_markup=reply_markup
                )

        elif query.data == "back_to_members":
            keyboard = []
            for chat_id, title in rental_data.bot_channels.items():
                keyboard.append([InlineKeyboardButton(
                    f"👥 {title}",
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
                "🗑️ Xóa thời gian - Xóa time thuê của user\n\n"
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
    
    elif old_status in ['member', 'administrator', 'creator'] and new_status in ['left', 'kicked']:
        rental_data.remove_member(chat.id, user.id)
        logger.info(f"Member {user.id} left {chat.title}")

def main():
    TOKEN = "8502835156:AAEgehzrk98kZUEx2rlL0gkovxQYgSnAmsI"
    
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("settime", settime, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("removetime", removetime, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("menu", menu, filters=filters.ChatType.PRIVATE))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(ChatMemberHandler(track_bot_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(ChatMemberHandler(track_chat_members, ChatMemberHandler.CHAT_MEMBER))

    job_queue = application.job_queue
    job_queue.run_repeating(check_expired_rentals, interval=60, first=10)

    logger.info("Bot đang chạy...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()