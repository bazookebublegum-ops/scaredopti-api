"""
Scared Opti — combined service
================================
Один процесс, один Render Web Service:
  - Flask (админка + API проверки/активации ключей) крутится в фоновом потоке
  - Discord-бот scaredREV крутится в главном потоке (bot.run блокирующий)

Раньше это были два отдельных файла (server.py и bot.py) на двух отдельных
Render-сервисах. Логика НЕ менялась ни на бит — просто оба куска склеены в
один файл и запускаются в одном процессе, чтобы не тратить лимит часов
Render на два инстанса.

Переменные окружения (те же, что были у обоих сервисов раньше):
  DISCORD_TOKEN, GUILD_ID, PANEL_CHANNEL_ID, MOD_CHANNEL_ID,
  PUBLIC_REVIEWS_CHANNEL_ID, LICENSE_API_URL, SELF_URL,
  MASCOT_THUMBNAIL_URL, PORT (Render подставляет сам)
"""

import os
import json
import threading
import datetime
from datetime import datetime as dt, timedelta
from typing import Optional

import requests
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from flask import Flask, request, jsonify, render_template_string

# ═══════════════════════════════════════════════
# ⚙️ ЧАСТЬ 1: FLASK — АДМИНКА + API КЛЮЧЕЙ (было server.py)
# ═══════════════════════════════════════════════

app = Flask(__name__)

KEYS_FILE = "keys.json"
BETA_DURATION_DAYS = 30

DISCORD_WEBHOOK_URL = os.getenv(
    "DISCORD_WEBHOOK_URL",
    "https://discord.com/api/webhooks/1523045988401549396/NxEa66M65uPCdyN68E-pdv4byp7EehCxR0biNUt7ZaZ_XN7qPtkXC3zDyYhRB1LUlNEN",
)


def send_discord_alert(title, description, color=0xFF0000):
    """Отправляет Embed-уведомление в Discord через webhook."""
    if not DISCORD_WEBHOOK_URL or "https://discord.com/api/webhooks/1523045988401549396/NxEa66M65uPCdyN68E-pdv4byp7EehCxR0biNUt7ZaZ_XN7qPtkXC3zDyYhRB1LUlNEN" in DISCORD_WEBHOOK_URL:
        return
    try:
        payload = {
            "embeds": [{
                "title": title,
                "description": description,
                "color": color,
                "timestamp": dt.now().isoformat(),
                "footer": {"text": "Scared Opti Security System"}
            }]
        }
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        print(f"[DISCORD ERROR] Failed to send alert: {e}")


