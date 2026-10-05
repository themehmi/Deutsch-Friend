from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import pymongo
from werkzeug.security import generate_password_hash, check_password_hash
import urllib.request
import urllib.error
import json
import re
import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'my_secret_key_123')

MONGO_URI = os.getenv('MongoDB')
if MONGO_URI:
    client = pymongo.MongoClient(MONGO_URI)
    db = client.get_database('deutsch_app')
    users_collection = db.users
    try:
        users_collection.create_index("username", unique=True)
        users_collection.create_index("email", unique=True)
    except Exception as e:
        print("Warning: Could not create unique indexes:", e)
else:
    users_collection = None

@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    show_tutorial = session.pop('show_tutorial', False)
    return render_template('index.html', show_tutorial=show_tutorial)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        
        if users_collection is None:
            flash('Database connection failed.')
            return redirect(url_for('signup'))
            
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_regex, email):
            flash('Invalid email address format.')
            return redirect(url_for('signup'))
            
        if len(password) < 8:
            flash('Password must be at least 8 characters long.')
            return redirect(url_for('signup'))
            
        if users_collection.find_one({'username': username}):
            flash('Username already exists.')
            return redirect(url_for('signup'))
            
        if users_collection.find_one({'email': email}):
            flash('Email already registered.')
            return redirect(url_for('signup'))
        
        hashed_password = generate_password_hash(password)
        users_collection.insert_one({'username': username, 'email': email, 'password': hashed_password, 'is_first_login': True})
        
        flash('Successfully registered. Please log in.')
        return redirect(url_for('login'))
        
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form.get('username', '').strip().lower()
        password = request.form.get('password')
        
        if users_collection is None:
            flash('Database connection failed.')
            return redirect(url_for('login'))
            
        user = users_collection.find_one({
            '$or': [
                {'username': username_or_email},
                {'email': username_or_email}
            ]
        })
        
        if user and check_password_hash(user['password'], password):
            session.permanent = True
            session['username'] = user['username']
            
            if user.get('is_first_login', False):
                session['show_tutorial'] = True
                users_collection.update_one({'_id': user['_id']}, {'$set': {'is_first_login': False}})
                
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.')
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/grammar')
def grammar():
    return render_template('grammar_dashboard.html')

@app.route('/schreiben')
def schreiben():
    return render_template('schreiben_dashboard.html')

@app.route('/sprechen')
def sprechen():
    return render_template('sprechen_dashboard.html')

@app.route('/hoeren')
def hoeren():
    return render_template('hoeren_dashboard.html')

@app.route('/lesen')
def lesen():
    return render_template('lesen_dashboard.html')

@app.route('/quiz')
def quiz():
    return render_template('quiz_dashboard.html')

@app.route('/api/save_preference', methods=['POST'])
def save_preference():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json
    key = data.get('key')
    value = data.get('value')
    
    if key and value and users_collection is not None:
        users_collection.update_one(
            {'username': session['username']},
            {'$set': {f'preferences.{key}': value}}
        )
        return jsonify({"success": True})
    return jsonify({"error": "Invalid data"}), 400

@app.route('/api/get_preferences', methods=['GET'])
def get_preferences():
    if 'username' not in session or users_collection is None:
        return jsonify({})
        
    user = users_collection.find_one({'username': session['username']})
    if user and 'preferences' in user:
        return jsonify(user['preferences'])
    return jsonify({})

