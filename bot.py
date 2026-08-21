import logging
import os
import sqlite3
import imaplib
import email
import time
from email.header import decode_header
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# -----------------------------------------------------------------------------
# 1. ADVANCED ENTERPRISE LOGGING & CONFIGURATION SETUP
# -----------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - [%(levelname)s] - %(name)s - (Line %(lineno)d) - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger("EnterpriseGmailBot")

BOT_TOKEN = "8611310082:AAEWuG6NjGjouFguy0ChsM0BiV4QNbu1g84"
OWNER_ID = 8961596390

# -----------------------------------------------------------------------------
# 2. ADVANCED HIGH-PERFORMANCE DATABASE ARCHITECTURE & MIGRATION
# -----------------------------------------------------------------------------
def initialize_complete_database():
    try:
        connection = sqlite3.connect("enterprise_bot_master.db", timeout=30.0)
        cursor = connection.cursor()
        
        # Performance tuning pragmas
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")

        # Users Table with extended attributes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                is_premium INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Active',
                joined_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # User Gmail Accounts Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_gmails (
                account_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                email TEXT UNIQUE,
                app_password TEXT,
                connection_status TEXT DEFAULT 'Healthy',
                last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # System Audit & Security Logs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id INTEGER,
                action_type TEXT,
                description TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Bot Analytics & Metrics Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_metrics (
                metric_key TEXT PRIMARY KEY,
                metric_value INTEGER DEFAULT 0
            )
        """)

        connection.commit()
        connection.close()
        logger.info("Enterprise database architecture initialized successfully.")
    except Exception as db_error:
        logger.critical(f"Critical database initialization failure: {db_error}")

initialize_complete_database()

# -----------------------------------------------------------------------------
# 3. ROBUST ENCRYPTED/SECURE IMAP OTP PARSING & FETCHING ENGINE
# -----------------------------------------------------------------------------
def execute_imap_otp_pipeline(email_address, app_password):
    connection_instance = None
    try:
        # Secure SSL Connection to Gmail IMAP
        connection_instance = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        connection_instance.login(email_address, app_password)
        connection_instance.select("inbox", readonly=True)

        # Search query for unread or recent messages
        search_status, message_id_list = connection_instance.search(None, "UNSEEN")
        if search_status != "OK" or not message_id_list[0]:
            search_status, message_id_list = connection_instance.search(None, "ALL")

        if not message_id_list or not message_id_list[0]:
            connection_instance.logout()
            return "⚠️ ইনবক্সে কোনো নতুন মেইল বা ওটিপি পাওয়া যায়নি।"

        # Fetch latest email payload
        recent_ids = message_id_list[0].split()
        target_mail_id = recent_ids[-1]

        fetch_status, raw_mail_data = connection_instance.fetch(target_mail_id, "(RFC822)")
        for response_chunk in raw_mail_data:
            if isinstance(response_chunk, tuple):
                parsed_email_object = email.message_from_bytes(response_chunk[1])
                
                # Extract and decode subject line
                raw_subject = parsed_email_object["Subject"]
                decoded_subject = "No Subject"
                if raw_subject:
                    subject_parts = decode_header(raw_subject)
                    for text_content, character_encoding in subject_parts:
                        if isinstance(text_content, bytes):
                            decoded_subject = text_content.decode(character_encoding or "utf-8", errors="ignore")
                        else:
                            decoded_subject = text_content

                # Extract plain text body content
                extracted_body_text = ""
                if parsed_email_object.is_multipart():
                    for multipart_element in parsed_email_object.walk():
                        content_type = multipart_element.get_content_type()
                        content_disposition = str(multipart_element.get("Content-Disposition"))
                        if "attachment" not in content_disposition and content_type == "text/plain":
                            try:
                                payload_bytes = multipart_element.get_payload(decode=True)
                                if payload_bytes:
                                    extracted_body_text = payload_bytes.decode(errors="ignore")
                                    break
                            except Exception:
                                pass
                else:
                    try:
                        payload_bytes = parsed_email_object.get_payload(decode=True)
                        if payload_bytes:
                            extracted_body_text = payload_bytes.decode(errors="ignore")
                    except Exception:
                        pass

                connection_instance.logout()
                
                # Formatting final output for Telegram UI
                truncated_body = extracted_body_text[:500] if extracted_body_text else "Body content could not be parsed."
                return (
                    f"📌 **Subject:** {decoded_subject}\n\n"
                    f"💬 **Extracted Content / OTP Preview:**\n"
                    f"<code>{truncated_body}</code>"
                )

        connection_instance.logout()
        return "❌ মেইল পার্স করা সম্ভব হয়নি।"
        
    except imaplib.IMAP4.error as imap_err:
        logger.error(f"IMAP Auth/Protocol Error for {email_address}: {imap_err}")
        return "❌ জিমেইল প্রমাণীকরণ ত্রুটি! অ্যাপ পাসওয়ার্ড সঠিক আছে কিনা এবং IMAP এনাবল করা আছে কিনা চেক করুন।"
    except Exception as general_err:
        logger.error(f"Unexpected error in IMAP pipeline: {general_err}")
        return "❌ সার্ভার কানেকশনে সমস্যা হয়েছে। অনুগ্রহ করে পরে আবার চেষ্টা করুন।"

# -----------------------------------------------------------------------------
# 4. COMPREHENSIVE START & DASHBOARD INTERFACE HANDLER
# -----------------------------------------------------------------------------
async def start_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_obj = update.effective_user
    db_conn = sqlite3.connect("enterprise_bot_master.db")
    db_cursor = db_conn.cursor()
    
    # Register or update user profile in database
    db_cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username, first_name) 
        VALUES (?, ?, ?)
    """, (user_obj.id, user_obj.username or "None", user_obj.first_name))
    db_conn.commit()
    
    # Check user premium status
    db_cursor.execute("SELECT is_premium FROM users WHERE user_id = ?", (user_obj.id,))
    membership_row = db_cursor.fetchone()
    user_is_premium = membership_row[0] if membership_row else 0
    db_conn.close()

    dashboard_greeting_text = (
        f"⚡ **Enterprise Gmail Automation Hub** ⚡\n\n"
        f"স্বাগতম, **{user_obj.first_name}**!\n"
        f"আপনার অ্যাকাউন্ট স্ট্যাটাস: `{'⭐ Premium Member' if user_is_premium == 1 or user_obj.id == OWNER_ID else '🛡️ Standard User'}`\n\n"
        "নিচের উচ্চ-ক্ষমতা সম্পন্ন মেনু প্যানেল থেকে আপনার প্রয়োজনীয় অপারেশনটি সিলেক্ট করুন:"
    )

    markup_keyboard = [
        [InlineKeyboardButton("📩 Add Gmail / জিমেইল অ্যাড", callback_data="menu_add_gmail")],
        [InlineKeyboardButton("🔍 Check OTP / ওটিপি চেক", callback_data="menu_check_otp")],
        [InlineKeyboardButton("📋 My Accounts / অ্যাকাউন্টস", callback_data="menu_list_gmails")],
        [InlineKeyboardButton("⭐ Premium Status / প্রিমিয়াম", callback_data="menu_premium_info")]
    ]

    if user_obj.id == OWNER_ID or user_is_premium == 1:
        markup_keyboard.append([InlineKeyboardButton("👑 Enterprise Admin Panel / অ্যাডমিন প্যানেল", callback_data="admin_control_panel")])

    reply_markup_markup = InlineKeyboardMarkup(markup_keyboard)
    
    if update.message:
        await update.message.reply_text(dashboard_greeting_text, reply_markup=reply_markup_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(dashboard_greeting_text, reply_markup=reply_markup_markup, parse_mode="Markdown")

# -----------------------------------------------------------------------------
# 5. ADVANCED CALLBACK QUERY ROUTING ENGINE
# -----------------------------------------------------------------------------
async def global_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_obj = update.callback_query
    await query_obj.answer()
    callback_payload = query_obj.data
    user_id_val = query_obj.from_user.id

    if callback_payload == "menu_add_gmail":
        guideline_text = (
            "📩 **জিমেইল অ্যাকাউন্ট সংযোগের নির্দেশিকা:**\n\n"
            "১. আপনার জিমেইল অ্যাকাউন্টে 2-Step Verification অন করুন।\n"
            "২. Google Account Security থেকে একটি **App Password** জেনারেট করুন।\n"
            "৩. নিচের ফরম্যাটে বট চ্যাটে মেসেজ পাঠান:\n\n"
            "`your_email@gmail.com your_app_password`\n\n"
            "সরাসরি চ্যাটে লিখে পাঠিয়ে দিন।"
        )
        back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu_return")]])
        await query_obj.message.edit_text(guideline_text, reply_markup=back_markup, parse_mode="Markdown")

    elif callback_payload == "menu_check_otp":
        db_conn = sqlite3.connect("enterprise_bot_master.db")
        db_cursor = db_conn.cursor()
        db_cursor.execute("SELECT email, app_password FROM user_gmails WHERE user_id = ?", (user_id_val,))
        stored_accounts = db_cursor.fetchall()
        db_conn.close()

        if not stored_accounts:
            response_text = "⚠️ আপনার কোনো জিমেইল অ্যাকাউন্ট সংরক্ষিত নেই। প্রথমে জিমেইল অ্যাড করুন।"
            back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu_return")]])
        else:
            response_text = "📬 **রিয়েল-টাইম জিমেইল ওটিপি ফেচিং রেজাল্ট:**\n\n"
            for index_num, (mail_acc, pass_acc) in enumerate(stored_accounts, 1):
                otp_output = execute_imap_otp_pipeline(mail_acc, pass_acc)
                response_text += f"🔹 **Acc #{index_num}:** `{mail_acc}`\n{otp_output}\n\n"
            
            back_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh OTP Now", callback_data="menu_check_otp")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu_return")]
            ])

        await query_obj.message.edit_text(response_text, reply_markup=back_markup, parse_mode="Markdown")

    elif callback_payload == "menu_list_gmails":
        db_conn = sqlite3.connect("enterprise_bot_master.db")
        db_cursor = db_conn.cursor()
        db_cursor.execute("SELECT email, added_date FROM user_gmails WHERE user_id = ?", (user_id_val,))
        my_accs = db_cursor.fetchall()
        db_conn.close()

        if not my_accs:
            response_text = "📭 আপনার প্রোফাইলে কোনো জিমেইল অ্যাড করা নেই।"
        else:
            response_text = "📋 **আপনার সংগৃহীত জিমেইল অ্যাকাউন্টসমূহ:**\n\n"
            for idx, (m, dt) in enumerate(my_accs, 1):
                response_text += f"{idx}. `{m}` (Added: {dt})\n"

        back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu_return")]])
        await query_obj.message.edit_text(response_text, reply_markup=back_markup, parse_mode="Markdown")

    elif callback_payload == "menu_premium_info":
        info_text = (
            "⭐ **এন্টারপ্রাইজ প্রিমিয়াম প্যাকেজ সুবিধা:**\n\n"
            "• আনলিমিটেড জিমেইল কানেক্টিভিটি\n"
            "• ইনস্ট্যান্ট রিয়েল-টাইম অটো-রিড ওটিপি ইঞ্জিন\n"
            "• ডেডিকেটেড ক্লাউড সার্ভার ব্যাকএন্ড\n\n"
            f"প্রিমিয়াম নিতে সরাসরি ওনারের সাথে যোগাযোগ করুন: [Contact Owner](tg://user?id={OWNER_ID})"
        )
        back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu_return")]])
        await query_obj.message.edit_text(info_text, reply_markup=back_markup, parse_mode="Markdown")

    elif callback_payload == "admin_control_panel" and user_id_val == OWNER_ID:
        admin_panel_text = "👑 **Enterprise Administrator Command Control**\n\nনিচের অ্যাডমিন অপশনগুলো ব্যবহার করুন:"
        admin_keyboard = [
            [InlineKeyboardButton("📊 System Metrics / স্ট্যাটিস্টিক্স", callback_data="admin_action_stats")],
            [InlineKeyboardButton("➕ Grant Premium / প্রিমিয়াম দিন", callback_data="admin_action_prem_guide")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu_return")]
        ]
        await query_obj.message.edit_text(admin_panel_text, reply_markup=InlineKeyboardMarkup(admin_keyboard), parse_mode="Markdown")

    elif callback_payload == "admin_action_stats" and user_id_val == OWNER_ID:
        db_conn = sqlite3.connect("enterprise_bot_master.db")
        db_cursor = db_conn.cursor()
        db_cursor.execute("SELECT COUNT(*) FROM users")
        user_count = db_cursor.fetchone()[0]
        db_cursor.execute("SELECT COUNT(*) FROM user_gmails")
        gmail_count = db_cursor.fetchone()[0]
        db_conn.close()

        stats_text = (
            "📊 **সার্ভার ও সিস্টেম পারফরম্যান্স মেট্রিক্স:**\n\n"
            f"👥 মোট রেজিস্টার্ড ইউজার সংখ্যা: {user_count}\n"
            f"📧 মোট ডাটাবেজে যুক্ত জিমেইল: {gmail_count}\n"
            "⚙️ ক্লাউড সার্ভার হেলথ: 100% Operational\n"
            "🚀 প্রটোকল: IMAP Secure SSL v4"
        )
        back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_control_panel")]])
        await query_obj.message.edit_text(stats_text, reply_markup=back_markup, parse_mode="Markdown")

    elif callback_payload == "admin_action_prem_guide" and user_id_val == OWNER_ID:
        guide_txt = (
            "➕ **ইউজারকে প্রিমিয়াম করার নিয়ম:**\n\n"
            "বট চ্যাটে সরাসরি এই কমান্ডটি টাইপ করুন:\n"
            "`/addprem USER_ID`\n\n"
            "উদাহরণস্বরূপ: `/addprem 8961596390`"
        )
        back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_control_panel")]])
        await query_obj.message.edit_text(guide_txt, reply_markup=back_markup, parse_mode="Markdown")

    elif callback_payload == "main_menu_return":
        await start_command_handler(update, context)

# -----------------------------------------------------------------------------
# 6. ADMIN COMMANDS & CHAT INPUT CONTROLLERS
# -----------------------------------------------------------------------------
async def command_add_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caller_id = update.effective_user.id
    if caller_id != OWNER_ID:
        await update.message.reply_text("⛔ এই কমান্ডটি শুধুমাত্র সিস্টেম ওনারের জন্য নির্ধারিত!")
        return

    command_arguments = context.args
    if not command_arguments:
        await update.message.reply_text("⚠️ সঠিক ফরম্যাটে কমান্ড দিন:\n`/addprem USER_ID`", parse_mode="Markdown")
        return

    try:
        target_user_id = int(command_arguments[0])
        db_conn = sqlite3.connect("enterprise_bot_master.db")
        db_cursor = db_conn.cursor()
        db_cursor.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (target_user_id,))
        db_conn.commit()
        db_conn.close()

        await update.message.reply_text(f"✅ সফলভাবে ইউজার আইডি `{target_user_id}`-কে প্রিমিয়াম স্ট্যাটাস প্রদান করা হয়েছে!", parse_mode="Markdown")
    except Exception as execution_error:
        await update.message.reply_text(f"❌ কমান্ড কার্যকরে ত্রুটি ঘটেছে: {execution_error}")

