# Telegram Bot - Schedule Message to Group

## Project Overview
A Khmer-language Telegram bot for scheduling messages to groups with the following features:
- Schedule messages by replying to a message with date/time format
- Uses `bot.forward_message()` to directly forward messages (preserves all formatting and media)
- Forward sender detection for forwarded messages
- Schedule status tracking (Pending/Sent)
- Owner-only access control
- Private chat scheduling only
- APScheduler for automated sending

## Tech Stack
- Python 3.11+
- python-telegram-bot 21.8
- APScheduler 3.10.4
- JSON database (schedules.json)
- Pytz for timezone handling

## Key Features Implemented
1. **Schedule Format**: DD-MM-YYYY HH:MM GROUP_ID
2. **Reply-based Scheduling**: Reply to any message with schedule format
3. **Message Forwarding**: Uses `forward_message()` to preserve original formatting and all media types automatically
4. **Forward Detection**: Extracts and displays original sender name for forwarded messages
5. **Status System**: Pending/Sent status tracking
6. **Commands**: /start, /list, /delete [ID]
7. **Khmer Language**: All messages in Khmer
8. **Owner Only**: OWNER_ID environment variable controls access

## Database Structure (schedules.json)
```json
{
  "schedules": [
    {
      "id": 1,
      "source_chat_id": 5002402843,
      "source_message_id": 2547,
      "group_id": "-1001234567890",
      "schedule_time": "2026-03-25T20:00:00+07:00",
      "status": "pending",
      "created_at": "2026-03-10T..."
    }
  ],
  "next_id": 2
}
```
**Note**: `source_chat_id` is the owner's private chat with the bot, `source_message_id` is the message ID to be forwarded. Messages are forwarded as-is - no "forwarded from" attribution is added.

## Files
- `main.py`: Main bot code with all handlers
- `database.py`: Database abstraction for JSON storage
- `.env.example`: Environment variables template
- `schedules.json`: Auto-created database file

## Environment Variables Required
- `BOT_TOKEN`: Telegram bot token
- `OWNER_ID`: Owner user ID for access control
- `WEBHOOK_URL`: (Optional) For webhook deployment
- `PORT`: (Optional) Port for webhook, defaults to 8080

## Running the Bot
```bash
pip install -r requirements.txt
python main.py
```

Uses polling by default (no WEBHOOK_URL), or webhook if WEBHOOK_URL is set.

## Timezone
- Fixed to Asia/Phnom_Penh (Cambodia timezone)
- Uses 24-hour time format
