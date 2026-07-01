from flask import Flask, request, jsonify, render_template_string
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# ═══════════════════════════════════════════════
# ⚙️ КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════
KEYS_FILE = "keys.json"
BETA_DURATION_DAYS = 30

# ═══════════════════════════════════════════════
# 🔑 БАЗА КЛЮЧЕЙ
# ═══════════════════════════════════════════════
def load_keys():
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_keys():
    with open(KEYS_FILE, 'w') as f:
        json.dump(keys, f, indent=2)

# Загружаем ключи при старте
keys = load_keys()

# Если база пустая - добавляем тестовые ключи
if not keys:
    keys = {
        "SCARED-BASIC-TEST01": {
            "used": False,
            "tier": "BASIC",
            "hwid": None,
            "first_ip": None,
            "activated_at": None,
            "expires_at": None,
            "banned": False
        },
        "SCARED-PREM-TEST01": {
            "used": False,
            "tier": "PREMIUM",
            "hwid": None,
            "first_ip": None,
            "activated_at": None,
            "expires_at": None,
            "banned": False
        }
    }
    save_keys()

# ═══════════════════════════════════════════════
# 🎨 ИНТЕРФЕЙС АДМИНКИ
# ═══════════════════════════════════════════════
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Scared Opti - Admin Panel</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            margin-bottom: 40px;
            padding: 30px;
            background: rgba(22, 22, 35, 0.6);
            border-radius: 16px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        
        h1 {
            font-size: 36px;
            background: linear-gradient(135deg, #7c5cff, #9d4eff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #888;
            font-size: 14px;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        
        .stat-card {
            background: rgba(22, 22, 35, 0.6);
            padding: 24px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(10px);
            transition: all 0.3s;
        }
        
        .stat-card:hover {
            transform: translateY(-4px);
            border-color: rgba(124, 92, 255, 0.3);
            box-shadow: 0 8px 32px rgba(124, 92, 255, 0.2);
        }
        
        .stat-label {
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        
        .stat-value {
            font-size: 32px;
            font-weight: 700;
            color: #7c5cff;
        }
        
        .controls {
            background: rgba(22, 22, 35, 0.6);
            padding: 24px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            margin-bottom: 30px;
        }
        
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #7c5cff, #9d4eff);
            color: #fff;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(124, 92, 255, 0.4);
        }
        
        .btn-danger {
            background: rgba(255, 71, 87, 0.2);
            color: #ff4757;
            border: 1px solid #ff4757;
        }
        
        .btn-danger:hover {
            background: #ff4757;
            color: #fff;
        }
        
        .btn-success {
            background: rgba(0, 214, 143, 0.2);
            color: #00d68f;
            border: 1px solid #00d68f;
        }
        
        .btn-success:hover {
            background: #00d68f;
            color: #fff;
        }
        
        .keys-list {
            background: rgba(22, 22, 35, 0.6);
            padding: 24px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        
        .key-item {
            background: rgba(10, 10, 15, 0.6);
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 12px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            transition: all 0.3s;
        }
        
        .key-item:hover {
            border-color: rgba(124, 92, 255, 0.3);
        }
        
        .key-item.banned {
            border-color: #ff4757;
            background: rgba(255, 71, 87, 0.05);
        }
        
        .key-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .key-code {
            font-family: 'Courier New', monospace;
            font-size: 16px;
            font-weight: 600;
            color: #7c5cff;
        }
        
        .key-tier {
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
        }
        
        .tier-basic {
            background: rgba(74, 144, 226, 0.2);
            color: #4a90e2;
        }
        
        .tier-premium {
            background: rgba(255, 215, 0, 0.2);
            color: #ffd700;
        }
        
        .tier-owner {
            background: rgba(255, 42, 42, 0.2);
            color: #ff2a2a;
        }
        
        .key-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 12px;
            margin-bottom: 16px;
            font-size: 13px;
        }
        
        .info-item {
            color: #888;
        }
        
        .info-item strong {
            color: #fff;
        }
        
        .key-actions {
            display: flex;
            gap: 10px;
        }
        
        .status-badge {
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
        }
        
        .status-unused {
            background: rgba(0, 214, 143, 0.2);
            color: #00d68f;
        }
        
        .status-used {
            background: rgba(255, 165, 2, 0.2);
            color: #ffa502;
        }
        
        .status-banned {
            background: rgba(255, 71, 87, 0.2);
            color: #ff4757;
        }
        
        .add-key-form {
            display: flex;
            gap: 12px;
            margin-bottom: 20px;
        }
        
        .add-key-form input, .add-key-form select {
            padding: 12px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            background: rgba(10, 10, 15, 0.6);
            color: #fff;
            font-size: 14px;
        }
        
        .add-key-form input {
            flex: 1;
        }
        
        .add-key-form select {
            min-width: 150px;
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #888;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔐 Scared Opti Admin Panel</h1>
            <div class="subtitle">Управление лицензиями и защита от шаринга</div>
        </header>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">Всего ключей</div>
                <div class="stat-value" id="totalKeys">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Активных</div>
                <div class="stat-value" id="activeKeys">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Забанено</div>
                <div class="stat-value" id="bannedKeys">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Не использовано</div>
                <div class="stat-value" id="unusedKeys">0</div>
            </div>
        </div>
        
        <div class="controls">
            <h3 style="margin-bottom: 16px;">Добавить новый ключ</h3>
            <div class="add-key-form">
                <input type="text" id="newKey" placeholder="SCARED-BASIC-XXXXXXXX">
                <select id="newTier">
                    <option value="BASIC">BASIC</option>
                    <option value="PREMIUM">PREMIUM</option>
                    <option value="OWNER">OWNER</option>
                </select>
                <button class="btn btn-primary" onclick="addKey()">Добавить</button>
            </div>
        </div>
        
        <div class="keys-list">
            <h3 style="margin-bottom: 20px;">Все ключи</h3>
            <div id="keysContainer"></div>
        </div>
    </div>

    <script>
        async function loadKeys() {
            const response = await fetch('/api/admin/keys');
            const data = await response.json();
            
            const container = document.getElementById('keysContainer');
            
            if (data.keys.length === 0) {
                container.innerHTML = '<div class="empty-state">Нет ключей. Добавьте первый ключ выше.</div>';
                return;
            }
            
            container.innerHTML = data.keys.map(key => `
                <div class="key-item ${key.banned ? 'banned' : ''}">
                    <div class="key-header">
                        <div class="key-code">${key.key}</div>
                        <div class="key-tier tier-${key.tier.toLowerCase()}">${key.tier}</div>
                    </div>
                    <div class="key-info">
                        <div class="info-item">
                            <strong>Статус:</strong> 
                            <span class="status-badge status-${key.banned ? 'banned' : (key.used ? 'used' : 'unused')}">
                                ${key.banned ? 'ЗАБАНЕН' : (key.used ? 'Использован' : 'Не использован')}
                            </span>
                        </div>
                        ${key.used ? `
                            <div class="info-item"><strong>HWID:</strong> ${key.hwid || 'N/A'}</div>
                            <div class="info-item"><strong>IP:</strong> ${key.first_ip || 'N/A'}</div>
                            <div class="info-item"><strong>Активирован:</strong> ${key.activated_at || 'N/A'}</div>
                            <div class="info-item"><strong>Истекает:</strong> ${key.expires_at || 'N/A'}</div>
                        ` : ''}
                    </div>
                    <div class="key-actions">
                        ${key.banned ? 
                            `<button class="btn btn-success" onclick="unbanKey('${key.key}')">Разбанить</button>` :
                            `<button class="btn btn-danger" onclick="banKey('${key.key}')">Забанить</button>`
                        }
                        <button class="btn btn-danger" onclick="deleteKey('${key.key}')">Удалить</button>
                    </div>
                </div>
            `).join('');
            
            // Обновляем статистику
            document.getElementById('totalKeys').textContent = data.stats.total;
            document.getElementById('activeKeys').textContent = data.stats.active;
            document.getElementById('bannedKeys').textContent = data.stats.banned;
            document.getElementById('unusedKeys').textContent = data.stats.unused;
        }
        
        async function addKey() {
            const key = document.getElementById('newKey').value.trim();
            const tier = document.getElementById('newTier').value;
            
            if (!key) {
                alert('Введите ключ!');
                return;
            }
            
            const response = await fetch('/api/admin/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({key, tier})
            });
            
            const data = await response.json();
            
            if (data.status === 'ok') {
                document.getElementById('newKey').value = '';
                loadKeys();
            } else {
                alert('Ошибка: ' + data.message);
            }
        }
        
        async function banKey(key) {
            if (!confirm(`Забанить ключ ${key}?`)) return;
            
            await fetch('/api/admin/ban', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({key})
            });
            
            loadKeys();
        }
        
        async function unbanKey(key) {
            if (!confirm(`Разбанить ключ ${key}?`)) return;
            
            await fetch('/api/admin/unban', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({key})
            });
            
            loadKeys();
        }
        
        async function deleteKey(key) {
            if (!confirm(`Удалить ключ ${key}? Это действие необратимо!`)) return;
            
            await fetch('/api/admin/delete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({key})
            });
            
            loadKeys();
        }
        
        // Загружаем ключи при старте
        loadKeys();
        
        // Автообновление каждые 5 секунд
        setInterval(loadKeys, 5000);
    </script>