ALL_KEYS_DATA = {
    # BASIC KEYS (60)
    "SCARED-BASIC-0GRF5A4M": "BASIC", "SCARED-BASIC-0MVAPYIX": "BASIC",
    "SCARED-BASIC-0P55CST0": "BASIC", "SCARED-BASIC-0UPJ6X4H": "BASIC",
    "SCARED-BASIC-16FYFTFQ": "BASIC", "SCARED-BASIC-1KX1H92I": "BASIC",
    "SCARED-BASIC-39VA4A62": "BASIC", "SCARED-BASIC-3DRANVCN": "BASIC",
    "SCARED-BASIC-53AF32WY": "BASIC", "SCARED-BASIC-5TCSMO0W": "BASIC",
    "SCARED-BASIC-5ZX65IFA": "BASIC", "SCARED-BASIC-7BY9KLBA": "BASIC",
    "SCARED-BASIC-7F969OL7": "BASIC", "SCARED-BASIC-7GIU1GUY": "BASIC",
    "SCARED-BASIC-7TWIKDSV": "BASIC", "SCARED-BASIC-88050UMG": "BASIC",
    "SCARED-BASIC-8I0L9S1Y": "BASIC", "SCARED-BASIC-B6U9UEJF": "BASIC",
    "SCARED-BASIC-B99CKJZ0": "BASIC", "SCARED-BASIC-CAU78JM9": "BASIC",
    "SCARED-BASIC-CERGLLHO": "BASIC", "SCARED-BASIC-ED1AYH81": "BASIC",
    "SCARED-BASIC-EXFSSLHB": "BASIC", "SCARED-BASIC-EXGIMMN3": "BASIC",
    "SCARED-BASIC-FJSNY16U": "BASIC", "SCARED-BASIC-G2SJ4AVQ": "BASIC",
    "SCARED-BASIC-G94PU2YO": "BASIC", "SCARED-BASIC-GYLFJYWQ": "BASIC",
    "SCARED-BASIC-HG9LJYEW": "BASIC", "SCARED-BASIC-HO4I7JRF": "BASIC",
    "SCARED-BASIC-HYKMDOZE": "BASIC", "SCARED-BASIC-I0YY22MP": "BASIC",
    "SCARED-BASIC-I2KKGZ7Y": "BASIC", "SCARED-BASIC-IDU3649G": "BASIC",
    "SCARED-BASIC-IEAR3TKM": "BASIC", "SCARED-BASIC-JAP4LKQ7": "BASIC",
    "SCARED-BASIC-LGWYVT61": "BASIC", "SCARED-BASIC-MHU0TIHC": "BASIC",
    "SCARED-BASIC-MRJNU1PJ": "BASIC", "SCARED-BASIC-N5YCZ0G2": "BASIC",
    "SCARED-BASIC-NHQ0K4N7": "BASIC", "SCARED-BASIC-O4TGRRZ6": "BASIC",
    "SCARED-BASIC-O6GV9ZJ1": "BASIC", "SCARED-BASIC-P3MQPS3O": "BASIC",
    "SCARED-BASIC-PMZJME7A": "BASIC", "SCARED-BASIC-Q0XE3ZJL": "BASIC",
    "SCARED-BASIC-Q60ORSWJ": "BASIC", "SCARED-BASIC-SIY657E3": "BASIC",
    "SCARED-BASIC-SLSRV5EV": "BASIC", "SCARED-BASIC-SPHHRT5Z": "BASIC",
    "SCARED-BASIC-TB1YJ3KV": "BASIC", "SCARED-BASIC-TFVVX548": "BASIC",
    "SCARED-BASIC-U6GB3KOY": "BASIC", "SCARED-BASIC-V5Z15U46": "BASIC",
    "SCARED-BASIC-V9RPP3FY": "BASIC", "SCARED-BASIC-VV7IP3O1": "BASIC",
    "SCARED-BASIC-XLZQDCKM": "BASIC", "SCARED-BASIC-Z9Q2FXE7": "BASIC",
    "SCARED-BASIC-ZIMZNHJR": "BASIC", "SCARED-BASIC-ZT0JRIYO": "BASIC",

    # PREMIUM KEYS (60)
    "SCARED-PREM-01LEM9O1": "PREMIUM", "SCARED-PREM-0FBM2MPP": "PREMIUM",
    "SCARED-PREM-107RQOJ1": "PREMIUM", "SCARED-PREM-10LN3WBH": "PREMIUM",
    "SCARED-PREM-1CKMM6R7": "PREMIUM", "SCARED-PREM-1MZIFYIK": "PREMIUM",
    "SCARED-PREM-3027OZNN": "PREMIUM", "SCARED-PREM-329P0GOA": "PREMIUM",
    "SCARED-PREM-3PSYL9FS": "PREMIUM", "SCARED-PREM-40YBBXCE": "PREMIUM",
    "SCARED-PREM-46XTOAMS": "PREMIUM", "SCARED-PREM-4BZPTGJ3": "PREMIUM",
    "SCARED-PREM-4J9L0ARQ": "PREMIUM", "SCARED-PREM-53HEFPAW": "PREMIUM",
    "SCARED-PREM-6BVERWWU": "PREMIUM", "SCARED-PREM-6HKXW9S3": "PREMIUM",
    "SCARED-PREM-7C9OBUS0": "PREMIUM", "SCARED-PREM-AFGB3VQI": "PREMIUM",
    "SCARED-PREM-AHAA21MF": "PREMIUM", "SCARED-PREM-AJH2HHRE": "PREMIUM",
    "SCARED-PREM-CT055VX9": "PREMIUM", "SCARED-PREM-EGGURNEY": "PREMIUM",
    "SCARED-PREM-F38KD12Z": "PREMIUM", "SCARED-PREM-F7U9VNZF": "PREMIUM",
    "SCARED-PREM-G3HJ1UBF": "PREMIUM", "SCARED-PREM-IIHRFPQV": "PREMIUM",
    "SCARED-PREM-JG6G8V42": "PREMIUM", "SCARED-PREM-JNCWF97A": "PREMIUM",
    "SCARED-PREM-K3SP5MWO": "PREMIUM", "SCARED-PREM-KEN8FDS8": "PREMIUM",
    "SCARED-PREM-KGVM7TBN": "PREMIUM", "SCARED-PREM-KJY3WDUE": "PREMIUM",
    "SCARED-PREM-KO68N7SD": "PREMIUM", "SCARED-PREM-LL2M2Q5C": "PREMIUM",
    "SCARED-PREM-M8Y7FF8O": "PREMIUM", "SCARED-PREM-OE53FDZ9": "PREMIUM",
    "SCARED-PREM-QSI9HVC5": "PREMIUM", "SCARED-PREM-QU6VA5BJ": "PREMIUM",
    "SCARED-PREM-SZANYS01": "PREMIUM", "SCARED-PREM-TGRWR6TF": "PREMIUM",
    "SCARED-PREM-THPZLWMV": "PREMIUM", "SCARED-PREM-U5VXE1KR": "PREMIUM",
    "SCARED-PREM-UPFODCFH": "PREMIUM", "SCARED-PREM-VASUPEW2": "PREMIUM",
    "SCARED-PREM-VSKC4FV4": "PREMIUM", "SCARED-PREM-VUJBV74K": "PREMIUM",
    "SCARED-PREM-VXECK2LR": "PREMIUM", "SCARED-PREM-W2JPAW11": "PREMIUM",
    "SCARED-PREM-WLJOV9NV": "PREMIUM", "SCARED-PREM-X1L9H8TS": "PREMIUM",
    "SCARED-PREM-XC27B7YC": "PREMIUM", "SCARED-PREM-XEG1S1OD": "PREMIUM",
    "SCARED-PREM-XMT2J7HZ": "PREMIUM", "SCARED-PREM-XOZ3WSIU": "PREMIUM",
    "SCARED-PREM-XWQ28MKC": "PREMIUM", "SCARED-PREM-YB2JXI6A": "PREMIUM",
    "SCARED-PREM-YJUMV7LT": "PREMIUM", "SCARED-PREM-YO2EMVKN": "PREMIUM",
    "SCARED-PREM-ZR3SGYI0": "PREMIUM", "SCARED-PREM-ZUVBT0RX": "PREMIUM",

    # OWNER KEYS (4)
    "SCARED-OWNER-GODMODE": "OWNER", "SCARED-OWNER-ALPHA01": "OWNER",
    "SCARED-OWNER-BETA002": "OWNER", "SCARED-OWNER-DELTA03": "OWNER"
}