@app.route('/api/check_text', methods=['POST'])
def check_text():
    data = request.json
    api_key = data.get('api_key') or os.getenv('API_KEY')
    text = data.get('text')
    prompt = data.get('prompt', 'Korrigiere den Text.')

    if not api_key:
        return jsonify({"error": "API Key is missing."}), 400

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    system_prompt = "You are a friendly, expert German teacher. Grade the user's German text based on the provided writing prompt. Point out grammar, spelling, and style errors and explain the mistakes in English so the student can easily understand. Provide the corrected German text. Finally, give an estimated CEFR level (A1, A2, B1, etc.) for the text. Format your response in clean HTML so it can be directly injected into a div. Use <h3> for headings, <ul> for lists, and <b> for emphasis. Do NOT use markdown code blocks like ```html."
    
    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Prompt/Context: {prompt}\n\nStudent's Text:\n{text}"}
        ],
        "temperature": 0.2,
        "max_tokens": 1024
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            feedback = result['choices'][0]['message']['content']
            return jsonify({"feedback": feedback})
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        print(f"GROQ ERROR: HTTP {e.code}: {error_body}")
        return jsonify({"error": f"HTTP {e.code}: {error_body}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate_scenario', methods=['POST'])
def generate_scenario():
    data = request.json
    api_key = data.get('api_key') or os.getenv('API_KEY')
    topic = data.get('topic')

    if not api_key:
        return jsonify({"error": "API Key is missing."}), 400

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    system_prompt = "You are a German teacher. The student will describe a topic they want to practice writing about in either English or German. You must generate a short, realistic writing task (scenario) and a list of 3-4 bullet points they must include. Write the task instructions in German (to simulate an exam) but provide English translations in parentheses. Keep it concise. Format your response in simple HTML using <p> and <ul> tags."
    
    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Topic: {topic}"}
        ],
        "temperature": 0.5,
        "max_tokens": 512
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            scenario = result['choices'][0]['message']['content']
            return jsonify({"scenario": scenario})
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        return jsonify({"error": f"HTTP {e.code}: {error_body}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    api_key = os.getenv('API_KEY')
    lang = request.form.get('language')
    
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    audio_file = request.files['audio']
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {
        'file': (audio_file.filename, audio_file.stream, audio_file.content_type),
        'model': (None, 'whisper-large-v3'),
        'prompt': (None, 'This is a student speaking German and English. Please transcribe accurately. Hallo, wie geht es dir? Hello, how are you?')
    }
    
    if lang:
        files['language'] = (None, lang)
    
    try:
        res = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files)
        res.raise_for_status()
        return jsonify({"text": res.json().get('text', '')})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    api_key = os.getenv('API_KEY')
    data = request.json
    system_prompt = data.get('system', '')
    messages = data.get('messages', [])
    
    payload_messages = [{"role": "system", "content": system_prompt}] + messages
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": payload_messages,
        "temperature": 0.5,
        "max_tokens": 256
    }
    
    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        res.raise_for_status()
        return jsonify({"reply": res.json()['choices'][0]['message']['content']})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate_listen', methods=['POST'])
def generate_listen():
    api_key = os.getenv('API_KEY')
    data = request.json
    topic = data.get('topic')
    custom_prompt = data.get('custom_prompt')
    
    if not api_key:
        return jsonify({"error": "API Key is missing."}), 400

    prompts = {
        'bahnhof': "Write a short, realistic train station announcement in German (about 3 sentences). E.g. a delayed train or platform change.",
        'wetter': "Write a short, realistic German weather report for tomorrow (about 3 sentences).",
        'nachrichten': "Write a short, realistic German news headline/bulletin (about 3 sentences).",
        'alltag': "Write a short, casual German voice message from a friend (about 3 sentences). E.g. about meeting up or asking a favor."
    }

    if topic == 'custom' and custom_prompt:
        system_prompt = f"Write a short, realistic German listening exercise text (about 3 sentences) based on this scenario: '{custom_prompt}'."
    else:
        system_prompt = prompts.get(topic, "Write 3 short German sentences.")
    
    level = data.get('level', 'A1')
    system_prompt += f" Strictly adapt your vocabulary and grammar to the {level} CEFR language level."
    
    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [
            {"role": "system", "content": "You are a German text generator. Output strictly the German text and nothing else. No markdown, no quotes, no English translations. Just the raw German text."},
            {"role": "user", "content": system_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 128
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        res.raise_for_status()
        transcript = res.json()['choices'][0]['message']['content'].strip()
        return jsonify({"transcript": transcript})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate_lesen', methods=['POST'])
def generate_lesen():
    api_key = os.getenv('API_KEY')
    data = request.json
    topic = data.get('topic')
    custom_prompt = data.get('custom_prompt')
    
    if not api_key:
        return jsonify({"error": "API Key is missing."}), 400

    prompts = {
        'email': "Write a B1-level German email (about 80 words). Below the email, write 3 reading comprehension questions in German.",
        'blog': "Write a B1-level German blog post (about 80 words). Below the post, write 3 reading comprehension questions in German.",
        'news': "Write a B1-level German short news article (about 80 words). Below the article, write 3 reading comprehension questions in German.",
        'story': "Write a B1-level German short story (about 80 words). Below the story, write 3 reading comprehension questions in German."
    }
    
    if topic == 'custom' and custom_prompt:
        system_prompt = f"Write a B1-level German text about: '{custom_prompt}'. Below the text, write 3 reading comprehension questions in German."
    else:
        system_prompt = prompts.get(topic, prompts['email'])
        
    level = data.get('level', 'A1')
    system_prompt += f" Strictly adapt your vocabulary and grammar to the {level} CEFR language level."
        
    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [
            {"role": "system", "content": "You are a German teacher. Output strictly the German text followed immediately by 3 questions. No markdown, no English translations."},
            {"role": "user", "content": system_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 512
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        res.raise_for_status()
        text = res.json()['choices'][0]['message']['content'].strip()
        return jsonify({"text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/quiz_chat', methods=['POST'])
def quiz_chat():
    api_key = os.getenv('API_KEY')
    data = request.json
    messages = data.get('messages', [])
    
    if not api_key:
        return jsonify({"error": "API Key is missing."}), 400

    system_prompt = "You are a friendly German teacher and language learning assistant. The user can ask you to explain any German grammar topic, request specific exercises, ask for translations, or anything else related to learning German. You must communicate with the user in English by default, unless they request otherwise. When they ask for exercises, generate them clearly with an answer key at the end. Format your responses beautifully in HTML (e.g., using <h3>, <p>, <ul>, <li>, <b>). Do NOT use markdown code blocks like ```html."
    
    payload_messages = [{"role": "system", "content": system_prompt}] + messages
    
    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": payload_messages,
        "temperature": 0.7,
        "max_tokens": 2048
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        res.raise_for_status()
        reply_html = res.json()['choices'][0]['message']['content'].strip()
        return jsonify({"reply": reply_html})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/check_speech', methods=['POST'])
def check_speech():
    api_key = os.getenv('API_KEY')
    data = request.json
    text = data.get('text', '')

    system = data.get('system', '')

    if not api_key:
        return jsonify({"error": "API Key is missing."}), 400
    if not text:
        return jsonify({"correction": None}), 200

    system_prompt = (
        "You are a strict but friendly German grammar checker for language learners. "
        "The user will give you a sentence they just SPOKE in German. "
        "Your job is twofold: \n"
        "1. Check if the sentence makes sense in the context of the current scenario/topic. \n"
        f"The current scenario context is: '{system}'\n"
        "2. Carefully check for grammar, vocabulary, word order, or article errors.\n"
        "If the sentence is ON TOPIC and grammatically CORRECT, reply with exactly the word: OK\n"
        "If the sentence is OFF TOPIC or has mistakes, reply with a SHORT HTML snippet (no surrounding tags like <html> or <body>). "
        "Use this exact format:\n"
        "<b>✏️ Korrektur:</b> <span style='color:#7ee787'>[corrected sentence or on-topic suggestion here]</span><br>"
        "<b>💡 Erklärung:</b> [brief explanation in English of what was wrong grammatically, or why it was off-topic and what they should have said instead]"
        "Do NOT add any extra commentary, greetings, or markdown."
    )

    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        "temperature": 0.1,
        "max_tokens": 256
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        res.raise_for_status()
        result = res.json()['choices'][0]['message']['content'].strip()
        if result == "OK":
            return jsonify({"correction": None})
        return jsonify({"correction": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/dictionary', methods=['POST'])
def dictionary_translate():
    api_key = os.getenv('API_KEY')
    data = request.json
    word = data.get('word', '')
    
    if not api_key:
        return jsonify({"error": "API Key is missing. Add it in the backend."}), 400
    if not word:
        return jsonify({"error": "Word is missing."}), 400

    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [
            {"role": "system", "content": "You are a bilingual German-English dictionary assistant. If the user provides a German word, reply with its English translation; if English, reply with German (include the definite article der/die/das for nouns). IMPORTANT: If the user provides a verb in ANY form (e.g., 'gegangen', 'mache', 'write'), provide the translation, identify its current grammatical form, and provide the infinitive. ALWAYS automatically include the following verb conjugations for the infinitive: Partizip II (Perfekt), Präteritum (Past), Futur I, and Futur II. Keep responses strictly focused on translation and grammatical forms, neatly formatted without conversational filler."},
            {"role": "user", "content": word}
        ],
        "temperature": 0.3,
        "max_tokens": 256
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        res.raise_for_status()
        translation = res.json()['choices'][0]['message']['content'].strip()
        return jsonify({"translation": translation})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)



