from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.errors import FloodWait
from datetime import datetime, timedelta
import pytz
import re
from PIL import Image, ImageDraw, ImageFont
import io
import asyncio
from config import API_ID, API_HASH, BOT_TOKEN, ALLOWED_CHAT_IDS, BATCH_GROUPS, TIME_ZONE

#LgcyAlex@123

app = Client("learner_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


def load_data(file_path="data.txt"):
    learners = []
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()[1:]
        for line in lines:
            parts = line.strip().split("\t")
            if len(parts) == 7:
                learners.append({
                    "Learner Code": parts[0],
                    "Learner Name": parts[1],
                    "eMailId": parts[2],
                    "L.P": parts[3],
                    "S.C": parts[4],
                    "Type": parts[5],
                    "Batch": parts[6]
                })
    return learners

learners_data = load_data()
awaiting_update = {}


# Safe wrappers
async def safe_send_message(client, chat_id, text):
    try:
        return await client.send_message(chat_id, text)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await client.send_message(chat_id, text)


async def safe_send_photo(client, chat_id, photo, caption=None, reply_markup=None):
    try:
        return await client.send_photo(chat_id, photo=photo, caption=caption, reply_markup=reply_markup)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await client.send_photo(chat_id, photo=photo, caption=caption, reply_markup=reply_markup)


@app.on_message(filters.command("update") & (filters.private | filters.group))
async def update_command(client, message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    try:
        await message.delete()
    except:
        pass
    if chat_id not in ALLOWED_CHAT_IDS:
        not_allowed_msg = await safe_send_message(client, chat_id, "> You're not authorized to use this command.")
        await asyncio.sleep(10)
        try:
            await not_allowed_msg.delete()
        except:
            pass
        return
    sent = await safe_send_message(client, chat_id, "> 📄 Please send the new `.txt` file to update the data.")
    awaiting_update[user_id] = sent.id


@app.on_message(filters.document & (filters.private | filters.group))
async def handle_file_upload(client, message: Message):
    user_id = message.from_user.id
    if user_id not in awaiting_update:
        return
    update_msg_id = awaiting_update[user_id]
    del awaiting_update[user_id]

    if not message.document.file_name.endswith(".txt"):
        try:
            await message.delete()
            await client.delete_messages(chat_id=message.chat.id, message_ids=update_msg_id)
        except:
            pass
        await safe_send_message(client, message.chat.id, "> Please send a `.txt` file.")
        return

    try:
        await message.delete()
    except:
        pass

    checking_msg = await client.edit_message_text(chat_id=message.chat.id, message_id=update_msg_id, text="🔍 Checking file.")
    await asyncio.sleep(0.5)
    await checking_msg.edit_text("🔍 Checking file...")
    await asyncio.sleep(0.5)
    await checking_msg.edit_text("🔍 Checking file.....")
    await asyncio.sleep(0.5)

    file_path = await message.download()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if not lines:
                raise ValueError("File is empty.")
            for i, line in enumerate(lines[1:], start=2):
                if len(line.strip().split("\t")) != 7:
                    raise ValueError(f"Line {i} is malformed (should have 7 tab-separated values)")
    except Exception as e:
        await checking_msg.edit_text(f"> ⚠️ Format error: {e}")
        return

    with open("data.txt", "w", encoding="utf-8") as f:
        f.writelines(lines)

    global learners_data
    learners_data = load_data()

    try:
        await checking_msg.delete()
    except:
        pass

    with open("data.txt", "rb") as updated_file:
        await client.send_document(chat_id=message.chat.id, document=updated_file, caption="> Data updated successfully.")


def generate_image_with_details(data):
    template_file = "template_dist.png" if data["Type"].lower() == "dist" else "template.png"
    image = Image.open(template_file).convert("RGB")
    draw = ImageDraw.Draw(image)
    initial_font_size = 90
    line_spacing = 40  # space between lines

    try:
        font = ImageFont.truetype("arialbd.ttf", size=initial_font_size)
    except IOError:
        font = ImageFont.load_default()
        initial_font_size = 40

    lines = [
        f"Name: {data['Learner Name']}",
        f"L.P: {data['L.P']}",
        f"Type: {data['Type']}",
        f"Batch: {data['Batch']}",
        f"ID: {data['eMailId']}"
    ]
    max_width = image.width - 80
    font_size = initial_font_size

    while True:
        current_font = ImageFont.truetype("arialbd.ttf", size=font_size) if font != ImageFont.load_default() else font
        total_text_height = len(lines) * (font_size + line_spacing)
        if total_text_height + 300 < image.height:
            too_wide = any(draw.textlength(line, font=current_font) > max_width for line in lines)
            if not too_wide:
                break
        font_size -= 2
        if font_size <= 20:
            break

    final_font = ImageFont.truetype("arialbd.ttf", size=font_size) if font != ImageFont.load_default() else font

    # Dynamically calculate starting Y so text is vertically centered within the remaining space
    total_text_height = len(lines) * (font_size + line_spacing)
    y = max(300, (image.height - total_text_height) // 2)

    x = 40
    for line in lines:
        draw.text((x, y), line, fill="white", font=final_font)
        y += font_size + line_spacing

    sc_text = f"{data['S.C']}"
    sc_font = ImageFont.truetype("arialbd.ttf", size=initial_font_size) if font != ImageFont.load_default() else font
    bbox = draw.textbbox((0, 0), sc_text, font=sc_font)
    text_width = bbox[2] - bbox[0]
    draw.text((image.width - text_width - 40, 50), sc_text, fill="white", font=sc_font)

    output = io.BytesIO()
    image.save(output, format='PNG')
    output.seek(0)
    return output


def get_main_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("☕ In Progress", callback_data="select:InProgress"),
            InlineKeyboardButton("⏳ Expired", callback_data="select:Expired")
        ],
        [
            InlineKeyboardButton("❇️ Completed", callback_data="select:Completed"),
            InlineKeyboardButton("🚪 Check Out", callback_data="select:CheckOut")
        ]
    ])

