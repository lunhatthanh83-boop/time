import asyncio
import re
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from telegram.error import TelegramError
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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

LANGUAGES = {
    'vi': {
        'start_welcome': "Chào mừng đến với Bot Quản Lý Thuê Kênh!\n\n"
                        "User ID: {user_id}\n"
                        "Admin: {is_admin}\n\n"
                        "Vui lòng chọn ngôn ngữ / Please select language:",
        'language_selected': "Đã chọn ngôn ngữ: Tiếng Việt",
        'select_language': "Chọn ngôn ngữ của bạn:",
        'menu_title': "MENU QUẢN LÝ\n\nVui lòng chọn chức năng:",
        'admin_menu_title': "MENU ADMIN\n\nChọn chức năng quản trị:",
        'user_menu_title': "MENU NGƯỜI DÙNG\n\nChọn chức năng:",
        'check_time': "Kiểm tra thời gian",
        'check_time_info': "THÔNG TIN THUÊ KÊNH\n\n"
                          "User: {user_name}\n"
                          "ID: {user_id}\n\n",
        'no_rentals': "Bạn chưa thuê kênh nào hoặc đã hết hạn.",
        'channel': "Kênh",
        'expire_time': "Hết hạn",
        'time_left': "Còn lại",
        'expired': "ĐÃ HẾT HẠN",
        'days': "ngày",
        'hours': "giờ",
        'minutes': "phút",
        'set_time': "Set thời gian",
        'remove_time': "Xóa thời gian",
        'extend_time': "Gia hạn thêm",
        'member_management': "Quản lý members",
        'admin_management': "Quản lý admins",
        'statistics': "Thống kê",
        'need_admin': "BẠN KHÔNG CÓ ĐỦ QUYỀN HẠN!\n\n"
                     "Chức năng này chỉ dành cho quản trị viên.\n"
                     "Vui lòng liên hệ admin nếu bạn cần hỗ trợ.",
        'admin_only': "Chỉ admin mới có thể thực hiện thao tác này!",
        'back_to_menu': "Quay lại menu",
        'back_to_main': "Menu chính",
        'admin_menu': "Menu Admin",
        'success': "Thành công!",
        'error': "Lỗi!",
        'confirm': "Xác nhận",
        'cancel': "Hủy",
        'help_text': "TRỢ GIÚP\n\n"
                    "Sử dụng menu để thao tác với bot\n"
                    "Chọn các button trong menu để sử dụng các chức năng.",
        'member_info': "Thông tin member",
        'search_member': "Tìm kiếm member",
        'export_members': "Xuất danh sách",
        'list_admins': "Danh sách admins",
        'add_admin': "Thêm admin",
        'remove_admin': "Xóa admin",
        'language_btn': "Ngôn ngữ",
        'vietnamese': "Tiếng Việt",
        'english': "English",
        'select_channel': "Chọn kênh:",
        'no_channels': "Chưa có kênh nào được thêm vào bot!",
        'select_member': "Chọn member:",
        'no_members': "Chưa có member nào trong kênh này!",
        'enter_days': "Nhập số ngày:",
        'send_days': "Gửi số ngày (VD: 30):",
        'member_selected': "Đã chọn member:",
        'channel_members': "Danh sách members trong {channel}:",
        'view_more_members': "Xem thêm ({remaining} members)",
        'back_to_channels': "Quay lại danh sách kênh",
    },
    'en': {
        'start_welcome': "Welcome to Channel Rental Management Bot!\n\n"
                        "User ID: {user_id}\n"
                        "Admin: {is_admin}\n\n"
                        "Vui lòng chọn ngôn ngữ / Please select language:",
        'language_selected': "Language selected: English",
        'select_language': "Select your language:",
        'menu_title': "MANAGEMENT MENU\n\nPlease select a function:",
        'admin_menu_title': "ADMIN MENU\n\nSelect admin function:",
        'user_menu_title': "USER MENU\n\nSelect function:",
        'check_time': "Check Time",
        'check_time_info': "RENTAL INFORMATION\n\n"
                          "User: {user_name}\n"
                          "ID: {user_id}\n\n",
        'no_rentals': "You haven't rented any channel or it has expired.",
        'channel': "Channel",
        'expire_time': "Expires",
        'time_left': "Time left",
        'expired': "EXPIRED",
        'days': "days",
        'hours': "hours",
        'minutes': "minutes",
        'set_time': "Set Time",
        'remove_time': "Remove Time",
        'extend_time': "Extend Time",
        'member_management': "Member Management",
        'admin_management': "Admin Management",
        'statistics': "Statistics",
        'need_admin': "INSUFFICIENT PERMISSIONS!\n\n"
                     "This function is only for administrators.\n"
                     "Please contact admin if you need support.",
        'admin_only': "Only admins can perform this action!",
        'back_to_menu': "Back to menu",
        'back_to_main': "Main Menu",
        'admin_menu': "Admin Menu",
        'success': "Success!",
        'error': "Error!",
        'confirm': "Confirm",
        'cancel': "Cancel",
        'help_text': "HELP\n\n"
                    "Use menu to interact with bot\n"
                    "Select buttons in the menu to use functions.",
        'member_info': "Member Info",
        'search_member': "Search Member",
        'export_members': "Export List",
        'list_admins': "List Admins",
        'add_admin': "Add Admin",
        'remove_admin': "Remove Admin",
        'language_btn': "Language",
        'vietnamese': "Tiếng Việt",
        'english': "English",
        'select_channel': "Select channel:",
        'no_channels': "No channels added to bot yet!",
        'select_member': "Select member:",
        'no_members': "No members in this channel!",
        'enter_days': "Enter number of days:",
        'send_days': "Send number of days (e.g., 30):",
        'member_selected': "Member selected:",
        'channel_members': "Member list in {channel}:",
        'view_more_members': "View more ({remaining} members)",
        'back_to_channels': "Back to channel list",
    }
}

