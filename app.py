from flask import Flask, render_template, request, jsonify, session, send_from_directory
import os, json, uuid
from werkzeug.utils import secure_filename
from groq_client import get_groq_response

app = Flask(__name__)
app.secret_key = 'supersecretkey'

UPLOAD_FOLDER = 'uploads'
HISTORY_DIR = 'history'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)

def get_session_id():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]

def get_history_file(session_id):
    return os.path.join(HISTORY_DIR, f"{session_id}.json")

def load_history(session_id):
    try:
        with open(get_history_file(session_id), "r") as f:
            return json.load(f)
    except:
        return []

def save_history(session_id, history):
    with open(get_history_file(session_id), "w") as f:
        json.dump(history, f)

@app.route("/")
def index():
    session_id = get_session_id()
    history = load_history(session_id)
    return render_template("chat.html", history=history)

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/chat", methods=["POST"])
def chat():
    session_id = get_session_id()
    message = request.form.get("message")
    image = request.files.get("image")

    image_path = None
    image_filename = None
    if image:
        filename = secure_filename(image.filename)
        image_filename = f"{session_id}_{filename}"
        image_path = os.path.join(UPLOAD_FOLDER, image_filename)
        image.save(image_path)

    history = load_history(session_id)
    
    # Store user message with image info
    user_message = {
        "role": "user", 
        "content": message,
        "image": image_filename if image_filename else None
    }
    history.append(user_message)

    response = get_groq_response(history.copy(), image_path=image_path)
    history.append({"role": "assistant", "content": response})

    save_history(session_id, history)
    return jsonify({
        "response": response,
        "image": image_filename if image_filename else None
    })

@app.route("/reset", methods=["POST"])
def reset():
    session_id = get_session_id()
    try:
        # Remove history file
        os.remove(get_history_file(session_id))
        
        # Remove uploaded images for this session
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.startswith(f"{session_id}_"):
                os.remove(os.path.join(UPLOAD_FOLDER, filename))
    except FileNotFoundError:
        pass
    return jsonify({"message": "Session reset."})

if __name__ == "__main__":
    app.run(debug=True)