SELECTION_MAP = {
    "InProgress": "☕ In Progress",
    "Expired": "⏳ Expired",
    "Completed": "❇️ Completed",
    "CheckOut": "🚪 Check Out"
}


def get_selected_button(selection, first_name):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{selection} by {first_name}", callback_data="selected")],
        [InlineKeyboardButton("📝 Remark", callback_data="remark")]
    ])


# for BATCH_GROUPS see on top
@app.on_message(filters.command("start") & (filters.private | filters.group))
async def start_command(client, message: Message):
    chat_id = message.chat.id
    if chat_id in ALLOWED_CHAT_IDS:
        await safe_send_message(client, chat_id, "> I'm alive, online, and ready to help you!\n\n> Just send a **Learner Code** or **Learner Pin** in this chat.")
    else:
        not_allowed_msg = await safe_send_message(client, chat_id, "> ⚠️ This chat is **not authorized** to interact with me.")
        await asyncio.sleep(10)
        try:
            await not_allowed_msg.delete()
        except:
            pass


@app.on_message(filters.text & (filters.private | filters.group))
async def handle_message(client, message: Message):
    chat_id = message.chat.id
    numbers = re.findall(r'\b\d+\b', message.text)
    found_learners = []

    for num in numbers:
        for data in learners_data:
            if num == data["L.P"] or num == data["Learner Code"]:
                found_learners.append(data)

    if found_learners and chat_id not in ALLOWED_CHAT_IDS:
        not_allowed_msg = await safe_send_message(client, chat_id, "> ⚠️ This chat is not authorized to interact with me.")
        await asyncio.sleep(10)
        try:
            await not_allowed_msg.delete()
        except:
            pass
        return

    if not found_learners or chat_id not in ALLOWED_CHAT_IDS:
        return

    total = len(found_learners)
    start_time = datetime.now(pytz.timezone(TIME_ZONE))
    formatted_start = start_time.strftime("%I:%M:%S %p").lstrip("0")

    sending_msg = await safe_send_message(client, chat_id, "📤 Sending...")
    await asyncio.sleep(1)

    try:
        await sending_msg.edit_text(
            f"> 🕒 Estimated time: `{formatted_start} IST`\n"
            f"> 👥 Total learners to process: {total}"
        )
    except:
        pass

    count = 0
    for data in found_learners:
        raw_img = generate_image_with_details(data).getvalue()
        batch = data['Batch'].strip()

        if batch in BATCH_GROUPS:
            for target_chat_id in BATCH_GROUPS[batch]:
                fresh_img = io.BytesIO(raw_img)
                # await safe_send_photo(client, target_chat_id, fresh_img, caption=f"{data['Batch']}", reply_markup=get_main_buttons())
                expire_time = (datetime.now(pytz.timezone(TIME_ZONE)) + timedelta(hours=4)).strftime("%I:%M %p")
                caption = f"Expire At: {expire_time}\n{data['Batch']}"
                await safe_send_photo(client, target_chat_id, fresh_img, caption=caption, reply_markup=get_main_buttons())

                await asyncio.sleep(1)
        else:
            await sending_msg.edit_text(f"> ⚠️ Unknown batch: `{batch}`. Cannot route this learner's info.")
            return

        count += 1
        if count % 5 == 0:
            try:
                await sending_msg.edit_text(
                    f"> 🕒 Estimated time: `{formatted_start}`\n"
                    f"> 👥 Total learners to process: {total}\n"
                    f"> 🚀 Learners processed so far: {count}"
                )
            except:
                pass

    try:
        await message.delete()
    except:
        pass

    end_time = datetime.now(pytz.timezone(TIME_ZONE))
    duration = (end_time - start_time).total_seconds()
    est_minutes = round(duration / 60, 1)

    try:
        await sending_msg.edit_text(
            f"> 🕒 Time taken: `{est_minutes}` {'minute' if est_minutes == 1 else 'minutes'}\n"
            f"> 👥 Total learners processed: {total}\n\n"
            f" 🙏 Thank you for using me.\n"
            f" Have a great day!  •‿•"
        )
        await asyncio.sleep(25)
        await sending_msg.delete()
    except:
        pass