def load_keys():
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_keys():
    with open(KEYS_FILE, 'w') as f:
        json.dump(keys, f, indent=2)


keys = load_keys()

if not keys:
    for key, tier in ALL_KEYS_DATA.items():
        keys[key] = {
            "used": False, "tier": tier, "hwid": None,
            "first_ip": None, "activated_at": None,
            "last_login_at": None, "expires_at": None,
            "banned": False, "ban_reason": None
        }
    save_keys()
    print(f"[OK] Initialized {len(keys)} keys")

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Scared Opti Admin</title>
    <style>
        :root { --bg: #000; --surface: #0a0a0a; --border: #1a1a1a; --text: #fff; --muted: #666; --danger: #ff0000; --success: #00ff00; --warning: #ffd700; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Courier New', monospace; }
        body { background: var(--bg); color: var(--text); padding: 40px; min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; }

        header { border-bottom: 1px solid var(--border); padding-bottom: 20px; margin-bottom: 40px; display: flex; justify-content: space-between; align-items: center; }
        h1 { font-size: 24px; font-weight: normal; letter-spacing: 2px; text-transform: uppercase; }

        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 40px; }
        .stat { background: var(--surface); border: 1px solid var(--border); padding: 20px; }
        .stat-label { font-size: 10px; color: var(--muted); text-transform: uppercase; margin-bottom: 8px; }
        .stat-value { font-size: 28px; font-weight: bold; }

        .add-form { display: flex; gap: 10px; margin-bottom: 40px; }
        input, select, button { background: var(--surface); border: 1px solid var(--border); color: var(--text); padding: 12px 16px; font-family: inherit; font-size: 12px; outline: none; }
        input { flex: 1; }
        button { cursor: pointer; text-transform: uppercase; transition: all 0.2s; }
        button:hover { background: var(--text); color: var(--bg); }

        table { width: 100%; border-collapse: collapse; }
        th { text-align: left; padding: 12px; border-bottom: 1px solid var(--border); font-size: 10px; color: var(--muted); text-transform: uppercase; font-weight: normal; cursor: pointer; user-select: none; }
        th:hover { color: var(--text); }
        td { padding: 16px 12px; border-bottom: 1px solid var(--border); font-size: 12px; }
        tr:hover { background: rgba(255,255,255,0.02); }

        .badge { padding: 2px 8px; font-size: 10px; text-transform: uppercase; border: 1px solid; }
        .badge-basic { border-color: #444; color: #888; }
        .badge-premium { border-color: var(--warning); color: var(--warning); }
        .badge-owner { border-color: var(--danger); color: var(--danger); }

        .status-active { color: var(--success); font-weight: bold; }
        .status-sharing { color: var(--danger); font-weight: bold; text-decoration: underline; }
        .status-ipchange { color: var(--warning); font-weight: bold; }
        .status-banned { color: #ff4444; }
        .status-unused { color: var(--muted); }

        .actions { display: flex; gap: 8px; }
        .btn-sm { padding: 4px 12px; font-size: 10px; border: 1px solid var(--border); background: transparent; color: var(--muted); }
        .btn-sm:hover { background: var(--text); color: var(--bg); }
        .btn-danger:hover { background: var(--danger); color: #fff; border-color: var(--danger); }

        .sort-arrow { margin-left: 5px; font-size: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Scared Opti // Admin</h1>
            <div style="font-size: 10px; color: var(--muted);">v2.5 COMBINED SERVICE</div>
        </header>

        <div class="stats">
            <div class="stat"><div class="stat-label">Total Keys</div><div class="stat-value" id="total">0</div></div>
            <div class="stat"><div class="stat-label">Active</div><div class="stat-value" id="active">0</div></div>
            <div class="stat"><div class="stat-label">Sharing Ban</div><div class="stat-value" id="sharing" style="color:var(--danger)">0</div></div>
            <div class="stat"><div class="stat-label">Unused</div><div class="stat-value" id="unused">0</div></div>
        </div>

        <div class="add-form">
            <input type="text" id="newKey" placeholder="SCARED-TIER-XXXXXXXX">
            <select id="newTier">
                <option value="BASIC">BASIC</option>
                <option value="PREMIUM">PREMIUM</option>
                <option value="OWNER">OWNER</option>
            </select>
            <button onclick="addKey()">Add Key</button>
        </div>

        <table>
            <thead>
                <tr>
                    <th onclick="sortTable('key')">Key <span class="sort-arrow" id="arrow-key"></span></th>
                    <th onclick="sortTable('tier')">Tier <span class="sort-arrow" id="arrow-tier"></span></th>
                    <th onclick="sortTable('status')">Status <span class="sort-arrow" id="arrow-status"></span></th>
                    <th>HWID / IP</th>
                    <th>Last Login</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="keysTable"></tbody>
        </table>
    </div>

    <script>
        let sortField = 'key';
        let sortAsc = true;
        let allKeysData = [];

        async function load() {
            const res = await fetch('/api/admin/keys');
            const data = await res.json();
            allKeysData = data.keys;

            document.getElementById('total').textContent = data.stats.total;
            document.getElementById('active').textContent = data.stats.active;
            document.getElementById('sharing').textContent = data.stats.sharing;
            document.getElementById('unused').textContent = data.stats.unused;

            renderTable();
        }

        function sortTable(field) {
            if (sortField === field) sortAsc = !sortAsc;
            else { sortField = field; sortAsc = true; }

            document.querySelectorAll('.sort-arrow').forEach(a => a.textContent = '');
            document.getElementById(`arrow-${field}`).textContent = sortAsc ? '▲' : '▼';

            renderTable();
        }

        function getStatusDisplay(k) {
            if (!k.used && !k.banned) return '<span class="status-unused">UNUSED</span>';
            if (k.banned && k.ban_reason === 'SHARING') return '<span class="status-sharing">🚫 SHARING</span>';
            if (k.banned && k.ban_reason === 'IP_CHANGE') return '<span class="status-ipchange">🌐 IP CHANGE</span>';
            if (k.banned) return '<span class="status-banned">⛔ BANNED</span>';
            return '<span class="status-active">✅ ACTIVE</span>';
        }

        function getSortValue(k) {
            if (!k.used && !k.banned) return 0;
            if (k.banned && k.ban_reason === 'SHARING') return 3;
            if (k.banned && k.ban_reason === 'IP_CHANGE') return 2;
            if (k.banned) return 1;
            return 4;
        }

        function renderTable() {
            let filtered = allKeysData;

            filtered.sort((a, b) => {
                if (sortField === 'status') {
                    let valA = getSortValue(a);
                    let valB = getSortValue(b);
                    return sortAsc ? valA - valB : valB - valA;
                }

                let valA = a[sortField] || '';
                let valB = b[sortField] || '';

                if (valA < valB) return sortAsc ? -1 : 1;
                if (valA > valB) return sortAsc ? 1 : -1;
                return 0;
            });

            document.getElementById('keysTable').innerHTML = filtered.map(k => `
                <tr style="${k.banned ? 'opacity:0.6' : ''}">
                    <td style="font-family:monospace">${k.key}</td>
                    <td><span class="badge badge-${k.tier.toLowerCase()}">${k.tier}</span></td>
                    <td>${getStatusDisplay(k)}</td>
                    <td style="color:var(--muted); font-size:10px;">
                        ${k.hwid ? k.hwid.substring(0,12)+'...' : '-'}<br>
                        ${k.first_ip || '-'}
                    </td>
                    <td style="color:var(--muted); font-size:10px;">
                        ${k.last_login_at ? new Date(k.last_login_at).toLocaleString() : '-'}
                    </td>
                    <td class="actions">
                        ${k.banned
                            ? `<button class="btn-sm" onclick="unban('${k.key}')">Unban</button>`
                            : `<button class="btn-sm btn-danger" onclick="ban('${k.key}')">Ban</button>`
                        }
                        <button class="btn-sm btn-danger" onclick="del('${k.key}')">Del</button>
                    </td>
                </tr>
            `).join('');
        }

        async function addKey() {
            const key = document.getElementById('newKey').value.trim().toUpperCase();
            const tier = document.getElementById('newTier').value;
            if(!key) return;
            await fetch('/api/admin/add', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({key,tier})});
            document.getElementById('newKey').value = '';
            load();
        }

        async function ban(key) {
            await fetch('/api/admin/ban', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({key, reason: 'MANUAL'})});
            load();
        }
        async function unban(key) {
            await fetch('/api/admin/unban', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({key})});
            load();
        }
        async function del(key) {
            if(confirm('Delete '+key+'?')) {
                await fetch('/api/admin/delete', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({key})});
                load();
            }
        }

        load();
        setInterval(load, 5000);
    </script>
