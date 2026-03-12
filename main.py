import os
import json
from datetime import datetime
from typing import Optional
import pytz
import logging
from telegram import Update, Chat
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import Database

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "8507971493:AAHI1qvmEof07K2pn8yXtO4eEFllWeLj_98")
OWNER_ID = int(os.getenv("OWNER_ID", "8377642006"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
PORT = int(os.getenv("PORT", "8080"))

# Initialize database and scheduler
db = Database()
scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Phnom_Penh'))
app_instance = None  # Will be set in main()

# Khmer messages
MESSAGES = {
    "owner_only": "⛔ អ្នកមិនមានសិទ្ធិប្រើ Bot នេះទេ",
    "private_only": "⚠️ សូមធ្វើការកំណត់ពេលក្នុង Private Chat ប៉ុណ្ណោះ",
    "past_time": "❌ មិនអាចកំណត់ពេលអតីតកាលបានទេ\n\nសូមកំណត់ពេលវេលាខាងមុខ។",
    "invalid_format": "❌ ស្ទង់មើលលម្អិត\n\nរូបរាង:\n📅 DD-MM-YYYY HH:MM GROUP_ID\n\nឧទាហរណ៍:\n25-03-2026 18:30 -1001234567890",
    "success": "✅ កំណត់ពេលបានជោគជ័យ\n\n📅 ថ្ងៃ: {date}\n⏰ ម៉ោង: {time}\n👥 Group ID: {group_id}\n📊 Status: Pending ⏳",
    "sent": "✅ សារត្រូវបានផ្ញើដោយជោគជ័យ\n\n📅 {date}\n⏰ {time}\n👥 Group ID: {group_id}\n📊 Status: បានផ្ញើ ✅",
    "list_header": "📋 បញ្ជីកាលវិភាគសារ (Schedule Messages)",
    "no_schedules": "📋 គ្មានលេខកាលវិ按",
    "deleted": "🗑 Schedule #{id} ត្រូវបានលុបរួចរាល់",
    "delete_error": "❌ មិនរកឃើញលេខកាលវិពន្ធ #{id}",
}

def format_time(dt_str: str) -> tuple:
    """Parse schedule_time from DB and return date, time strings"""
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%d-%m-%Y"), dt.strftime("%H:%M")
    except:
        return dt_str.split()[0], dt_str.split()[1] if len(dt_str.split()) > 1 else "00:00"

async def check_owner(update: Update) -> bool:
    """Check if user is the bot owner"""
    return update.effective_user.id == OWNER_ID

async def check_private(update: Update) -> bool:
    """Check if message is in private chat"""
    return update.effective_chat.type == Chat.PRIVATE

async def parse_schedule_format(text: str) -> Optional[dict]:
    """Parse schedule format: DD-MM-YYYY HH:MM GROUP_ID"""
    try:
        parts = text.strip().split()
        if len(parts) < 3:
            return None
        
        date_str = parts[0]  # DD-MM-YYYY
        time_str = parts[1]  # HH:MM
        group_id = parts[2]   # GROUP_ID
        
        # Validate date format
        dt = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H:%M")
        
        # Check if time is in future
        tz = pytz.timezone('Asia/Phnom_Penh')
        dt_tz = tz.localize(dt)
        now_tz = datetime.now(tz)
        
        if dt_tz <= now_tz:
            return None
        
        return {
            "date": date_str,
            "time": time_str,
            "group_id": group_id,
            "datetime": dt_tz
        }
    except:
        return None

async def send_scheduled_message(schedule_id: int):
    """Send a scheduled message to the group"""
    schedule = db.get_schedule(schedule_id)
    if not schedule:
        return
    
    try:
        group_id = int(schedule["group_id"])
        source_chat_id = schedule["source_chat_id"]
        source_message_id = schedule["source_message_id"]
        is_scheduled_forward = schedule.get("is_scheduled_forward", False)
        bot = app_instance.bot
        
        # If this is a scheduled forward, use forward_message (shows "forwarded from")
        # If this is NOT a scheduled forward, use copy_message (doesn't show original sender)
        if is_scheduled_forward:
            await bot.forward_message(
                chat_id=group_id,
                from_chat_id=source_chat_id,
                message_id=source_message_id
            )
        else:
            await bot.copy_message(
                chat_id=group_id,
                from_chat_id=source_chat_id,
                message_id=source_message_id
            )
        
        # Update status to sent
        db.update_status(schedule_id, "sent")
        
        # Notify owner
        date_str, time_str = format_time(schedule['schedule_time'])
        notification = MESSAGES["sent"].format(
            date=date_str,
            time=time_str,
            group_id=schedule['group_id']
        )
        await bot.send_message(chat_id=OWNER_ID, text=notification)
        
        # Delete schedule from list after successful send
        db.delete_schedule(schedule_id)
        
        logger.info(f"Sent scheduled message {schedule_id}")
    except Exception as e:
        logger.error(f"Error sending scheduled message {schedule_id}: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    # Check owner
    if not await check_owner(update):
        await update.message.reply_text(MESSAGES["owner_only"])
        return
    
    # Check private chat
    if not await check_private(update):
        return  # Silently ignore
    
    # Check if this is a reply
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "💬 សូមឆ្លើយតម្លើងលើសារដែលលាក់ទុក\n\n"
            "ដូចនេះ៖\n"
            "1️⃣ ផ្ញើសារណាមួយ\n"
            "2️⃣ ឆ្លើយតម្លើងលើសារ\n"
            "3️⃣ វាយបញ្ចូលលម្អិត៖ DD-MM-YYYY HH:MM GROUP_ID"
        )
        return
    
    # Parse schedule format from reply
    schedule_data = await parse_schedule_format(update.message.text)
    if not schedule_data:
        await update.message.reply_text(MESSAGES["invalid_format"] if "-" in update.message.text else MESSAGES["past_time"])
        return
    
    # Get replied message
    replied_msg = update.message.reply_to_message
    source_message_id = replied_msg.message_id
    source_chat_id = OWNER_ID  # The message is in the owner's private chat with the bot
    
    # Check if the replied message is a forwarded message
    is_scheduled_forward = (getattr(replied_msg, 'forward_from', None) is not None or 
                            getattr(replied_msg, 'forward_from_chat', None) is not None)
    
    # Add schedule to database
    schedule_id = db.add_schedule(
        source_chat_id=source_chat_id,
        source_message_id=source_message_id,
        group_id=schedule_data["group_id"],
        schedule_time=schedule_data["datetime"].isoformat(),
        is_scheduled_forward=is_scheduled_forward
    )
    
    # Schedule the message
    scheduler.add_job(
        send_scheduled_message,
        'date',
        run_date=schedule_data["datetime"],
        args=(schedule_id,),
        id=f"schedule_{schedule_id}"
    )
    
    # Send confirmation
    confirmation = MESSAGES["success"].format(
        date=schedule_data["date"],
        time=schedule_data["time"],
        group_id=schedule_data["group_id"]
    )
    await update.message.reply_text(confirmation)

async def list_schedules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all schedules"""
    # Check private chat first (silent ignore if not)
    if not await check_private(update):
        return
    
    if not await check_owner(update):
        await update.message.reply_text(MESSAGES["owner_only"])
        return
    
    # Renumber schedules to eliminate gaps from deletions
    db.renumber_schedules()
    
    schedules = db.get_all_schedules()
    pending_schedules = [s for s in schedules if s['status'] == 'pending']
    
    if not pending_schedules:
        await update.message.reply_text(MESSAGES["no_schedules"])
        return
    
    response = MESSAGES["list_header"] + "\n\n"
    for schedule in pending_schedules:
        date_str, time_str = format_time(schedule['schedule_time'])
        response += f"━━━━━━━━━━━━━━━━\n\n"
        response += f"📝 Schedule #{schedule['id']}\n"
        response += f"📅 កាលបរិច្ឆេទ: {date_str}\n"
        response += f"⏰ ម៉ោង: {time_str}\n"
        response += f"👥 Group ID: {schedule['group_id']}\n"
        response += f"📌 ស្ថានភាព: ⏳ Pending\n\n"
    
    response += "━━━━━━━━━━━━━━━━"
    await update.message.reply_text(response)

async def delete_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a schedule"""
    # Check private chat first (silent ignore if not)
    if not await check_private(update):
        return
    
    if not await check_owner(update):
        await update.message.reply_text(MESSAGES["owner_only"])
        return
    
    try:
        if not context.args:
            await update.message.reply_text("❌ សូមផ្ដល់លេខកាលវិពន្ធ")
            return
        
        schedule_id = int(context.args[0].lstrip('#').rstrip('.'))
        if not schedule_id:
            await update.message.reply_text("❌ សូមផ្ដល់លេខកាលវិពន្ធ")
            return
        
        if db.delete_schedule(schedule_id):
            # Cancel job if exists
            try:
                scheduler.remove_job(f"schedule_{schedule_id}")
            except:
                pass
            
            await update.message.reply_text(MESSAGES["deleted"].format(id=schedule_id))
        else:
            await update.message.reply_text(MESSAGES["delete_error"].format(id=schedule_id))
    except:
        await update.message.reply_text("❌ ប្រឹងម្តងទៀត")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    # Check private chat first (silent ignore if not)
    if not await check_private(update):
        return
    
    if not await check_owner(update):
        await update.message.reply_text(MESSAGES["owner_only"])
        return
    
    welcome = (
        "👋 សូមស្វាគមន៍មកកាន់ Schedule Bot!\n\n"
        "📋 ការណ្តើម៖\n"
        "/list - ដើម្បីមើលលេខកាលវិពន្ធ\n"
        "/delete [ID] - ដើម្បីលុបលេខកាលវិពន្ធ\n\n"
        "💬 ដើម្បីកំណត់ពេល:\n"
        "1️⃣ ផ្ញើសារណាមួយ\n"
        "2️⃣ ឆ្លើយតម្លើងលើសារ\n"
        "3️⃣ វាយបញ្ចូល: DD-MM-YYYY HH:MM GROUP_ID"
    )
    await update.message.reply_text(welcome)

def main():
    """Start the bot"""
    global app_instance
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    app_instance = app  # Store app instance for scheduler jobs
    
    # Start scheduler
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_schedules))
    app.add_handler(CommandHandler("delete", delete_schedule))
    app.add_handler(MessageHandler(filters.REPLY & ~filters.COMMAND, handle_message))
    
    # Use webhook if URL is provided, otherwise polling
    if WEBHOOK_URL:
        logger.info(f"Starting bot with webhook: {WEBHOOK_URL}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
        )
    else:
        logger.info("Starting bot with polling")
        app.run_polling()

if __name__ == "__main__":
    main()