class RentalData:
    def __init__(self):
        self.rentals: Dict[int, Dict[int, datetime]] = {}
        self.admins: List[int] = []
        self.bot_channels: Dict[int, str] = {}
        self.channel_members: Dict[int, Dict[int, dict]] = {}
        self.user_languages: Dict[int, str] = {}
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
            },
            "user_languages": {str(k): v for k, v in self.user_languages.items()}
        }
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    def load_data(self):
        if not os.path.exists(self.data_file):
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
            self.user_languages = {int(k): v for k, v in data.get("user_languages", {}).items()}
        except Exception as e:
            logger.error(f"Error loading data: {e}")

    def set_rental(self, chat_id: int, user_id: int, expire_time: datetime):
        if chat_id not in self.rentals:
            self.rentals[chat_id] = {}
        self.rentals[chat_id][user_id] = expire_time
        self.save_data()

    def get_rental(self, chat_id: int, user_id: int) -> Optional[datetime]:
        return self.rentals.get(chat_id, {}).get(user_id)

    def remove_rental(self, chat_id: int, user_id: int):
        if chat_id in self.rentals and user_id in self.rentals[chat_id]:
            del self.rentals[chat_id][user_id]
            if not self.rentals[chat_id]:
                del self.rentals[chat_id]
            self.save_data()

    def get_all_rentals(self, chat_id: int) -> Dict[int, datetime]:
        return self.rentals.get(chat_id, {})

    def add_admin(self, user_id: int):
        if user_id not in self.admins:
            self.admins.append(user_id)
            self.save_data()

    def remove_admin(self, user_id: int):
        if user_id in self.admins:
            self.admins.remove(user_id)
            self.save_data()

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admins

    def add_channel(self, chat_id: int, channel_name: str):
        self.bot_channels[chat_id] = channel_name
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
            'username': username,
            'full_name': full_name,
            'status': status,
            'join_time': join_time
        }
        self.save_data()

    def remove_member(self, chat_id: int, user_id: int):
        if chat_id in self.channel_members and user_id in self.channel_members[chat_id]:
            del self.channel_members[chat_id][user_id]
            self.save_data()

    def get_member_info(self, chat_id: int, user_id: int) -> Optional[dict]:
        return self.channel_members.get(chat_id, {}).get(user_id)

    def update_member_status(self, chat_id: int, user_id: int, status: str):
        if chat_id in self.channel_members and user_id in self.channel_members[chat_id]:
            self.channel_members[chat_id][user_id]['status'] = status
            self.save_data()

    def get_all_members(self, chat_id: int) -> Dict[int, dict]:
        return self.channel_members.get(chat_id, {})

    def set_user_language(self, user_id: int, language: str):
        self.user_languages[user_id] = language
        self.save_data()

    def get_user_language(self, user_id: int) -> str:
        return self.user_languages.get(user_id, 'vi')

rental_data = RentalData()

user_states = {}

def t(uid: int, key: str) -> str:
    lang = rental_data.get_user_language(uid)
    return LANGUAGES.get(lang, LANGUAGES['vi']).get(key, key)