</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(ADMIN_HTML)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "combined"})


@app.route("/activate", methods=["POST"])
def activate():
    data = request.json
    key = data.get("key", "").strip().upper()
    hwid = data.get("hwid", "").strip()
    client_ip = request.remote_addr

    if not key or key not in keys:
        return jsonify({"status": "invalid", "message": "Invalid key"})

    k = keys[key]

    if k.get("banned"):
        return jsonify({
            "status": "banned",
            "message": f"KEY BANNED ({k.get('ban_reason', 'UNKNOWN')}). Contact support."
        })

    if k.get("expires_at"):
        try:
            if dt.now() > dt.fromisoformat(k["expires_at"]):
                return jsonify({"status": "expired", "message": "License expired"})
        except Exception:
            pass

    if not k["used"]:
        now = dt.now()
        expires = now + timedelta(days=BETA_DURATION_DAYS)
        k.update({
            "used": True,
            "hwid": hwid,
            "first_ip": client_ip,
            "activated_at": now.isoformat(),
            "last_login_at": now.isoformat(),
            "expires_at": expires.isoformat(),
            "banned": False,
            "ban_reason": None
        })
        save_keys()

        send_discord_alert(
            "✅ New Activation",
            f"**Key:** `{key}`\n**Tier:** {k['tier']}\n**IP:** {client_ip}\n**HWID:** `{hwid[:12]}...`",
            color=0x00FF00
        )

        return jsonify({
            "status": "ok",
            "tier": k["tier"],
            "expires_at": int(expires.timestamp())
        })

    if k["hwid"] != hwid:
        k["banned"] = True
        k["ban_reason"] = "SHARING"
        save_keys()

        send_discord_alert(
            "🚫 SHARING DETECTED!",
            f"**Key:** `{key}` ({k['tier']})\n"
            f"**Original IP:** {k['first_ip']}\n"
            f"**New IP:** {client_ip}\n"
            f"**Original HWID:** `{k['hwid'][:12]}...`\n"
            f"**New HWID:** `{hwid[:12]}...`\n\n"
            f"**Status:** BANNED AUTOMATICALLY",
            color=0xFF0000
        )

        return jsonify({
            "status": "banned",
            "message": "SHARING DETECTED. Contact support in discord."
        })

    if k["first_ip"] != client_ip:
        k["banned"] = True
        k["ban_reason"] = "IP_CHANGE"
        save_keys()

        send_discord_alert(
            "🌐 IP Change Detected",
            f"**Key:** `{key}` ({k['tier']})\n"
            f"**Old IP:** {k['first_ip']}\n"
            f"**New IP:** {client_ip}\n\n"
            f"**Status:** BANNED FOR SECURITY",
            color=0xFFFF00
        )

        return jsonify({
            "status": "banned",
            "message": "IP CHANGE DETECTED. Key banned for security. Contact support."
        })

    last_login_str = k.get("last_login_at")
    notify_user = False

    if not last_login_str:
        notify_user = True
    else:
        try:
            last_login = dt.fromisoformat(last_login_str)
            if (dt.now() - last_login).total_seconds() > 1800:
                notify_user = True
        except Exception:
            notify_user = True

    k["last_login_at"] = dt.now().isoformat()
    save_keys()

    if notify_user:
        send_discord_alert(
            "🔑 Successful Login",
            f"**Key:** `{key}` ({k['tier']})\n**IP:** {client_ip}\n**HWID:** `{hwid[:12]}...`",
            color=0x0088FF
        )

    exp_ts = 0
    if k.get("expires_at"):
        try:
            exp_ts = int(dt.fromisoformat(k["expires_at"]).timestamp())
        except Exception:
            pass

    return jsonify({"status": "ok", "tier": k["tier"], "expires_at": exp_ts})


