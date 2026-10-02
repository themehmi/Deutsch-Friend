from flask import Flask, render_template, request, jsonify
import urllib.request
import urllib.error
import json
import os
from dotenv import load_dotenv

load_dotenv(override=True)

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/grammar')
def grammar():
    return render_template('grammar_dashboard.html')

@app.route('/schreiben')
def schreiben():
    return render_template('schreiben_dashboard.html')

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

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