def format_member_display(member_info: dict, user_id: int, rental_info: Optional[datetime] = None) -> str:
    """Format member info for button display"""
    name = member_info['full_name'][:20]  # Limit length
    username = member_info['username']
    
    if rental_info:
        time_left = rental_info - datetime.now()
        if time_left.total_seconds() > 0:
            days = time_left.days
            hours = time_left.seconds // 3600
            status = f"⏰ {days}d {hours}h"
        else:
            status = "❌ HẾT HẠN"
    else:
        status = "⚠️ Chưa set"
    
    return f"{name} | {status}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    is_admin = rental_data.is_admin(uid)
    
    keyboard = [
        [
            InlineKeyboardButton("Tiếng Việt 🇻🇳", callback_data='lang_vi'),
            InlineKeyboardButton("English 🇺🇸", callback_data='lang_en')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    lang = rental_data.get_user_language(uid)
    welcome_text = LANGUAGES[lang]['start_welcome'].format(
        user_id=uid,
        is_admin="Yes" if is_admin else "No"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = update.effective_user.id
    
    if query:
        await query.answer()
    
    is_admin = rental_data.is_admin(uid)
    
    if is_admin:
        keyboard = [
            [InlineKeyboardButton(t(uid, 'check_time'), callback_data='check_time')],
            [InlineKeyboardButton(t(uid, 'set_time'), callback_data='set_time')],
            [InlineKeyboardButton(t(uid, 'extend_time'), callback_data='extend_time')],
            [InlineKeyboardButton(t(uid, 'remove_time'), callback_data='remove_time')],
            [InlineKeyboardButton(t(uid, 'member_management'), callback_data='member_menu')],
            [InlineKeyboardButton(t(uid, 'admin_management'), callback_data='admin_menu')],
            [InlineKeyboardButton(t(uid, 'statistics'), callback_data='statistics')],
            [InlineKeyboardButton(t(uid, 'language_btn'), callback_data='language')]
        ]
        title = t(uid, 'admin_menu_title')
    else:
        keyboard = [
            [InlineKeyboardButton(t(uid, 'check_time'), callback_data='check_time')],
            [InlineKeyboardButton(t(uid, 'language_btn'), callback_data='language')]
        ]
        title = t(uid, 'user_menu_title')
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(title, reply_markup=reply_markup)
    else:
        await update.message.reply_text(title, reply_markup=reply_markup)

async def checktime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = update.effective_user.id
    user_name = update.effective_user.full_name
    
    if query:
        await query.answer()
    
    lang = rental_data.get_user_language(uid)
    response = LANGUAGES[lang]['check_time_info'].format(user_name=user_name, user_id=uid)
    
    has_rentals = False
    for chat_id, channel_name in rental_data.bot_channels.items():
        expire_time = rental_data.get_rental(chat_id, uid)
        if expire_time:
            has_rentals = True
            time_left = expire_time - datetime.now()
            
            if time_left.total_seconds() > 0:
                days = time_left.days
                hours = time_left.seconds // 3600
                minutes = (time_left.seconds % 3600) // 60
                
                time_str = ""
                if days > 0:
                    time_str += f"{days} {t(uid, 'days')} "
                if hours > 0:
                    time_str += f"{hours} {t(uid, 'hours')} "
                if minutes > 0:
                    time_str += f"{minutes} {t(uid, 'minutes')}"
                
                response += f"\n{t(uid, 'channel')}: {channel_name}\n"
                response += f"{t(uid, 'expire_time')}: {expire_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                response += f"{t(uid, 'time_left')}: {time_str}\n"
            else:
                response += f"\n{t(uid, 'channel')}: {channel_name}\n"
                response += f"{t(uid, 'expired')}\n"
    
    if not has_rentals:
        response += t(uid, 'no_rentals')
    
    keyboard = [[InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(response, reply_markup=reply_markup)
    else:
        await update.message.reply_text(response, reply_markup=reply_markup)

async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = update.effective_user.id
    
    if query:
        await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton(t(uid, 'vietnamese'), callback_data='lang_vi'),
            InlineKeyboardButton(t(uid, 'english'), callback_data='lang_en')
        ],
        [InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = t(uid, 'select_language')
    
    if query:
        await query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    help_text = t(uid, 'help_text')
    
    keyboard = [[InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(help_text, reply_markup=reply_markup)

async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    if not rental_data.is_admin(uid):
        await update.message.reply_text(t(uid, 'need_admin'))
        return

    if len(context.args) != 1:
        await update.message.reply_text("Format: /addadmin [user_id]")
        return

    try:
        new_admin_id = int(context.args[0])
        rental_data.add_admin(new_admin_id)
        await update.message.reply_text(f"{t(uid, 'success')} Added admin: {new_admin_id}")
    except ValueError:
        await update.message.reply_text("Invalid user ID!")

async def removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    if not rental_data.is_admin(uid):
        await update.message.reply_text(t(uid, 'need_admin'))
        return

    if len(context.args) != 1:
        await update.message.reply_text("Format: /removeadmin [user_id]")
        return

    try:
        remove_admin_id = int(context.args[0])
        rental_data.remove_admin(remove_admin_id)
        await update.message.reply_text(f"{t(uid, 'success')} Removed admin: {remove_admin_id}")
    except ValueError:
        await update.message.reply_text("Invalid user ID!")

async def listadmins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    if not rental_data.is_admin(uid):
        await update.message.reply_text(t(uid, 'need_admin'))
        return

    if not rental_data.admins:
        await update.message.reply_text("No admins found!")
        return
    
    admin_list = "\n".join([f"• {admin_id}" for admin_id in rental_data.admins])
    await update.message.reply_text(f"ADMIN LIST:\n\n{admin_list}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    if not rental_data.is_admin(uid):
        await update.message.reply_text(t(uid, 'need_admin'))
        return

    total_channels = len(rental_data.bot_channels)
    total_rentals = sum(len(users) for users in rental_data.rentals.values())
    total_members = sum(len(members) for members in rental_data.channel_members.values())
    
    stats_text = (
        f"STATISTICS\n\n"
        f"Channels: {total_channels}\n"
        f"Active Rentals: {total_rentals}\n"
        f"Total Members: {total_members}\n"
        f"Admins: {len(rental_data.admins)}"
    )
    
    await update.message.reply_text(stats_text)

async def exportmembers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    if not rental_data.is_admin(uid):
        await update.message.reply_text(t(uid, 'need_admin'))
        return

    if len(context.args) != 1:
        await update.message.reply_text("Format: /exportmembers [channel_id]")
        return

    try:
        chat_id = int(context.args[0])
        members = rental_data.get_all_members(chat_id)
        
        if not members:
            await update.message.reply_text("No members found!")
            return
        
        channel_name = rental_data.bot_channels.get(chat_id, "Unknown")
        filename = f"members_{chat_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"MEMBER LIST - {channel_name}\n")
            f.write(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Members: {len(members)}\n\n")
            f.write("="*80 + "\n\n")
            
            for member_id, info in members.items():
                f.write(f"Name: {info['full_name']}\n")
                f.write(f"Username: {info['username']}\n")
                f.write(f"ID: {member_id}\n")
                f.write(f"Status: {info['status']}\n")
                f.write(f"Join Time: {info['join_time']}\n")
                
                # Add rental info
                rental = rental_data.get_rental(chat_id, member_id)
                if rental:
                    time_left = rental - datetime.now()
                    if time_left.total_seconds() > 0:
                        f.write(f"Rental Expires: {rental.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"Time Left: {time_left.days} days\n")
                    else:
                        f.write(f"Rental: EXPIRED\n")
                else:
                    f.write(f"Rental: Not set\n")
                
                f.write("-"*80 + "\n")
        
        with open(filename, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=filename,
                caption=f"Member list for {channel_name}"
            )
        
        os.remove(filename)
        
    except ValueError:
        await update.message.reply_text("Invalid channel ID!")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    uid = update.effective_user.id
    callback_data = query.data
    
    # Language selection
    if callback_data.startswith('lang_'):
        lang_code = callback_data.split('_')[1]
        rental_data.set_user_language(uid, lang_code)
        
        await query.edit_message_text(
            text=t(uid, 'language_selected'),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')
            ]])
        )
        return
    
    # Main menu
    if callback_data == 'main_menu':
        if uid in user_states:
            del user_states[uid]
        await menu(update, context)
        return
    
    if callback_data == 'check_time':
        await checktime(update, context)
        return
    
    if callback_data == 'language':
        await language(update, context)
        return
    
    # SET TIME workflow
    if callback_data == 'set_time':
        if not rental_data.is_admin(uid):
            await query.edit_message_text(t(uid, 'need_admin'))
            return
        
        if not rental_data.bot_channels:
            await query.edit_message_text(
                t(uid, 'no_channels'),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')
                ]])
            )
            return
        
        keyboard = []
        for chat_id, channel_name in rental_data.bot_channels.items():
            members_count = len(rental_data.get_all_members(chat_id))
            keyboard.append([InlineKeyboardButton(
                f"{channel_name} ({members_count} members)", 
                callback_data=f'settime_ch_{chat_id}'
            )])
        keyboard.append([InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')])
        
        await query.edit_message_text(
            t(uid, 'select_channel'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if callback_data.startswith('settime_ch_'):
        chat_id = int(callback_data.split('_')[2])
        members = rental_data.get_all_members(chat_id)
        
        if not members:
            await query.edit_message_text(
                t(uid, 'no_members'),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')
                ]])
            )
            return
        
        channel_name = rental_data.bot_channels.get(chat_id, "Unknown")
        keyboard = []
        
        # Show members with pagination (10 per page)
        member_list = list(members.items())
        page = 0
        page_size = 10
        start_idx = page * page_size
        end_idx = start_idx + page_size
        
        for member_id, info in member_list[start_idx:end_idx]:
            rental = rental_data.get_rental(chat_id, member_id)
            display_text = format_member_display(info, member_id, rental)
            keyboard.append([InlineKeyboardButton(
                display_text,
                callback_data=f'settime_mb_{chat_id}_{member_id}'
            )])
        
        # Add navigation buttons if needed
        if len(member_list) > end_idx:
            remaining = len(member_list) - end_idx
            keyboard.append([InlineKeyboardButton(
                t(uid, 'view_more_members').format(remaining=remaining),
                callback_data=f'settime_pg_{chat_id}_{page+1}'
            )])
        
        keyboard.append([InlineKeyboardButton(t(uid, 'back_to_channels'), callback_data='set_time')])
        
        await query.edit_message_text(
            t(uid, 'channel_members').format(channel=channel_name) + "\n\n" + t(uid, 'select_member'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if callback_data.startswith('settime_mb_'):
        parts = callback_data.split('_')
        chat_id = int(parts[2])
        member_id = int(parts[3])
        
        user_states[uid] = {'action': 'set_time', 'chat_id': chat_id, 'member_id': member_id}
        
        member_info = rental_data.get_member_info(chat_id, member_id)
        channel_name = rental_data.bot_channels.get(chat_id, "Unknown")
        
        await query.edit_message_text(
            f"{t(uid, 'member_selected')}\n\n"
            f"Kênh: {channel_name}\n"
            f"Tên: {member_info['full_name']}\n"
            f"ID: {member_id}\n\n"
            f"{t(uid, 'send_days')}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(uid, 'cancel'), callback_data='main_menu')
            ]])
        )
        return
    
    # EXTEND TIME workflow
    if callback_data == 'extend_time':
        if not rental_data.is_admin(uid):
            await query.edit_message_text(t(uid, 'need_admin'))
            return
        
        if not rental_data.bot_channels:
            await query.edit_message_text(
                t(uid, 'no_channels'),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')
                ]])
            )
            return
        
        keyboard = []
        for chat_id, channel_name in rental_data.bot_channels.items():
            members_count = len(rental_data.get_all_members(chat_id))
            keyboard.append([InlineKeyboardButton(
                f"{channel_name} ({members_count} members)", 
                callback_data=f'extend_ch_{chat_id}'
            )])
        keyboard.append([InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')])
        
        await query.edit_message_text(
            t(uid, 'select_channel'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if callback_data.startswith('extend_ch_'):
        chat_id = int(callback_data.split('_')[2])
        members = rental_data.get_all_members(chat_id)
        
        if not members:
            await query.edit_message_text(
                t(uid, 'no_members'),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')
                ]])
            )
            return
        
        channel_name = rental_data.bot_channels.get(chat_id, "Unknown")
        keyboard = []
        
        for member_id, info in members.items():
            rental = rental_data.get_rental(chat_id, member_id)
            display_text = format_member_display(info, member_id, rental)
            keyboard.append([InlineKeyboardButton(
                display_text,
                callback_data=f'extend_mb_{chat_id}_{member_id}'
            )])
        
        keyboard.append([InlineKeyboardButton(t(uid, 'back_to_channels'), callback_data='extend_time')])
        
        await query.edit_message_text(
            t(uid, 'channel_members').format(channel=channel_name) + "\n\n" + t(uid, 'select_member'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if callback_data.startswith('extend_mb_'):
        parts = callback_data.split('_')
        chat_id = int(parts[2])
        member_id = int(parts[3])
        
        user_states[uid] = {'action': 'extend_time', 'chat_id': chat_id, 'member_id': member_id}
        
        member_info = rental_data.get_member_info(chat_id, member_id)
        channel_name = rental_data.bot_channels.get(chat_id, "Unknown")
        
        current_rental = rental_data.get_rental(chat_id, member_id)
        rental_text = ""
        if current_rental:
            time_left = current_rental - datetime.now()
            if time_left.total_seconds() > 0:
                rental_text = f"Thời hạn hiện tại: {current_rental.strftime('%Y-%m-%d %H:%M:%S')}\n"
                rental_text += f"Còn lại: {time_left.days} ngày {time_left.seconds // 3600} giờ\n\n"
            else:
                rental_text = f"Trạng thái: ĐÃ HẾT HẠN\n\n"
        else:
            rental_text = "Chưa có thời hạn thuê\n\n"
        
        await query.edit_message_text(
            f"{t(uid, 'member_selected')}\n\n"
            f"Kênh: {channel_name}\n"
            f"Tên: {member_info['full_name']}\n"
            f"ID: {member_id}\n"
            f"{rental_text}"
            f"{t(uid, 'send_days')}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(uid, 'cancel'), callback_data='main_menu')
            ]])
        )
        return
    
    # REMOVE TIME workflow
    if callback_data == 'remove_time':
        if not rental_data.is_admin(uid):
            await query.edit_message_text(t(uid, 'need_admin'))
            return
        
        if not rental_data.bot_channels:
            await query.edit_message_text(
                t(uid, 'no_channels'),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')
                ]])
            )
            return
        
        keyboard = []
        for chat_id, channel_name in rental_data.bot_channels.items():
            members_count = len(rental_data.get_all_members(chat_id))
            keyboard.append([InlineKeyboardButton(
                f"{channel_name} ({members_count} members)", 
                callback_data=f'remove_ch_{chat_id}'
            )])
        keyboard.append([InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')])
        
        await query.edit_message_text(
            t(uid, 'select_channel'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if callback_data.startswith('remove_ch_'):
        chat_id = int(callback_data.split('_')[2])
        members = rental_data.get_all_members(chat_id)
        
        if not members:
            await query.edit_message_text(
                t(uid, 'no_members'),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')
                ]])
            )
            return
        
        channel_name = rental_data.bot_channels.get(chat_id, "Unknown")
        keyboard = []
        
        for member_id, info in members.items():
            rental = rental_data.get_rental(chat_id, member_id)
            display_text = format_member_display(info, member_id, rental)
            keyboard.append([InlineKeyboardButton(
                display_text,
                callback_data=f'remove_mb_{chat_id}_{member_id}'
            )])
        
        keyboard.append([InlineKeyboardButton(t(uid, 'back_to_channels'), callback_data='remove_time')])
        
        await query.edit_message_text(
            t(uid, 'channel_members').format(channel=channel_name) + "\n\n" + t(uid, 'select_member'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if callback_data.startswith('remove_mb_'):
        parts = callback_data.split('_')
        chat_id = int(parts[2])
        member_id = int(parts[3])
        
        member_info = rental_data.get_member_info(chat_id, member_id)
        channel_name = rental_data.bot_channels.get(chat_id, "Unknown")
        
        # Confirm before removing
        keyboard = [
            [InlineKeyboardButton("✅ XÁC NHẬN XÓA", callback_data=f'confirm_remove_{chat_id}_{member_id}')],
            [InlineKeyboardButton(t(uid, 'cancel'), callback_data=f'remove_ch_{chat_id}')]
        ]
        
        await query.edit_message_text(
            f"⚠️ XÁC NHẬN XÓA THỜI GIAN ⚠️\n\n"
            f"Kênh: {channel_name}\n"
            f"Tên: {member_info['full_name']}\n"
            f"ID: {member_id}\n\n"
            f"User sẽ bị kick khỏi kênh!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if callback_data.startswith('confirm_remove_'):
        parts = callback_data.split('_')
        chat_id = int(parts[2])
        member_id = int(parts[3])
        
        # Remove rental and kick user
        rental_data.remove_rental(chat_id, member_id)
        
        try:
            await context.bot.ban_chat_member(chat_id, member_id)
            await context.bot.unban_chat_member(chat_id, member_id)
        except Exception as e:
            logger.error(f"Error kicking user: {e}")
        
        channel_name = rental_data.bot_channels.get(chat_id, "Unknown")
        await query.edit_message_text(
            f"{t(uid, 'success')}\n\n"
            f"Đã xóa thời gian và kick user\n"
            f"User ID: {member_id}\n"
            f"Kênh: {channel_name}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')
            ]])
        )
        return
    
    # MEMBER INFO workflow
    if callback_data == 'member_menu':
        if not rental_data.is_admin(uid):
            await query.edit_message_text(t(uid, 'need_admin'))
            return
        
        keyboard = [
            [InlineKeyboardButton(t(uid, 'member_info'), callback_data='member_info_select')],
            [InlineKeyboardButton(t(uid, 'export_members'), callback_data='export_select')],
            [InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')]
        ]
        await query.edit_message_text(
            "MEMBER MANAGEMENT\n\nSelect function:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if callback_data == 'member_info_select':
        if not rental_data.bot_channels:
            await query.edit_message_text(
                t(uid, 'no_channels'),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')
                ]])
            )
            return
        
        keyboard = []
        for chat_id, channel_name in rental_data.bot_channels.items():
            members_count = len(rental_data.get_all_members(chat_id))
            keyboard.append([InlineKeyboardButton(
                f"{channel_name} ({members_count} members)", 
                callback_data=f'meminfo_ch_{chat_id}'
            )])
        keyboard.append([InlineKeyboardButton(t(uid, 'back_to_menu'), callback_data='member_menu')])
        
        await query.edit_message_text(
            t(uid, 'select_channel'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if callback_data.startswith('meminfo_ch_'):
        chat_id = int(callback_data.split('_')[2])
        members = rental_data.get_all_members(chat_id)
        
        if not members:
            await query.edit_message_text(
                t(uid, 'no_members'),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')
                ]])
            )
            return
        
        channel_name = rental_data.bot_channels.get(chat_id, "Unknown")
        keyboard = []
        
        for member_id, info in members.items():
            rental = rental_data.get_rental(chat_id, member_id)
            display_text = format_member_display(info, member_id, rental)
            keyboard.append([InlineKeyboardButton(
                display_text,
                callback_data=f'meminfo_mb_{chat_id}_{member_id}'
            )])
        
        keyboard.append([InlineKeyboardButton(t(uid, 'back_to_channels'), callback_data='member_info_select')])
        
        await query.edit_message_text(
            t(uid, 'channel_members').format(channel=channel_name) + "\n\n" + t(uid, 'select_member'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if callback_data.startswith('meminfo_mb_'):
        parts = callback_data.split('_')
        chat_id = int(parts[2])
        member_id = int(parts[3])
        
        member_info = rental_data.get_member_info(chat_id, member_id)
        channel_name = rental_data.bot_channels.get(chat_id, "Unknown")
        rental = rental_data.get_rental(chat_id, member_id)
        
        info_text = (
            f"📋 MEMBER INFO\n\n"
            f"Kênh: {channel_name}\n"
            f"Tên: {member_info['full_name']}\n"
            f"Username: {member_info['username']}\n"
            f"ID: {member_id}\n"
            f"Trạng thái: {member_info['status']}\n"
            f"Ngày join: {member_info['join_time']}\n\n"
        )
        
        if rental:
            time_left = rental - datetime.now()
            if time_left.total_seconds() > 0:
                days = time_left.days
                hours = time_left.seconds // 3600
                info_text += f"⏰ THỜI GIAN THUÊ\n"
                info_text += f"Hết hạn: {rental.strftime('%Y-%m-%d %H:%M:%S')}\n"
                info_text += f"Còn lại: {days} ngày {hours} giờ"
            else:
                info_text += f"❌ ĐÃ HẾT HẠN\n"
                info_text += f"Đã hết hạn: {rental.strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            info_text += "⚠️ Chưa set thời gian thuê"
        
        await query.edit_message_text(
            info_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(uid, 'back_to_channels'), callback_data=f'meminfo_ch_{chat_id}')
            ]])
        )
        return
    
    # Export members
    if callback_data == 'export_select':
        if not rental_data.bot_channels:
            await query.edit_message_text(
                t(uid, 'no_channels'),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')
                ]])
            )
            return
        
        await query.edit_message_text(
            "Sử dụng command:\n/exportmembers [channel_id]\n\nVí dụ: /exportmembers -1001234567890",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(uid, 'back_to_menu'), callback_data='member_menu')
            ]])
        )
        return
    
    # Admin menu
    if callback_data == 'admin_menu':
        if not rental_data.is_admin(uid):
            await query.edit_message_text(t(uid, 'need_admin'))
            return
        
        keyboard = [
            [InlineKeyboardButton(t(uid, 'list_admins'), callback_data='list_admins')],
            [InlineKeyboardButton(t(uid, 'add_admin'), callback_data='add_admin')],
            [InlineKeyboardButton(t(uid, 'remove_admin'), callback_data='remove_admin')],
            [InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')]
        ]
        await query.edit_message_text(
            t(uid, 'admin_menu_title'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if callback_data == 'list_admins':
        if not rental_data.admins:
            text = "No admins found!"
        else:
            text = "ADMIN LIST:\n\n"
            for admin_id in rental_data.admins:
                text += f"• {admin_id}\n"
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(t(uid, 'back_to_menu'), callback_data='admin_menu')
        ]])
        await query.edit_message_text(text, reply_markup=keyboard)
        return
    
    if callback_data in ['add_admin', 'remove_admin']:
        text = f"Use: /addadmin [user_id]" if callback_data == 'add_admin' else f"Use: /removeadmin [user_id]"
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(t(uid, 'back_to_menu'), callback_data='admin_menu')
        ]])
        await query.edit_message_text(text, reply_markup=keyboard)
        return
    
    # Statistics
    if callback_data == 'statistics':
        if not rental_data.is_admin(uid):
            await query.edit_message_text(t(uid, 'need_admin'))
            return
        
        total_channels = len(rental_data.bot_channels)
        total_rentals = sum(len(users) for users in rental_data.rentals.values())
        total_members = sum(len(members) for members in rental_data.channel_members.values())
        
        stats_text = (
            f"📊 STATISTICS\n\n"
            f"Channels: {total_channels}\n"
            f"Active Rentals: {total_rentals}\n"
            f"Total Members: {total_members}\n"
            f"Admins: {len(rental_data.admins)}"
        )
        
        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')
            ]])
        )
        return

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    if uid not in user_states:
        return
    
    state = user_states[uid]
    action = state.get('action')
    chat_id = state.get('chat_id')
    member_id = state.get('member_id')
    
    text = update.message.text.strip()
    
    try:
        if action in ['set_time', 'extend_time']:
            days = int(text)
            
            if action == 'set_time':
                expire_time = datetime.now() + timedelta(days=days)
                rental_data.set_rental(chat_id, member_id, expire_time)
                
                member_info = rental_data.get_member_info(chat_id, member_id)
                channel_name = rental_data.bot_channels.get(chat_id, "Unknown")
                
                await update.message.reply_text(
                    f"{t(uid, 'success')}\n\n"
                    f"User: {member_info['full_name']}\n"
                    f"ID: {member_id}\n"
                    f"Kênh: {channel_name}\n"
                    f"Số ngày: {days}\n"
                    f"Hết hạn: {expire_time.strftime('%Y-%m-%d %H:%M:%S')}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')
                    ]])
                )
            
            elif action == 'extend_time':
                current_expire = rental_data.get_rental(chat_id, member_id)
                if not current_expire:
                    # If no current rental, set new one
                    new_expire = datetime.now() + timedelta(days=days)
                else:
                    # Extend from current expiry
                    new_expire = current_expire + timedelta(days=days)
                
                rental_data.set_rental(chat_id, member_id, new_expire)
                
                member_info = rental_data.get_member_info(chat_id, member_id)
                channel_name = rental_data.bot_channels.get(chat_id, "Unknown")
                
                await update.message.reply_text(
                    f"{t(uid, 'success')}\n\n"
                    f"User: {member_info['full_name']}\n"
                    f"ID: {member_id}\n"
                    f"Kênh: {channel_name}\n"
                    f"Đã gia hạn thêm {days} ngày\n"
                    f"Hết hạn mới: {new_expire.strftime('%Y-%m-%d %H:%M:%S')}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(t(uid, 'back_to_main'), callback_data='main_menu')
                    ]])
                )
            
            del user_states[uid]
            
    except ValueError:
        await update.message.reply_text(
            f"{t(uid, 'error')} Vui lòng nhập số ngày hợp lệ!"
        )
    except Exception as e:
        await update.message.reply_text(
            f"{t(uid, 'error')} {str(e)}"
        )
        if uid in user_states:
            del user_states[uid]

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
                                text=f"⏰ EXPIRY NOTIFICATION\n\n"
                                     f"User: {user_name}\n"
                                     f"Channel: {channel_name}\n"
                                     f"ID: {user_id}\n"
                                     f"Kicked due to rental expiry"
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
                        text=f"🆕 Bot added to new channel!\n\n"
                             f"Channel: {chat.title}\n"
                             f"ID: {chat.id}"
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
        username = f"@{user.username}" if user.username else "No username"
        full_name = user.full_name or "No name"
        join_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        rental_data.add_member(chat.id, user.id, username, full_name, new_status, join_time)
        
        notification_text = (
            f"🆕 NEW MEMBER NOTIFICATION\n\n"
            f"Channel: {chat.title}\n"
            f"Name: {full_name}\n"
            f"ID: {user.id}\n"
            f"Username: {username}\n"
            f"Time: {join_time}\n"
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
    TOKEN = "8502835156:AAG5D1Zq3_QQawxOr9-kBdt-fz0L4LJcjyQ"
    
    INITIAL_ADMIN_ID = "6557052839"  # Set your admin ID here if needed
    
    if INITIAL_ADMIN_ID and not rental_data.admins:
        rental_data.add_admin(INITIAL_ADMIN_ID)
        logger.info(f"Added initial admin: {INITIAL_ADMIN_ID}")
    
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("checktime", checktime))
    application.add_handler(CommandHandler("language", language))
    application.add_handler(CommandHandler("help", help_command))
    
    application.add_handler(CommandHandler("menu", menu, filters=filters.ChatType.PRIVATE))
    
    application.add_handler(CommandHandler("addadmin", addadmin, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("removeadmin", removeadmin, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("listadmins", listadmins, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("stats", stats, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("exportmembers", exportmembers, filters=filters.ChatType.PRIVATE))
    
    application.add_handler(CallbackQueryHandler(button_callback))
    
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_text_message
    ))
    
    application.add_handler(ChatMemberHandler(track_bot_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(ChatMemberHandler(track_chat_members, ChatMemberHandler.CHAT_MEMBER))

    job_queue = application.job_queue
    job_queue.run_repeating(check_expired_rentals, interval=60, first=10)

    logger.info("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()