</body>
</html>
"""

# ═══════════════════════════════════════════════
# 🌐 МАРШРУТЫ
# ═══════════════════════════════════════════════

@app.route("/")
def home():
    """Админ-панель"""
    return render_template_string(ADMIN_HTML)

@app.route("/activate", methods=["POST"])
def activate():
    """API активации ключа с защитой от шаринга"""
    data = request.json
    key = data.get("key", "").strip().upper()
    hwid = data.get("hwid", "").strip()
    client_ip = request.remote_addr
    
    if not key:
        return jsonify({"status": "error", "message": "No key provided"})
    
    # Ключ не существует
    if key not in keys:
        return jsonify({"status": "invalid", "message": "Key not found"})
    
    key_data = keys[key]
    
    # Ключ забанен
    if key_data.get("banned", False):
        return jsonify({
            "status": "banned",
            "message": "SHARING DETECTED. Contact support in discord."
        })
    
    # Проверка срока действия
    if key_data.get("expires_at"):
        try:
            expires = datetime.fromisoformat(key_data["expires_at"])
            if datetime.now() > expires:
                return jsonify({"status": "expired", "message": "License expired"})
        except:
            pass
    
    # Первый запуск - активируем
    if not key_data["used"]:
        key_data["used"] = True
        key_data["hwid"] = hwid
        key_data["first_ip"] = client_ip
        key_data["activated_at"] = datetime.now().isoformat()
        
        # Устанавливаем срок действия (30 дней для беты)
        expires = datetime.now() + timedelta(days=BETA_DURATION_DAYS)
        key_data["expires_at"] = expires.isoformat()
        
        save_keys()
        
        return jsonify({
            "status": "ok",
            "tier": key_data["tier"],
            "expires_at": int(expires.timestamp())
        })
    
    # Уже использован - проверяем HWID и IP
    if key_data["hwid"] != hwid:
        # РАЗНЫЕ HWID - ЭТО ШАРИНГ!
        key_data["banned"] = True
        save_keys()
        
        return jsonify({
            "status": "banned",
            "message": "SHARING DETECTED. Contact support in discord."
        })
    
    # Если IP изменился, но HWID тот же - это нормально (динамический IP)
    # Но если хочешь жесткую привязку к IP - раскомментируй:
    # if key_data["first_ip"] != client_ip:
    #     key_data["banned"] = True
    #     save_keys()
    #     return jsonify({
    #         "status": "banned",
    #         "message": "SHARING DETECTED. Contact support in discord."
    #     })
    
    # Всё ок - ключ валиден
    expires_at = 0
    if key_data.get("expires_at"):
        try:
            expires = datetime.fromisoformat(key_data["expires_at"])
            expires_at = int(expires.timestamp())
        except:
            pass
    
    return jsonify({
        "status": "ok",
        "tier": key_data["tier"],
        "expires_at": expires_at
    })

# ═══════════════════════════════════════════════
# 🔧 API АДМИНКИ
# ═══════════════════════════════════════════════

@app.route("/api/admin/keys")
def admin_get_keys():
    """Получить все ключи для админки"""
    keys_list = []
    stats = {"total": 0, "active": 0, "banned": 0, "unused": 0}
    
    for key, data in keys.items():
        keys_list.append({
            "key": key,
            "tier": data.get("tier", "BASIC"),
            "used": data.get("used", False),
            "hwid": data.get("hwid"),
            "first_ip": data.get("first_ip"),
            "activated_at": data.get("activated_at"),
            "expires_at": data.get("expires_at"),
            "banned": data.get("banned", False)
        })
        
        stats["total"] += 1
        if data.get("banned"):
            stats["banned"] += 1
        elif data.get("used"):
            stats["active"] += 1
        else:
            stats["unused"] += 1
    
    return jsonify({"keys": keys_list, "stats": stats})

@app.route("/api/admin/add", methods=["POST"])
def admin_add_key():
    """Добавить новый ключ"""
    data = request.json
    key = data.get("key", "").strip().upper()
    tier = data.get("tier", "BASIC")
    
    if not key:
        return jsonify({"status": "error", "message": "Key is required"})
    
    if key in keys:
        return jsonify({"status": "error", "message": "Key already exists"})
    
    keys[key] = {
        "used": False,
        "tier": tier,
        "hwid": None,
        "first_ip": None,
        "activated_at": None,
        "expires_at": None,
        "banned": False
    }
    
    save_keys()
    return jsonify({"status": "ok", "message": "Key added"})

@app.route("/api/admin/ban", methods=["POST"])
def admin_ban_key():
    """Забанить ключ"""
    data = request.json
    key = data.get("key")
    
    if key in keys:
        keys[key]["banned"] = True
        save_keys()
        return jsonify({"status": "ok"})
    
    return jsonify({"status": "error", "message": "Key not found"})

@app.route("/api/admin/unban", methods=["POST"])
def admin_unban_key():
    """Разбанить ключ"""
    data = request.json
    key = data.get("key")
    
    if key in keys:
        keys[key]["banned"] = False
        save_keys()
        return jsonify({"status": "ok"})
    
    return jsonify({"status": "error", "message": "Key not found"})

@app.route("/api/admin/delete", methods=["POST"])
def admin_delete_key():
    """Удалить ключ"""
    data = request.json
    key = data.get("key")
    
    if key in keys:
        del keys[key]
        save_keys()
        return jsonify({"status": "ok"})
    
    return jsonify({"status": "error", "message": "Key not found"})

# ═══════════════════════════════════════════════
# 🚀 ЗАПУСК
# ═══════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("🔐 Scared Opti Server v2.0")
    print("=" * 60)
    print(f"📊 Загружено ключей: {len(keys)}")
    print(f"🌐 Админ-панель: http://localhost:10000")
    print(f"🔑 API активации: http://localhost:10000/activate")
    print("=" * 60)
    app.run(host="0.0.0.0", port=10000, debug=True)