@app.route("/api/admin/keys")
def admin_keys():
    stats = {"total": 0, "active": 0, "sharing": 0, "unused": 0}
    keys_list = []

    for key, data in keys.items():
        keys_list.append({
            "key": key, "tier": data["tier"], "used": data["used"],
            "hwid": data["hwid"], "first_ip": data["first_ip"],
            "activated_at": data["activated_at"], "last_login_at": data.get("last_login_at"),
            "banned": data["banned"], "ban_reason": data.get("ban_reason")
        })

        stats["total"] += 1
        if data["banned"] and data.get("ban_reason") == "SHARING":
            stats["sharing"] += 1
        elif data["banned"]:
            pass
        elif data["used"]:
            stats["active"] += 1
        else:
            stats["unused"] += 1

    return jsonify({"keys": keys_list, "stats": stats})


@app.route("/api/admin/add", methods=["POST"])
def admin_add():
    d = request.json
    if d["key"] in keys:
        return jsonify({"status": "error"})
    keys[d["key"]] = {
        "used": False, "tier": d["tier"], "hwid": None, "first_ip": None,
        "activated_at": None, "last_login_at": None, "expires_at": None,
        "banned": False, "ban_reason": None
    }
    save_keys()
    return jsonify({"status": "ok"})


@app.route("/api/admin/ban", methods=["POST"])
def admin_ban():
    k = request.json["key"]
    reason = request.json.get("reason", "MANUAL")
    if k in keys:
        keys[k]["banned"] = True
        keys[k]["ban_reason"] = reason
        save_keys()
    return jsonify({"status": "ok"})


@app.route("/api/admin/unban", methods=["POST"])
def admin_unban():
    k = request.json["key"]
    if k in keys:
        keys[k]["banned"] = False
        keys[k]["ban_reason"] = None
        save_keys()
    return jsonify({"status": "ok"})


@app.route("/api/admin/delete", methods=["POST"])
def admin_del():
    k = request.json["key"]
    if k in keys:
        del keys[k]
        save_keys()
    return jsonify({"status": "ok"})


# ═══════════════════════════════════════════════
# 🤖 ЧАСТЬ 2: DISCORD-БОТ scaredREV (было bot.py)
# ═══════════════════════════════════════════════