@app.on_callback_query()
async def handle_callback(client: Client, query: CallbackQuery):
    user_first = query.from_user.first_name or "User"
    user_id = query.from_user.id
    data = query.data

    chat_id = query.message.chat.id
    message_id = query.message.id
    unique_msg_id = f"{chat_id}:{message_id}"

    if data.startswith("select:"):
        key = data.split(":")[1]
        selection = SELECTION_MAP.get(key, key)

        tz = pytz.timezone(TIME_ZONE)
        now = datetime.now(tz)
        message_time = query.message.date.astimezone(tz)
        age = now - message_time

        if key == "Expired" and age.total_seconds() < 4 * 3600:
            remaining = timedelta(hours=4) - age
            rem_minutes = int(remaining.total_seconds() // 60)
            rem_hours = rem_minutes // 60
            rem_minutes %= 60

            await query.answer(
                f"Expires After: {rem_hours} h {rem_minutes} m" if rem_hours else f"Expires After: {rem_minutes} m",
                show_alert=True
            )
            return

        await query.message.edit_reply_markup(get_selected_button(selection, user_first))

        try:
            formatted_time = now.strftime("%d-%b-%Y %I:%M %p")
            log_entry = f"{user_first} [{user_id}] | {selection} | {formatted_time} | {unique_msg_id}"

            with open("recode.txt", "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")

        except:
            pass

        await query.answer()

    elif data == "remark":
        try:
            with open("recode.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in reversed(lines):
                parts = line.strip().split(" | ")
                if len(parts) != 4:
                    continue

                name_raw, selection_part, timestamp_str, recorded_msg_id = parts
                if recorded_msg_id != unique_msg_id:
                    continue

                recorded_user_id = int(name_raw.split("[")[1].split("]")[0])
                selector_name = name_raw.split(" [")[0]

                if recorded_user_id != user_id:
                    await query.answer(f"⚠️ Only {selector_name} can remark this.", show_alert=True)
                    return

                # Remove the entry from file
                with open("recode.txt", "w", encoding="utf-8") as wf:
                    for l in lines:
                        if not l.strip().endswith(f"| {unique_msg_id}"):
                            wf.write(l)
                break
            else:
                await query.answer("⚠️ No matching record found.", show_alert=True)
                return

            await query.message.edit_reply_markup(get_main_buttons())
            await query.answer()

        except:
            await query.answer("⚠️ Error handling remark", show_alert=True)

    elif data == "selected":
        try:
            tz = pytz.timezone(TIME_ZONE)
            now = datetime.now(tz)

            with open("recode.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in reversed(lines):
                parts = line.strip().split(" | ")
                if len(parts) != 4:
                    continue

                name_raw, selection_part, timestamp_str, recorded_msg_id = parts
                if recorded_msg_id != unique_msg_id:
                    continue

                name_part = name_raw.split(" [")[0]
                selection_time = datetime.strptime(timestamp_str, "%d-%b-%Y %I:%M %p")
                selection_time = tz.localize(selection_time)

                diff = now - selection_time
                minutes = int(diff.total_seconds() // 60)
                ago_text = f"{minutes} m ago" if minutes < 60 else f"{round(diff.total_seconds() / 3600, 1)} h ago"

                message_time = query.message.date.astimezone(tz)
                countdown_end = message_time + timedelta(hours=4)
                remaining = countdown_end - now

                # countdown_text = "Expired" if remaining.total_seconds() <= 0 else f"{int(remaining.total_seconds() // 3600)}h {int((remaining.total_seconds() % 3600) // 60)}m"

                if remaining.total_seconds() <= 0:
                        countdown_text = "Expired"
                else:
                    total_minutes = int(remaining.total_seconds() // 60)
                    hours = total_minutes // 60
                    minutes = total_minutes % 60
                    if hours > 0 and minutes > 0:
                        countdown_text = f"{hours}h {minutes}m"
                    elif hours > 0:
                        countdown_text = f"{hours}h"
                    else:
                        countdown_text = f"{minutes}m"  
             
                alert_text = (
                    f"{name_part}\n\n"
                    f"{selection_part}\n"
                    f"{timestamp_str} ({ago_text})\n"
                    f"Expires After: {countdown_text}"
                )

                await query.answer(alert_text, show_alert=True)
                break
            else:
                await query.answer("⚠️ No recent selection record found.", show_alert=True)

        except:
            await query.answer("⚠️ Error reading log", show_alert=True)

    elif data == "noop":
        await query.answer()


print("Successfully hosted")
app.run()