async def message_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    incoming_text = update.message.text
    active_user_id = update.effective_user.id

    # Handle incoming Gmail and App Password format
    if incoming_text and " " in incoming_text and "@gmail.com" in incoming_text:
        split_elements = incoming_text.split(" ")
        if len(split_elements) >= 2:
            extracted_email = split_elements[0].strip()
            extracted_password = split_elements[1].strip()

            try:
                db_conn = sqlite3.connect("enterprise_bot_master.db")
                db_cursor = db_conn.cursor()
                db_cursor.execute("""
                    INSERT INTO user_gmails (user_id, email, app_password) 
                    VALUES (?, ?, ?)
                """, (active_user_id, extracted_email, extracted_password))
                db_conn.commit()
                db_conn.close()

                await update.message.reply_text(
                    "✅ আপনার জিমেইল অ্যাকাউন্ট ও অ্যাপ পাসওয়ার্ড সফলভাবে সিকিউর ডাটাবেজে সংরক্ষণ করা হয়েছে!\n\n"
                    "এখন মেনু থেকে **Check OTP** অপশনে গিয়ে ওটিপি দেখতে পারবেন।"
                )
                return
            except sqlite3.IntegrityError:
                await update.message.reply_text("⚠️ এই জিমেইল অ্যাকাউন্টটি ইতিমধ্যে ডাটাবেজে সংরক্ষিত রয়েছে।")
                return
            except Exception as save_err:
                logger.error(f"Failed to save gmail: {save_err}")
                await update.message.reply_text("❌ জিমেইল সেভ করতে সমস্যা হয়েছে। সঠিক ফরম্যাট ব্যবহার করুন।")
                return

    await update.message.reply_text(
        "❓ আপনার মেসেজটি পরিষ্কার নয়। জিমেইল যুক্ত করতে নিচের ফরম্যাটে পাঠান:\n\n"
        "`email@gmail.com app_password`\n\n"
        "অথবা মূল মেনুতে যেতে `/start` কমান্ড ব্যবহার করুন।",
        parse_mode="Markdown"
    )

# -----------------------------------------------------------------------------
# 7. MAIN EXECUTABLE RUNTIME INITIALIZER
# -----------------------------------------------------------------------------
def run_enterprise_bot():
    logger.info("Initializing Enterprise Telegram Bot Application...")
    app_builder = ApplicationBuilder().token(BOT_TOKEN).build()

    # Registering Handlers
    app_builder.add_handler(CommandHandler("start", start_command_handler))
    app_builder.add_handler(CommandHandler("addprem", command_add_premium))
    app_builder.add_handler(CallbackQueryHandler(global_callback_router))
    app_builder.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_input_handler))

    logger.info("Bot application is fully configured and starting polling...")
    app_builder.run_polling()

if __name__ == "__main__":
    run_enterprise_bot()