BOT_TOKEN = os.getenv("DISCORD_TOKEN", "MTUyMjAwMTgzOTA2OTg2MDAyMQ.GNDG3X.L9HofQ0VwWolZ0_n31e7LGXPR_kzPvbk8tlONc")

GUILD_ID = int(os.getenv("GUILD_ID", "1083127357818277938"))
PANEL_CHANNEL_ID = int(os.getenv("PANEL_CHANNEL_ID", "1518098248097595453"))
MOD_CHANNEL_ID = int(os.getenv("MOD_CHANNEL_ID", "1522379284189282336"))
PUBLIC_REVIEWS_CHANNEL_ID = int(os.getenv("PUBLIC_REVIEWS_CHANNEL_ID", "1517980239341424800"))

# Раз это теперь один процесс с Flask-ом, по умолчанию бьём в свой же /api/admin/keys
# на этом же инстансе (localhost), а не по внешнему URL — так быстрее и не зависит от DNS.
LICENSE_API_URL = os.getenv("LICENSE_API_URL", f"http://127.0.0.1:{os.environ.get('PORT', 10000)}/api/admin/keys")

# SELF_URL больше не обязателен (сервис теперь один, Flask сам держит порт открытым,
# а keep_alive снаружи держит UptimeRobot) — но оставляем на случай, если решишь
# вернуть внешний пинг вручную.
SELF_URL = os.getenv("SELF_URL", f"http://127.0.0.1:{os.environ.get('PORT', 10000)}/health")

MASCOT_THUMBNAIL_URL = os.getenv(
    "MASCOT_THUMBNAIL_URL",
    "https://i.imgur.com/your_mascot.png",
)

REVIEWS_FILE = os.path.join(os.path.dirname(__file__), "reviews.json")

INTENTS = discord.Intents.default()
INTENTS.message_content = True

bot = commands.Bot(command_prefix="!", intents=INTENTS)


