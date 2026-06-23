import requests, time, json, os

TOKEN = '8673968862:AAGWsC9DmSZ-zbGYqCTZjWRrMiewcNGk4BQ'
OR_KEY = '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'

MODELS = [
"z-ai/glm-4.5-air:free",
"qwen/qwen3.6-plus:free",
"meta-llama/llama-3.3-70b-instruct:free"
]

last_id = 0
user_modes = {}
user_memory = {}
processed = set()

stats = {
"messages": 0,
"ai_requests": 0,
"users": {}
}

---------- ЗАГРУЗКА ----------

def load_json(name, default):
try:
if os.path.exists(name):
with open(name, "r") as f:
data = json.load(f)
if isinstance(data, type(default)):
return data
except:
pass
return default

stats = load_json("stats.json", stats)
user_memory = load_json("memory.json", {})
user_modes = load_json("modes.json", {})

session = requests.Session()

print("бот запущен")

---------- СОХРАНЕНИЕ ----------

def save_all():
try:
with open("stats.tmp", "w") as f:
json.dump(stats, f)
os.replace("stats.tmp", "stats.json")

with open("memory.tmp", "w") as f:  
        json.dump(user_memory, f)  
    os.replace("memory.tmp", "memory.json")  

    with open("modes.tmp", "w") as f:  
        json.dump(user_modes, f)  
    os.replace("modes.tmp", "modes.json")  
except Exception as e:  
    print("save error:", e)

---------- TG ----------

def send(chat, text, keyboard=None):
if not text:
text = "🤖 Ошибка ответа"

data = {'chat_id': chat, 'text': text}  
if keyboard:  
    data['reply_markup'] = keyboard  

try:  
    r = session.post(  
        f'https://api.telegram.org/bot{TOKEN}/sendMessage',  
        json=data,  
        timeout=10  
    )  

    if r.status_code != 200:  
        print("TG ERROR:", r.text)  

except Exception as e:  
    print("send error:", e)

def typing(chat):
try:
session.post(
f'https://api.telegram.org/bot{TOKEN}/sendChatAction',
json={'chat_id': chat, 'action': 'typing'},
timeout=5
)
except:
pass

def menu():
return {
"keyboard": [
["🎭 Режим", "📊 Аналитика"],
["🧹 Очистить память"]
],
"resize_keyboard": True
}

---------- СТИЛЬ ----------

def get_mode_prompt(mode):
base = "Ты человек в чате. Пиши коротко и живо."
if mode == "rude":
return base + " Будь дерзким."
elif mode == "slave":
return base + " Будь максимально вежливым."
return base

---------- ПАМЯТЬ ----------

def update_memory(chat, role, content):
if chat not in user_memory:
user_memory[chat] = []

user_memory[chat].append({  
    "role": role,  
    "content": str(content)[:300]  
})  

user_memory[chat] = user_memory[chat][-8:]

---------- AI ----------

def ask_ai(chat, text, mode_prompt):
for model in MODELS:
try:
messages = [{"role": "system", "content": mode_prompt}]
messages += user_memory.get(chat, [])
messages.append({"role": "user", "content": text})

r = session.post(  
            "https://openrouter.ai/api/v1/chat/completions",  
            headers={  
                "Authorization": f"Bearer {OR_KEY}",  
                "Content-Type": "application/json"  
            },  
            json={  
                "model": model,  
                "messages": messages,  
                "max_tokens": 200,  
                "temperature": 0.7  
            },  
            timeout=15  
        )  

        if r.status_code != 200:  
            print("OR ERROR:", r.text)  
            continue  

        try:  
            data = r.json()  
        except:  
            continue  

        choices = data.get("choices")  
        if not choices:  
            continue  

        msg = choices[0].get("message", {})  
        reply = msg.get("content")  

        # фикс форматов  
        if isinstance(reply, list):  
            reply = "".join(  
                x.get("text", "") for x in reply if isinstance(x, dict)  
            )  

        if not isinstance(reply, str):  
            reply = str(reply)  

        if not reply.strip():  
            continue  

        stats["ai_requests"] += 1  

        update_memory(chat, "user", text)  
        update_memory(chat, "assistant", reply)  

        return reply  

    except Exception as e:  
        print("AI error:", model, e)  

return "⚠️ ИИ не ответил"

---------- LOOP ----------

while True:
try:
r = session.get(
f'https://api.telegram.org/bot{TOKEN}/getUpdates',
params={'offset': last_id + 1, 'timeout': 25},
timeout=30
)

if r.status_code != 200:  
        print("TG GET ERROR:", r.text)  
        time.sleep(2)  
        continue  

    try:  
        data = r.json()  
        if not data.get("ok"):  
            continue  
    except:  
        continue  

    for upd in data.get('result', []):  
        last_id = upd['update_id']  

        if last_id in processed:  
            continue  

        processed.add(last_id)  

        # фикс дублей (НЕ clear)  
        if len(processed) > 200:  
            processed = set(list(processed)[-100:])  

        msg = upd.get('message')  
        if not msg:  
            continue  

        chat = msg['chat']['id']  
        chat_str = str(chat)  
        text = msg.get('text', '').strip()  

        if not text:  
            continue  

        stats["messages"] += 1  
        stats["users"][chat_str] = stats["users"].get(chat_str, 0) + 1  

        if text == '/start':  
            user_memory[chat_str] = []  
            user_modes[chat_str] = "normal"  
            send(chat, "🚀 Бот запущен", menu())  

        elif text in ['🧹 Очистить память', '/clear']:  
            user_memory[chat_str] = []  
            send(chat, "🧠 Память очищена", menu())  

        elif text == '🎭 Режим':  
            cur = user_modes.get(chat_str, "normal")  
            new = "rude" if cur == "normal" else "slave" if cur == "rude" else "normal"  
            user_modes[chat_str] = new  
            send(chat, f"🎭 Режим: {new}", menu())  

        elif text == '📊 Аналитика':  
            send(chat,  
                f"📊 Статистика:\n"  
                f"👥 Юзеров: {len(stats['users'])}\n"  
                f"💬 Сообщений: {stats['messages']}\n"  
                f"🧠 ИИ: {stats['ai_requests']}",  
                menu()  
            )  

        else:  
            typing(chat)  

            mode = user_modes.get(chat_str, "normal")  
            prompt = get_mode_prompt(mode)  

            reply = ask_ai(chat_str, text, prompt)  
            send(chat, reply, menu())  

        if stats["messages"] % 10 == 0:  
            save_all()  

    time.sleep(0.2)  

except Exception as e:  
    print("loop error:", e)  
    time.sleep(2)
