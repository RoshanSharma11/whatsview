import os
import re
from flask import Flask, render_template, send_from_directory, request, jsonify, url_for
import shutil
import zipfile

app = Flask(__name__)
CHAT_FOLDER = "chats"  # Folder where exported chats are stored

# Regex pattern to parse messages with media attachments
MESSAGE_PATTERN = re.compile(r"\[(\d{2}/\d{2}/\d{2,4}), (\d{1,2}:\d{2}:\d{2}\s?[APap][Mm]?)\] (.*?): (.*)")
MEDIA_PATTERN = re.compile(r"^\[(\d{2}/\d{2}/\d{2}),\s*([\d:]+\s*[APM]*)\]\s(.*?):\s*(.*?)\s*<attached:\s*([^>]+)>")
# MEDIA_PATTERN = re.compile(r"^\[(\d{2}/\d{2}/\d{2}),\s*([\d:]+\s*[APM]*)\]\s(.+?):.*?<attached:\s*([^>]+)>")

def parse_chat(file_path, media_path):
    messages = []
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    for line in lines:
        clean_line = line.strip().replace("\u200e", "")
        message_match = MESSAGE_PATTERN.match(clean_line)
        media_match = MEDIA_PATTERN.findall(f"{clean_line}")

        if media_match:
            date, time, sender, message, media_file = media_match[0]
            messages.append({
                "date": date, "time": time, "sender": sender, "message": message, "type": "media",
                "media_file": media_file.strip()
            })
        elif message_match:
            date, time, sender, message = message_match.groups()
            messages.append({
                "date": date, "time": time, "sender": sender, "message": message, "type": "text"
            })
    
    return messages


@app.route("/")
def index():
    chat_folders = [f for f in os.listdir(CHAT_FOLDER) if os.path.isdir(os.path.join(CHAT_FOLDER, f))]
    return render_template("index.html", chat_folders=chat_folders)


@app.route("/chat/<chat_name>")
def chat(chat_name):
    chat_path = os.path.join(CHAT_FOLDER, chat_name, "_chat.txt")
    media_path = os.path.join(CHAT_FOLDER, chat_name)
    
    messages = parse_chat(chat_path, media_path) if os.path.exists(chat_path) else []
    return render_template("chat.html", chat_name=chat_name, messages=messages)


@app.route("/media/<chat_name>/<filename>")
def media(chat_name, filename):
    return send_from_directory(os.path.join(CHAT_FOLDER, chat_name), filename)

@app.route("/upload", methods=["POST"])
def upload_chat():
    if "chatZip" not in request.files:
        return jsonify({"success": False, "message": "No file uploaded."})

    uploaded_file = request.files["chatZip"]
    if uploaded_file.filename == "":
        return jsonify({"success": False, "message": "No selected file."})

    if not uploaded_file.filename.endswith(".zip"):
        return jsonify({"success": False, "message": "Only ZIP files are allowed."})

    # Save ZIP file temporarily
    temp_zip_path = os.path.join("temp_uploads", uploaded_file.filename)
    os.makedirs("temp_uploads", exist_ok=True)
    uploaded_file.save(temp_zip_path)

    # Extract ZIP
    try:
        with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
            extracted_folder = uploaded_file.filename.replace(".zip", "")  # Folder name from ZIP
            extract_path = os.path.join(CHAT_FOLDER, extracted_folder)
            
            if os.path.exists(extract_path):
                # return jsonify({"success": False, "message": "Chat folder already exists."})
                shutil.rmtree(extract_path)

            zip_ref.extractall(extract_path)

        os.remove(temp_zip_path)  # Clean up after extraction
        return jsonify({"success": True, "message": "Chat uploaded successfully!"})

    except zipfile.BadZipFile:
        return jsonify({"success": False, "message": "Invalid ZIP file."})


if __name__ == "__main__":
    app.run(debug=True, port=8000)