def load_reviews() -> list:
    if not os.path.exists(REVIEWS_FILE):
        return []
    with open(REVIEWS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_review(entry: dict) -> None:
    data = load_reviews()
    data.append(entry)
    with open(REVIEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def update_review_status(review_id: str, status: str) -> None:
    data = load_reviews()
    for r in data:
        if r.get("id") == review_id:
            r["status"] = status
    with open(REVIEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class LicenseResult:
    def __init__(self, valid: bool, reason: str = "", tier: str = ""):
        self.valid = valid
        self.reason = reason
        self.tier = tier


async def check_license(key: str) -> LicenseResult:
    normalized = key.strip().upper()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                LICENSE_API_URL, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return LicenseResult(False, reason=f"api_error_{resp.status}")
                data = await resp.json()
    except Exception as e:
        return LicenseResult(False, reason=f"connection_error: {e}")

    entry: Optional[dict] = None
    for k in data.get("keys", []):
        if str(k.get("key", "")).upper() == normalized:
            entry = k
            break

    if entry is None:
        return LicenseResult(False, reason="invalid_key")

    if entry.get("banned"):
        ban_reason = (entry.get("ban_reason") or "unknown").lower()
        return LicenseResult(False, reason=f"banned_{ban_reason}")

    if not entry.get("used"):
        return LicenseResult(False, reason="unused")

    return LicenseResult(True, tier=entry.get("tier", ""))


REASON_TEXT = {
    "invalid_key": "❌ Ключ не найден. Проверь правильность ввода.",
    "unused": "⚠️ Ключ ещё не активирован — сначала запусти прогу с этим ключом, потом возвращайся за отзывом.",
    "banned_sharing": "🚫 Ключ заблокирован за шаринг (передачу другому человеку).",
    "banned_ip_change": "🌐 Ключ заблокирован из-за смены IP (сработала защита от шаринга).",
    "banned_manual": "⛔ Ключ заблокирован вручную администрацией.",
    "banned_unknown": "⛔ Ключ заблокирован.",
}


def reason_to_text(reason: str) -> str:
    if reason in REASON_TEXT:
        return REASON_TEXT[reason]
    if reason.startswith("banned_"):
        return "⛔ Ключ заблокирован."
    if reason.startswith("api_error_"):
        return "⚠️ Сервер лицензий временно недоступен, попробуй чуть позже."
    if reason.startswith("connection_error"):
        return "⚠️ Не удалось связаться с сервером лицензий, попробуй чуть позже."
    return f"❌ Лицензия не подтверждена ({reason})."


def make_bar(value: float, max_value: float, length: int = 11) -> str:
    if max_value <= 0:
        filled = 0
    else:
        filled = round((value / max_value) * length)
        filled = max(0, min(length, filled))
    return "▓" * filled + "░" * (length - filled)


def stars(rating: int) -> str:
    rating = max(0, min(5, rating))
    return "⭐" * rating + "☆" * (5 - rating)


def build_review_embed(review: dict, member: discord.abc.User) -> discord.Embed:
    fps_before = review["fps_before"]
    fps_after = review["fps_after"]
    gain_pct = round(((fps_after - fps_before) / fps_before) * 100) if fps_before else 0
    scale_max = max(fps_before, fps_after) * 1.05

    embed = discord.Embed(
        title="⭐ Новый отзыв / New review",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
    embed.set_thumbnail(url=MASCOT_THUMBNAIL_URL)

    embed.add_field(name="От / From", value=member.mention, inline=False)
    embed.add_field(
        name="🌟 Оценка / Rating",
        value=f"{stars(review['rating'])} ({review['rating']}/5)",
        inline=False,
    )
    embed.add_field(name="🎮 Игра / Game", value=review["game"], inline=False)
    embed.add_field(name="💻 CPU", value=review["cpu"], inline=True)
    embed.add_field(name="🎮 GPU", value=review["gpu"], inline=True)

    results = (
        f"**До / Before:** `{make_bar(fps_before, scale_max)}` {fps_before} FPS\n"
        f"**После / After:** `{make_bar(fps_after, scale_max)}` {fps_after} FPS\n"
        f"📈 Прирост / Gain: **+{gain_pct}%**"
    )
    embed.add_field(name="📊 Результаты / Results", value=results, inline=False)

    embed.add_field(
        name="💬 Отзыв клиента / Customer feedback",
        value=f"```{review['feedback']}```",
        inline=False,
    )

    embed.set_footer(text="scaredREV • Team")
    return embed


class LicenseModal(discord.ui.Modal, title="Проверка лицензии"):
    license_key = discord.ui.TextInput(
        label="Лицензионный ключ",
        placeholder="XXXX-XXXX-XXXX-XXXX",
        required=True,
        max_length=100,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        result = await check_license(str(self.license_key.value).strip())

        if not result.valid:
            await interaction.followup.send(reason_to_text(result.reason), ephemeral=True)
            return

        view = OpenReviewFormView(license_key=str(self.license_key.value).strip())
        await interaction.followup.send(
            f"✅ Лицензия подтверждена ({result.tier or 'OK'}). Нажми кнопку ниже, чтобы написать отзыв.",
            view=view,
            ephemeral=True,
        )


class ReviewModal(discord.ui.Modal, title="Оставить отзыв"):
    game = discord.ui.TextInput(label="Игра / Game", max_length=50, required=True)
    rating = discord.ui.TextInput(label="Оценка (1-5)", max_length=1, required=True)
    cpu_gpu = discord.ui.TextInput(
        label="CPU / GPU (через ' / ')",
        placeholder="Ryzen 7 7800X3D / 4060",
        required=True,
    )
    fps_before_after = discord.ui.TextInput(
        label="FPS: До / После",
        placeholder="308 / 400",
        required=True,
    )
    feedback = discord.ui.TextInput(
        label="Отзыв",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True,
    )

    def __init__(self, license_key: str):
        super().__init__()
        self.license_key = license_key

    async def on_submit(self, interaction: discord.Interaction):
        try:
            rating_val = int(str(self.rating.value).strip())
            if not (1 <= rating_val <= 5):
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "⚠️ Оценка должна быть числом от 1 до 5. Попробуй ещё раз.", ephemeral=True
            )
            return

        try:
            cpu_str, gpu_str = [p.strip() for p in str(self.cpu_gpu.value).split("/", 1)]
        except ValueError:
            await interaction.response.send_message(
                "⚠️ Укажи CPU и GPU через ' / ', например: `Ryzen 7 7800X3D / 4060`", ephemeral=True
            )
            return

        try:
            before_str, after_str = [p.strip() for p in str(self.fps_before_after.value).split("/", 1)]
            fps_before = int(before_str)
            fps_after = int(after_str)
        except ValueError:
            await interaction.response.send_message(
                "⚠️ Укажи FPS через ' / ', например: `308 / 400`", ephemeral=True
            )
            return

        review_id = f"{interaction.user.id}-{int(dt.now().timestamp())}"
        pending_reviews[review_id] = {
            "id": review_id,
            "user_id": interaction.user.id,
            "license_key": self.license_key,
            "game": str(self.game.value).strip(),
            "rating": rating_val,
            "cpu": cpu_str,
            "gpu": gpu_str,
            "fps_before": fps_before,
            "fps_after": fps_after,
            "feedback": str(self.feedback.value).strip(),
            "before_url": None,
            "after_url": None,
            "status": "awaiting_screenshots",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        await interaction.response.send_message(
            "📸 Почти готово! Пришли ссылку на скриншот **BEFORE** (до) и **AFTER** (после).\n"
            "Загрузи картинки в любой личный чат/канал Discord, скопируй ссылку на файл и вставь её сюда.",
            view=ScreenshotButtonsView(review_id=review_id),
            ephemeral=True,
        )


class ScreenshotUrlModal(discord.ui.Modal):
    url = discord.ui.TextInput(label="Ссылка на скриншот", placeholder="https://...", required=True)

    def __init__(self, review_id: str, which: str):
        super().__init__(title=f"Скриншот {'BEFORE' if which == 'before' else 'AFTER'}")
        self.review_id = review_id
        self.which = which

    async def on_submit(self, interaction: discord.Interaction):
        entry = pending_reviews.get(self.review_id)
        if entry is None:
            await interaction.response.send_message("⚠️ Заявка устарела, начни заново через кнопку отзыва.", ephemeral=True)
            return

        entry[f"{self.which}_url"] = str(self.url.value).strip()

        if entry["before_url"] and entry["after_url"]:
            entry["status"] = "pending_moderation"
            await finalize_review(interaction, entry)
        else:
            await interaction.response.send_message(
                f"✅ Скриншот {self.which.upper()} сохранён. Осталось прислать "
                f"{'AFTER' if self.which == 'before' else 'BEFORE'}.",
                view=ScreenshotButtonsView(review_id=self.review_id),
                ephemeral=True,
            )


async def finalize_review(interaction: discord.Interaction, entry: dict):
    save_review(entry)
    pending_reviews.pop(entry["id"], None)

    mod_channel = bot.get_channel(MOD_CHANNEL_ID)
    if mod_channel is None:
        await interaction.response.send_message(
            "⚠️ Канал модерации не настроен (MOD_CHANNEL_ID). Отзыв сохранён в reviews.json, но не отправлен.",
            ephemeral=True,
        )
        return

    member = interaction.user
    embed = build_review_embed(entry, member)

    link_view = discord.ui.View()
    link_view.add_item(discord.ui.Button(label="Открыть BEFORE", url=entry["before_url"], emoji="📸"))
    link_view.add_item(discord.ui.Button(label="Открыть AFTER", url=entry["after_url"], emoji="📸"))
    mod_actions = ModerationActionsView(review_id=entry["id"])
    for item in mod_actions.children:
        link_view.add_item(item)

    await mod_channel.send(embed=embed, view=link_view)
    await interaction.response.send_message("🎉 Отзыв отправлен на модерацию, спасибо!", ephemeral=True)


pending_reviews: dict[str, dict] = {}


class ReviewPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="📝 Оставить отзыв",
        style=discord.ButtonStyle.primary,
        custom_id="scaredrev:start_review",
    )
    async def start_review(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(LicenseModal())


class OpenReviewFormView(discord.ui.View):
    def __init__(self, license_key: str):
        super().__init__(timeout=300)
        self.license_key = license_key

    @discord.ui.button(label="✍️ Написать отзыв", style=discord.ButtonStyle.success)
    async def open_form(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReviewModal(license_key=self.license_key))


class ScreenshotButtonsView(discord.ui.View):
    def __init__(self, review_id: str):
        super().__init__(timeout=600)
        self.review_id = review_id

    @discord.ui.button(label="📸 Прикрепить BEFORE", style=discord.ButtonStyle.secondary)
    async def before_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ScreenshotUrlModal(self.review_id, "before"))

    @discord.ui.button(label="📸 Прикрепить AFTER", style=discord.ButtonStyle.secondary)
    async def after_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ScreenshotUrlModal(self.review_id, "after"))


class ModerationActionsView(discord.ui.View):
    def __init__(self, review_id: str):
        super().__init__(timeout=None)
        self.review_id = review_id
        self.approve.custom_id = f"scaredrev:approve:{review_id}"
        self.reject.custom_id = f"scaredrev:reject:{review_id}"

    @discord.ui.button(label="✅ Опубликовать", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        update_review_status(self.review_id, "approved")
        public_channel = bot.get_channel(PUBLIC_REVIEWS_CHANNEL_ID)
        if public_channel and interaction.message.embeds:
            await public_channel.send(embed=interaction.message.embeds[0])
        await interaction.response.send_message("✅ Опубликовано.", ephemeral=True)

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        update_review_status(self.review_id, "rejected")
        await interaction.response.send_message("❌ Отзыв отклонён.", ephemeral=True)


@tasks.loop(minutes=5)
async def keep_alive():
    """Больше не обязателен внутри процесса (Flask и так открыт и его пингует
    UptimeRobot снаружи), но оставлен — не мешает и служит доп. логом живости."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(SELF_URL, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                print(f"[keep_alive] {SELF_URL} -> {resp.status}")
    except Exception as e:
        print(f"[keep_alive] ping failed: {e}")


@bot.event
async def on_ready():
    bot.add_view(ReviewPanelView())
    if GUILD_ID:
        await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    else:
        await bot.tree.sync()
    if not keep_alive.is_running():
        keep_alive.start()
    print(f"Logged in as {bot.user} (id={bot.user.id})")


@bot.tree.command(name="setup_review_panel", description="Опубликовать панель с кнопкой 'Оставить отзыв' в этом канале")
@app_commands.checks.has_permissions(administrator=True)
async def setup_review_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📝 Оставить отзыв о scaredREV",
        description=(
            "Нажми кнопку ниже, чтобы оставить отзыв.\n"
            "Потребуется твой лицензионный ключ для подтверждения покупки."
        ),
        color=discord.Color.blurple(),
    )
    await interaction.channel.send(embed=embed, view=ReviewPanelView())
    await interaction.response.send_message("Панель опубликована ✅", ephemeral=True)


# ═══════════════════════════════════════════════
# 🚀 ЕДИНАЯ ТОЧКА ЗАПУСКА
# ═══════════════════════════════════════════════

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    if BOT_TOKEN == "NOTOKEN_SET":
        raise SystemExit(
            "Не задан токен бота. Установи переменную окружения DISCORD_TOKEN на Render."
        )

    print(f"🔐 Scared Opti Combined Service | Keys: {len(keys)}")

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    bot.run(BOT_TOKEN)
