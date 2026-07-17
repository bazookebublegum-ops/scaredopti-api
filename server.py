import os, json, threading, datetime, asyncio, difflib, traceback
from datetime import datetime as dt, timedelta
from typing import Optional

import requests, aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import View, Modal
from flask import Flask, request, jsonify, render_template_string


# ══════════════════════════════════════════════════════════════
# ⚙️ КОНФИГУРАЦИЯ — МЕНЯЙ ЗДЕСЬ
# ══════════════════════════════════════════════════════════════

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = 0
PREFIX = "!"

ADMIN_ROLE_ID = 1527423541538979972
GUILD_ID = 1083127357818277938
PANEL_CHANNEL_ID = 1518098248097595453
MOD_CHANNEL_ID = 1522379284189282336
PUBLIC_REVIEWS_CHANNEL_ID = 1517980239341424800
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1523045988401549396/NxEa66M65uPCdyN68E-pdv4byp7EehCxR0biNUt7ZaZ_XN7qPtkXC3zDyYhRB1LUlNEN"
MASCOT_THUMBNAIL_URL = "https://i.imgur.com/your_mascot.png"
BETA_DURATION_DAYS = 30
KEYS_FILE = "keys.json"
REVIEWS_FILE = "reviews.json"


# ══════════════════════════════════════════════════════════════
# 🔐 БАЗА КЛЮЧЕЙ
# ══════════════════════════════════════════════════════════════

ALL_KEYS_DATA = {
    "SCARED-BASIC-0GRF5A4M": "BASIC", "SCARED-BASIC-0MVAPYIX": "BASIC",
    "SCARED-BASIC-V9RPP3FY": "BASIC", "SCARED-BASIC-VV7IP3O1": "BASIC",
    "SCARED-BASIC-XLZQDCKM": "BASIC", "SCARED-BASIC-Z9Q2FXE7": "BASIC",
    "SCARED-BASIC-ZIMZNHJR": "BASIC", "SCARED-BASIC-ZT0JRIYO": "BASIC",
    "SCARED-PREM-01LEM9O1": "PREMIUM", "SCARED-PREM-0FBM2MPP": "PREMIUM",
    "SCARED-PREM-107RQOJ1": "PREMIUM", "SCARED-PREM-10LN3WBH": "PREMIUM",
    "SCARED-PREM-XWQ28MKC": "PREMIUM", "SCARED-PREM-YB2JXI6A": "PREMIUM",
    "SCARED-PREM-YJUMV7LT": "PREMIUM", "SCARED-PREM-YO2EMVKN": "PREMIUM",
    "SCARED-PREM-ZR3SGYI0": "PREMIUM", "SCARED-PREM-ZUVBT0RX": "PREMIUM",
    "SCARED-OWNER-GODMODE": "OWNER", "SCARED-OWNER-ALPHA01": "OWNER",
    "SCARED-OWNER-BETA002": "OWNER", "SCARED-OWNER-DELTA03": "OWNER",
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


def send_discord_alert(title, description, color=0xFF0000):
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        payload = {
            "embeds": [{
                "title": title, "description": description, "color": color,
                "timestamp": dt.now().isoformat(),
                "footer": {"text": "Scared Opti Security System"}
            }]
        }
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        print(f"[DISCORD ERROR] {e}")


# ══════════════════════════════════════════════════════════════
# 🎨 FLASK — АДМИНКА + API
# ══════════════════════════════════════════════════════════════

app = Flask(__name__)

ADMIN_HTML = """<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><title>Scared Opti Admin</title>
<style>
:root{--bg:#0a0a0a;--text:#e0e0e0;--surface:#141414;--border:#2a2a2a;--muted:#666;--success:#4ade80;--warning:#fbbf24;--danger:#ef4444;}
*{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New',monospace;}
body{background:var(--bg);color:var(--text);padding:40px;min-height:100vh;}
.container{max-width:1200px;margin:0 auto;}
header{border-bottom:1px solid var(--border);padding-bottom:20px;margin-bottom:40px;display:flex;justify-content:space-between;align-items:center;}
h1{font-size:24px;font-weight:normal;letter-spacing:2px;text-transform:uppercase;}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin-bottom:40px;}
.stat{background:var(--surface);border:1px solid var(--border);padding:20px;}
.stat-label{font-size:10px;color:var(--muted);text-transform:uppercase;margin-bottom:8px;}
.stat-value{font-size:28px;font-weight:bold;}
.add-form{display:flex;gap:10px;margin-bottom:40px;}
input,select,button{background:var(--surface);border:1px solid var(--border);color:var(--text);padding:12px 16px;font-family:inherit;font-size:12px;outline:none;}
input{flex:1;}button{cursor:pointer;text-transform:uppercase;transition:all 0.2s;}
button:hover{background:var(--text);color:var(--bg);}
table{width:100%;border-collapse:collapse;}
th{text-align:left;padding:12px;border-bottom:1px solid var(--border);font-size:10px;color:var(--muted);text-transform:uppercase;font-weight:normal;cursor:pointer;user-select:none;}
th:hover{color:var(--text);}
td{padding:16px 12px;border-bottom:1px solid var(--border);font-size:12px;}
tr:hover{background:rgba(255,255,255,0.02);}
.badge{padding:2px 8px;font-size:10px;text-transform:uppercase;border:1px solid;}
.badge-basic{border-color:#444;color:#888;}
.badge-premium{border-color:var(--warning);color:var(--warning);}
.badge-owner{border-color:var(--danger);color:var(--danger);}
.status-active{color:var(--success);font-weight:bold;}
.status-sharing{color:var(--danger);font-weight:bold;text-decoration:underline;}
.status-ipchange{color:var(--warning);font-weight:bold;}
.status-banned{color:#ff4444;}
.status-unused{color:var(--muted);}
.actions{display:flex;gap:8px;}
.btn-sm{padding:4px 12px;font-size:10px;border:1px solid var(--border);background:transparent;color:var(--muted);}
.btn-sm:hover{background:var(--text);color:var(--bg);}
.btn-danger:hover{background:var(--danger);color:#fff;border-color:var(--danger);}
.sort-arrow{margin-left:5px;font-size:8px;}
</style></head><body>
<div class="container">
<header><h1>Scared Opti // Admin</h1><div style="font-size:10px;color:var(--muted);">v2.5 COMBINED SERVICE</div></header>
<div class="stats"><div class="stat"><div class="stat-label">Total Keys</div><div class="stat-value" id="total">0</div></div><div class="stat"><div class="stat-label">Active</div><div class="stat-value" id="active">0</div></div><div class="stat"><div class="stat-label">Sharing Ban</div><div class="stat-value" id="sharing" style="color:var(--danger)">0</div></div><div class="stat"><div class="stat-label">Unused</div><div class="stat-value" id="unused">0</div></div></div>
<div class="add-form"><input type="text" id="newKey" placeholder="SCARED-TIER-XXXXXXXX"><select id="newTier"><option value="BASIC">BASIC</option><option value="PREMIUM">PREMIUM</option><option value="OWNER">OWNER</option></select><button onclick="addKey()">Add Key</button></div>
<table><thead><tr><th onclick="sortTable('key')">Key <span class="sort-arrow" id="arrow-key"></span></th><th onclick="sortTable('tier')">Tier <span class="sort-arrow" id="arrow-tier"></span></th><th onclick="sortTable('status')">Status <span class="sort-arrow" id="arrow-status"></span></th><th>HWID</th><th>IP</th><th onclick="sortTable('activated_at')">Activated <span class="sort-arrow" id="arrow-activated_at"></span></th><th>Actions</th></tr></thead><tbody id="keysTable"></tbody></table></div>
<script>
let allKeysData=[];let sortField='status';let sortAsc=true;
async function load(){const r=await fetch('/api/admin/keys');const d=await r.json();allKeysData=d.keys;
document.getElementById('total').textContent=d.stats.total;document.getElementById('active').textContent=d.stats.active;
document.getElementById('sharing').textContent=d.stats.sharing;document.getElementById('unused').textContent=d.stats.unused;renderTable();}
function sortTable(f){if(sortField===f)sortAsc=!sortAsc;else{sortField=f;sortAsc=true;}
document.querySelectorAll('.sort-arrow').forEach(a=>a.textContent='');document.getElementById('arrow-'+f).textContent=sortAsc?'▲':'▼';renderTable();}
function getStatusDisplay(k){if(!k.used&&!k.banned)return'<span class="status-unused">UNUSED</span>';if(k.banned&&k.ban_reason==='SHARING')return'<span class="status-sharing">🚫 SHARING</span>';if(k.banned&&k.ban_reason==='IP_CHANGE')return'<span class="status-ipchange">🌐 IP CHANGE</span>';if(k.banned)return'<span class="status-banned">⛔ BANNED</span>';return'<span class="status-active">✅ ACTIVE</span>';}
function getSortValue(k){if(k.banned&&k.ban_reason==='SHARING')return 0;if(k.banned)return 1;return 4;}
function renderTable(){let filtered=allKeysData;filtered.sort((a,b)=>{if(sortField==='status'){let vA=getSortValue(a);let vB=getSortValue(b);return sortAsc?vA-vB:vB-vA;}
let vA=a[sortField]||'';let vB=b[sortField]||'';if(vA<vB)return sortAsc?-1:1;if(vA>vB)return sortAsc?1:-1;return 0;});
document.getElementById('keysTable').innerHTML=filtered.map(k=>`
<tr style="${k.banned?'opacity:0.6':''}"><td style="font-family:monospace">${k.key}</td>
<td><span class="badge badge-${k.tier.toLowerCase()}">${k.tier}</span></td>
<td>${getStatusDisplay(k)}</td>
<td style="font-size:10px">${k.hwid?k.hwid.substring(0,12)+'...':'-'}</td>
<td>${k.first_ip||'-'}</td>
<td>${k.activated_at?new Date(k.activated_at).toLocaleString():'-'}</td>
<td class="actions">${k.banned?`<button class="btn-sm" onclick="unban('${k.key}')">Unban</button>`:`<button class="btn-sm btn-danger" onclick="ban('${k.key}')">Ban</button>`}<button class="btn-sm btn-danger" onclick="del('${k.key}')">Del</button></td></tr>`).join('');}
async function addKey(){const key=document.getElementById('newKey').value.trim().toUpperCase();const tier=document.getElementById('newTier').value;if(!key)return;await fetch('/api/admin/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key,tier})});document.getElementById('newKey').value='';load();}
async function ban(key){await fetch('/api/admin/ban',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key,reason:'MANUAL'})});load();}
async function unban(key){await fetch('/api/admin/unban',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key})});load();}
async function del(key){if(confirm('Delete '+key+'?')){await fetch('/api/admin/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key})});load();}}
load();setInterval(load,5000);
</script></body></html>"""


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
        return jsonify({"status": "banned", "message": f"KEY BANNED ({k.get('ban_reason', 'UNKNOWN')}). Contact support."})

    if k.get("expires_at"):
        try:
            if dt.now() > dt.fromisoformat(k["expires_at"]):
                return jsonify({"status": "expired", "message": "License expired"})
        except:
            pass

    if not k["used"]:
        now = dt.now()
        expires = now + timedelta(days=BETA_DURATION_DAYS)
        k.update({
            "used": True, "hwid": hwid, "first_ip": client_ip,
            "activated_at": now.isoformat(), "last_login_at": now.isoformat(),
            "expires_at": expires.isoformat(), "banned": False, "ban_reason": None
        })
        save_keys()
        send_discord_alert("✅ New Activation", f"**Key:** `{key}`\n**Tier:** {k['tier']}\n**IP:** {client_ip}\n**HWID:** `{hwid[:12]}...`", color=0x00FF00)
        return jsonify({"status": "ok", "tier": k["tier"], "expires_at": int(expires.timestamp())})

    if k["hwid"] != hwid:
        k["banned"] = True; k["ban_reason"] = "SHARING"; save_keys()
        send_discord_alert("🚫 SHARING DETECTED!", f"**Key:** `{key}` ({k['tier']})\n**Original IP:** {k['first_ip']}\n**New IP:** {client_ip}", color=0xFF0000)
        return jsonify({"status": "banned", "message": "SHARING DETECTED. Contact support."})

    if k["first_ip"] != client_ip:
        k["banned"] = True; k["ban_reason"] = "IP_CHANGE"; save_keys()
        send_discord_alert("🌐 IP Change Detected", f"**Key:** `{key}` ({k['tier']})\n**Old IP:** {k['first_ip']}\n**New IP:** {client_ip}", color=0xFFFF00)
        return jsonify({"status": "banned", "message": "IP CHANGE DETECTED. Key banned for security."})

    last = k.get("last_login_at")
    notify = False
    if not last:
        notify = True
    else:
        try:
            if (dt.now() - dt.fromisoformat(last)).total_seconds() > 1800:
                notify = True
        except:
            notify = True

    k["last_login_at"] = dt.now().isoformat()
    save_keys()

    if notify:
        send_discord_alert("🔑 Successful Login", f"**Key:** `{key}` ({k['tier']})\n**IP:** {client_ip}\n**HWID:** `{hwid[:12]}...`", color=0x0088FF)

    exp_ts = 0
    if k.get("expires_at"):
        try:
            exp_ts = int(dt.fromisoformat(k["expires_at"]).timestamp())
        except:
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


def run_flask():
    port = int(os.environ.get("PORT", 10000))
    print(f"[+] Flask admin on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


# ══════════════════════════════════════════════════════════════
# 🤖 DISCORD БОТ
# ══════════════════════════════════════════════════════════════

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)
bot.owner_id = OWNER_ID


# ══════════════════════════════════════════════════════════════
# ⭐ СИСТЕМА ОТЗЫВОВ (REVIEWS)
# ══════════════════════════════════════════════════════════════

def load_reviews():
    if not os.path.exists(REVIEWS_FILE):
        return []
    with open(REVIEWS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_review(entry):
    data = load_reviews()
    data.append(entry)
    with open(REVIEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def update_review_status(review_id, status):
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


async def check_license(key):
    normalized = key.strip().upper()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://127.0.0.1:{os.environ.get('PORT', 10000)}/api/admin/keys",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return LicenseResult(False, reason=f"api_error_{resp.status}")
                data = await resp.json()
    except Exception as e:
        return LicenseResult(False, reason=f"connection_error: {e}")

    entry = None
    for k in data.get("keys", []):
        if str(k.get("key", "")).upper() == normalized:
            entry = k
            break
    if entry is None:
        return LicenseResult(False, reason="invalid_key")
    if entry.get("banned"):
        return LicenseResult(False, reason=f"banned_{(entry.get('ban_reason') or 'unknown').lower()}")
    if not entry.get("used"):
        return LicenseResult(False, reason="unused")
    return LicenseResult(True, tier=entry.get("tier", ""))


REASON_TEXT = {
    "invalid_key": "❌ Ключ не найден.",
    "unused": "⚠️ Ключ ещё не активирован — сначала запусти прогу.",
    "banned_sharing": "🚫 Ключ заблокирован за шаринг.",
    "banned_ip_change": "🌐 Ключ заблокирован из-за смены IP.",
    "banned_manual": "⛔ Ключ заблокирован вручную.",
    "banned_unknown": "⛔ Ключ заблокирован.",
}


def reason_to_text(reason):
    if reason in REASON_TEXT:
        return REASON_TEXT[reason]
    if reason.startswith("banned_"):
        return "⛔ Ключ заблокирован."
    if reason.startswith("api_error_"):
        return "⚠️ Сервер лицензий недоступен."
    if reason.startswith("connection_error"):
        return "⚠️ Не удалось связаться с сервером."
    return f"❌ {reason}"


def stars(rating):
    return "⭐" * rating + "☆" * (5 - rating)


def build_review_embed(review, member):
    fb = review["fps_before"]
    fa = review["fps_after"]
    gain = round(((fa - fb) / fb) * 100) if fb else 0
    scale = max(fb, fa) * 1.05

    embed = discord.Embed(
        title="⭐ Новый отзыв",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
    embed.set_thumbnail(url=MASCOT_THUMBNAIL_URL)
    embed.add_field(name="От", value=member.mention, inline=False)
    embed.add_field(name="Оценка", value=f"{stars(review['rating'])} ({review['rating']}/5)", inline=False)
    embed.add_field(name="Игра", value=review["game"], inline=False)
    embed.add_field(name="CPU", value=review["cpu"], inline=True)
    embed.add_field(name="GPU", value=review["gpu"], inline=True)
    embed.add_field(name="Результаты", value=f"**До:** {fb} FPS\n**После:** {fa} FPS\n📈 **+{gain}%**", inline=False)
    embed.add_field(name="Отзыв", value=f"```{review['feedback']}```", inline=False)
    embed.set_footer(text="scaredREV")
    return embed


class LicenseModal(Modal, title="Проверка лицензии"):
    license_key = discord.ui.TextInput(label="Лицензионный ключ", placeholder="XXXX-XXXX-XXXX-XXXX", required=True, max_length=100)

    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        result = await check_license(str(self.license_key.value).strip())
        if not result.valid:
            await interaction.followup.send(reason_to_text(result.reason), ephemeral=True)
            return
        view = OpenReviewFormView(license_key=str(self.license_key.value).strip())
        await interaction.followup.send(f"✅ Лицензия подтверждена ({result.tier}). Нажми кнопку ниже.", view=view, ephemeral=True)


class ReviewModal(Modal, title="Оставить отзыв"):
    game = discord.ui.TextInput(label="Игра", max_length=50, required=True)
    rating = discord.ui.TextInput(label="Оценка (1-5)", max_length=1, required=True)
    cpu_gpu = discord.ui.TextInput(label="CPU / GPU (через ' / ')", placeholder="Ryzen 7 7800X3D / 4060", required=True)
    fps_before_after = discord.ui.TextInput(label="FPS: До / После", placeholder="308 / 400", required=True)
    feedback = discord.ui.TextInput(label="Отзыв", style=discord.TextStyle.paragraph, max_length=500, required=True)

    def __init__(self, license_key):
        super().__init__()
        self.license_key = license_key

    async def on_submit(self, interaction):
        try:
            rating_val = int(str(self.rating.value).strip())
            if not (1 <= rating_val <= 5):
                raise ValueError
        except ValueError:
            await interaction.response.send_message("⚠️ Оценка от 1 до 5.", ephemeral=True)
            return

        try:
            cpu_str, gpu_str = [p.strip() for p in str(self.cpu_gpu.value).split("/", 1)]
        except ValueError:
            await interaction.response.send_message("⚠️ Укажи CPU/GPU через /", ephemeral=True)
            return

        try:
            before_str, after_str = [p.strip() for p in str(self.fps_before_after.value).split("/", 1)]
            fps_before, fps_after = int(before_str), int(after_str)
        except ValueError:
            await interaction.response.send_message("⚠️ Укажи FPS через /", ephemeral=True)
            return

        rid = f"{interaction.user.id}-{int(dt.now().timestamp())}"
        pending_reviews[rid] = {
            "id": rid, "user_id": interaction.user.id, "license_key": self.license_key,
            "game": str(self.game.value).strip(), "rating": rating_val,
            "cpu": cpu_str, "gpu": gpu_str, "fps_before": fps_before, "fps_after": fps_after,
            "feedback": str(self.feedback.value).strip(), "before_url": None, "after_url": None,
            "status": "awaiting_screenshots",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        await interaction.response.send_message("📸 Пришли ссылки на скриншоты BEFORE и AFTER.", view=ScreenshotButtonsView(review_id=rid), ephemeral=True)


class ScreenshotUrlModal(Modal):
    url = discord.ui.TextInput(label="Ссылка на скриншот", placeholder="https://...", required=True)

    def __init__(self, review_id, which):
        super().__init__(title=f"Скриншот {'BEFORE' if which == 'before' else 'AFTER'}")
        self.review_id = review_id
        self.which = which

    async def on_submit(self, interaction):
        entry = pending_reviews.get(self.review_id)
        if entry is None:
            await interaction.response.send_message("⚠️ Заявка устарела.", ephemeral=True)
            return
        entry[f"{self.which}_url"] = str(self.url.value).strip()
        if entry["before_url"] and entry["after_url"]:
            entry["status"] = "pending_moderation"
            await finalize_review(interaction, entry)
        else:
            await interaction.response.send_message(f"✅ Скриншот {self.which.upper()} сохранён.", view=ScreenshotButtonsView(review_id=self.review_id), ephemeral=True)


async def finalize_review(interaction, entry):
    save_review(entry)
    pending_reviews.pop(entry["id"], None)
    mod_channel = bot.get_channel(MOD_CHANNEL_ID)
    if mod_channel is None:
        await interaction.response.send_message("⚠️ Канал модерации не настроен.", ephemeral=True)
        return
    member = interaction.user
    embed = build_review_embed(entry, member)
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="BEFORE", url=entry["before_url"], emoji="📸"))
    view.add_item(discord.ui.Button(label="AFTER", url=entry["after_url"], emoji="📸"))
    view.add_item(discord.ui.Button(label="✅ Опубликовать", style=discord.ButtonStyle.success, custom_id=f"rev:approve:{entry['id']}"))
    view.add_item(discord.ui.Button(label="❌ Отклонить", style=discord.ButtonStyle.danger, custom_id=f"rev:reject:{entry['id']}"))
    await mod_channel.send(embed=embed, view=view)
    await interaction.response.send_message("🎉 Отзыв отправлен на модерацию!", ephemeral=True)


pending_reviews = {}


class OpenReviewFormView(View):
    def __init__(self, license_key):
        super().__init__(timeout=300)
        self.license_key = license_key

    @discord.ui.button(label="✍️ Написать отзыв", style=discord.ButtonStyle.success)
    async def open_form(self, interaction, button):
        await interaction.response.send_modal(ReviewModal(license_key=self.license_key))


class ScreenshotButtonsView(View):
    def __init__(self, review_id):
        super().__init__(timeout=600)
        self.review_id = review_id

    @discord.ui.button(label="📸 BEFORE", style=discord.ButtonStyle.secondary)
    async def before_btn(self, interaction, button):
        await interaction.response.send_modal(ScreenshotUrlModal(self.review_id, "before"))

    @discord.ui.button(label="📸 AFTER", style=discord.ButtonStyle.secondary)
    async def after_btn(self, interaction, button):
        await interaction.response.send_modal(ScreenshotUrlModal(self.review_id, "after"))


class ReviewPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Оставить отзыв", style=discord.ButtonStyle.primary, custom_id="scaredrev:start_review")
    async def start_review(self, interaction, button):
        await interaction.response.send_modal(LicenseModal())


# ══════════════════════════════════════════════════════════════
# 🎫 СИСТЕМА ТИКЕТОВ
# ══════════════════════════════════════════════════════════════

class AppModal(Modal):
    def __init__(self, bot):
        super().__init__(title="Заявка в клан")
        self.bot = bot
        self.add_item(discord.ui.TextInput(label="1. Сколько вам лет?", placeholder="18", min_length=1, max_length=3))
        self.add_item(discord.ui.TextInput(label="2. Часов в игре? (нужно от 2 000)", placeholder="2000+", min_length=1))
        self.add_item(discord.ui.TextInput(label="3. Ссылка на Steam", placeholder="https://steamcommunity.com/id/...", min_length=1))
        self.add_item(discord.ui.TextInput(label="4. Скриншот / Оценка адекватности", placeholder="Ссылка на скриншот и самооценка 1-10", style=discord.TextStyle.paragraph, min_length=1))
        self.add_item(discord.ui.TextInput(label="5. Желаемая роль", placeholder="Билдер, ПвП-шник, Фармер...", min_length=1))

    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        user = interaction.user
        for ch in guild.channels:
            if ch.name == f"ticket-{user.name.lower().replace(' ', '-')}":
                await interaction.followup.send("❌ У вас уже есть открытый тикет!", ephemeral=True)
                return
        category = discord.utils.get(guild.categories, name="Тикеты")
        if not category:
            category = await guild.create_category("Тикеты")
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True, manage_permissions=True)
        }
        desired_role = self.children[4].value
        channel = await guild.create_text_channel(
            f"тикет-{user.name.lower().replace(' ', '-')}", category=category,
            topic=f"Роль: {desired_role} | ID: {user.id}", overwrites=overwrites
        )
        embed = discord.Embed(title="Новая заявка", description=f"{user.mention}", color=discord.Color.green(), timestamp=datetime.datetime.now())
        embed.add_field(name="Возраст", value=self.children[0].value, inline=True)
        embed.add_field(name="Часов в игре", value=self.children[1].value, inline=True)
        embed.add_field(name="Steam", value=self.children[2].value, inline=False)
        embed.add_field(name="Скриншот / Адекватность", value=self.children[3].value, inline=False)
        embed.add_field(name="Желаемая роль", value=desired_role, inline=False)
        embed.set_footer(text=f"User ID: {user.id}")
        await channel.send(f"{user.mention}", embed=embed, view=TicketActions())
        await interaction.followup.send(f"✅ Тикет создан: {channel.mention}", ephemeral=True)

    async def on_error(self, interaction, error):
        await interaction.response.send_message("❌ Ошибка. Попробуйте снова.", ephemeral=True)


class AddUserModal(Modal):
    def __init__(self, channel):
        super().__init__(title="Добавить пользователя")
        self.channel = channel
        self.add_item(discord.ui.TextInput(label="ID пользователя", placeholder="Вставьте ID сюда", min_length=17, max_length=20))

    async def on_submit(self, interaction):
        try:
            member = await interaction.guild.fetch_member(int(self.children[0].value))
            await self.channel.set_permissions(member, read_messages=True, send_messages=True, attach_files=True, embed_links=True)
            await interaction.response.send_message(f"✅ {member.mention} добавлен.", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Пользователь не найден.", ephemeral=True)


class ConfirmClose(View):
    def __init__(self, channel):
        super().__init__(timeout=30)
        self.channel = channel

    @discord.ui.button(label="Да, закрыть", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction, button):
        await interaction.response.edit_message(content="🔒 Закрывается через 5 сек...", view=None)
        await asyncio.sleep(5)
        await self.channel.delete()

    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        await interaction.response.edit_message(content="❌ Отменено.", view=None, delete_after=3)


class TicketActions(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Выдать роль", style=discord.ButtonStyle.success, emoji="🎖️", custom_id="ticket:role")
    async def assign_role(self, interaction, button):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Только администратор может выдавать роли.", ephemeral=True)
            return
        if not interaction.channel.topic or "Роль:" not in interaction.channel.topic:
            await interaction.response.send_message("❌ Информация о роли не найдена.", ephemeral=True)
            return
        try:
            parts = interaction.channel.topic.split(" | ")
            desired_role_name = parts[0].replace("Роль: ", "")
            user_id = int(parts[1].replace("ID: ", ""))
        except:
            await interaction.response.send_message("❌ Ошибка чтения данных тикета.", ephemeral=True)
            return
        member = interaction.guild.get_member(user_id)
        if not member:
            await interaction.response.send_message("❌ Пользователь не на сервере.", ephemeral=True)
            return
        roles = interaction.guild.roles
        matches = []
        for r in roles:
            if r.name.lower() == desired_role_name.lower():
                matches = [r]
                break
        if not matches:
            matches = [r for r in roles if desired_role_name.lower() in r.name.lower() or r.name.lower() in desired_role_name.lower()]
        if not matches:
            close = difflib.get_close_matches(desired_role_name, [r.name for r in roles], n=3, cutoff=0.5)
            matches = [r for r in roles if r.name in close]
        if not matches:
            await interaction.response.send_message(f"❌ Роль \"{desired_role_name}\" не найдена.", ephemeral=True)
            return
        if len(matches) > 1:
            await interaction.response.send_message(f"❌ Найдено несколько: {', '.join(f'`{r.name}`' for r in matches)}. Выдайте вручную.", ephemeral=True)
            return
        role = matches[0]
        if role in member.roles:
            await interaction.response.send_message(f"ℹ️ Уже имеет роль `{role.name}`.", ephemeral=True)
            return
        if role.position >= interaction.guild.me.top_role.position:
            await interaction.response.send_message(f"❌ Не могу выдать `{role.name}` — роль выше моей.", ephemeral=True)
            return
        await member.add_roles(role, reason="Выдача роли через тикет")
        await interaction.response.send_message(f"✅ {member.mention} выдана роль `{role.name}`.", ephemeral=True)

    @discord.ui.button(label="Закрыть", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket:close")
    async def close(self, interaction, button):
        embed = discord.Embed(title="Закрыть тикет?", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, view=ConfirmClose(interaction.channel))

    @discord.ui.button(label="Добавить", style=discord.ButtonStyle.success, emoji="➕", custom_id="ticket:add")
    async def add_user(self, interaction, button):
        await interaction.response.send_modal(AddUserModal(channel=interaction.channel))


class OpenTicketBtn(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="persistent:ticket_open")
    async def create(self, interaction, button):
        await interaction.response.send_modal(AppModal(self.bot))


# ══════════════════════════════════════════════════════════════
# 🧩 ЗАГРУЗКА COGS ИЗ ПАПКИ
# ══════════════════════════════════════════════════════════════

async def load_cogs():
    for f in os.listdir("cogs"):
        if f.endswith(".py") and f != "__init__.py":
            await bot.load_extension(f"cogs.{f[:-3]}")
            print(f"[+] Loaded cog: {f[:-3]}")


# ══════════════════════════════════════════════════════════════
# 🤖 КОМАНДЫ БОТА
# ══════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    bot.add_view(ReviewPanelView())
    bot.add_view(OpenTicketBtn(bot))
    bot.add_view(TicketActions())
    if GUILD_ID:
        await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    else:
        await bot.tree.sync()
    print(f"[+] {bot.user} online! Servers: {len(bot.guilds)}")
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help"))


@bot.command()
@commands.is_owner()
async def load(ctx, extension: str):
    await bot.load_extension(f"cogs.{extension.lower()}")
    await ctx.send(f"✅ Cog `{extension}` loaded.")


@bot.command()
@commands.is_owner()
async def unload(ctx, extension: str):
    await bot.unload_extension(f"cogs.{extension.lower()}")
    await ctx.send(f"✅ Cog `{extension}` unloaded.")


@bot.command()
@commands.is_owner()
async def reload(ctx, extension: str = None):
    if extension:
        await bot.reload_extension(f"cogs.{extension.lower()}")
        await ctx.send(f"✅ Cog `{extension}` reloaded.")
    else:
        for f in os.listdir("cogs"):
            if f.endswith(".py") and f != "__init__.py":
                await bot.reload_extension(f"cogs.{f[:-3]}")
        await ctx.send("✅ All cogs reloaded.")


@bot.command()
@commands.is_owner()
async def ticket(ctx, action: str = None, member: discord.Member = None):
    if not action:
        embed = discord.Embed(title="Команды тикетов", description="`!ticket setup` — Панель заявок\n`!ticket close` — Закрыть\n`!ticket add @user` — Добавить\n`!ticket remove @user` — Убрать", color=discord.Color.blue())
        await ctx.send(embed=embed)
        return
    if action == "setup":
        embed = discord.Embed(title="Подача заявки в клан", description="Нажмите кнопку ниже.\n\nТребования: **от 2 000 часов**.", color=discord.Color.blue())
        await ctx.send(embed=embed, view=OpenTicketBtn(bot))
    elif action == "close":
        if not ctx.channel.name.startswith("тикет-") and not ctx.channel.name.startswith("ticket-"):
            await ctx.send("❌ Это не тикет.")
            return
        await ctx.send(embed=discord.Embed(title="Закрыть тикет?", color=discord.Color.red()), view=ConfirmClose(ctx.channel))
    elif action == "add":
        if not ctx.channel.name.startswith("тикет-") and not ctx.channel.name.startswith("ticket-"):
            await ctx.send("❌ Это не тикет.")
            return
        if not member:
            await ctx.send("Использование: `!ticket add @user`")
            return
        await ctx.channel.set_permissions(member, read_messages=True, send_messages=True, attach_files=True, embed_links=True)
        await ctx.send(f"✅ {member.mention} добавлен.")
    elif action == "remove":
        if not ctx.channel.name.startswith("тикет-") and not ctx.channel.name.startswith("ticket-"):
            await ctx.send("❌ Это не тикет.")
            return
        if not member:
            await ctx.send("Использование: `!ticket remove @user`")
            return
        await ctx.channel.set_permissions(member, overwrite=None)
        await ctx.send(f"✅ {member.mention} убран.")


# Клонирование (встроено, без отдельного cog)
async def _get_source(server_id):
    guild = discord.utils.get(bot.guilds, id=server_id)
    if guild:
        return guild, True
    try:
        guild = await bot.fetch_guild(server_id)
        return guild, False
    except Exception as e:
        print(f"[!] fetch_guild error: {type(e).__name__}: {e}")
        return None, False


async def _copy_server(source, target):
    await target.edit(name=source.name)
    if source.icon:
        try:
            await target.edit(icon=await source.icon.read())
        except:
            pass
    if source.banner:
        try:
            await target.edit(banner=await source.banner.read())
        except:
            pass
    if source.description:
        try:
            await target.edit(description=source.description)
        except:
            pass


async def _copy_roles(source, target):
    existing = {r.name for r in target.roles}
    to_copy = sorted([r for r in source.roles if r.name != "@everyone"], key=lambda r: r.position, reverse=True)
    count = 0
    for role in to_copy:
        if role.name not in existing:
            try:
                await target.create_role(name=role.name, permissions=role.permissions, color=role.color, hoist=role.hoist, mentionable=role.mentionable, reason=f"Cloned from {source.name}")
                count += 1
                await asyncio.sleep(0.5)
            except:
                pass
    return count


async def _copy_channels(source, target):
    for ch in target.channels:
        try:
            await ch.delete()
            await asyncio.sleep(0.3)
        except:
            pass
    categories = sorted(source.categories, key=lambda c: c.position)
    cat_map = {}
    for cat in categories:
        overwrites = {}
        for t, o in cat.overwrites.items():
            if isinstance(t, discord.Role):
                role = discord.utils.get(target.roles, name=t.name)
                if role:
                    overwrites[role] = o
        nc = await target.create_category(name=cat.name, overwrites=overwrites or None, position=cat.position)
        cat_map[cat.id] = nc
        await asyncio.sleep(0.5)
    for ch in source.channels:
        if isinstance(ch, discord.CategoryChannel):
            continue
        cat = cat_map.get(ch.category_id) if ch.category_id else None
        overwrites = {}
        for t, o in ch.overwrites.items():
            if isinstance(t, discord.Role):
                role = discord.utils.get(target.roles, name=t.name)
                if role:
                    overwrites[role] = o
        try:
            if isinstance(ch, discord.TextChannel):
                await target.create_text_channel(name=ch.name, category=cat, topic=ch.topic, slowmode_delay=ch.slowmode_delay, nsfw=ch.nsfw, position=ch.position, overwrites=overwrites or None)
            elif isinstance(ch, discord.VoiceChannel):
                await target.create_voice_channel(name=ch.name, category=cat, user_limit=ch.user_limit, bitrate=ch.bitrate, position=ch.position, overwrites=overwrites or None)
            await asyncio.sleep(0.5)
        except:
            pass


async def _copy_emojis(source, target):
    count = 0
    for emoji in source.emojis:
        try:
            await target.create_custom_emoji(name=emoji.name, image=await emoji.read(), reason=f"Cloned from {source.name}")
            count += 1
            await asyncio.sleep(0.5)
        except:
            pass
    return count


@bot.group(invoke_without_command=True)
@commands.is_owner()
async def clone(ctx):
    embed = discord.Embed(title="Clone Commands", description="`!clone server <id>`\n`!clone roles <id>`\n`!clone channels <id>`\n`!clone emojis <id>`\n`!clone all <id>`", color=discord.Color.blue())
    await ctx.send(embed=embed)


@clone.command()
@commands.is_owner()
async def server(ctx, server_id: int):
    source, ing = await _get_source(server_id)
    if not source:
        await ctx.send("❌ Server not found.")
        return
    await ctx.send(f"🔄 Copying server info from `{source.name}`...")
    await _copy_server(source, ctx.guild)
    await ctx.send(f"✅ Server name and icon copied from `{source.name}`")


@clone.command()
@commands.is_owner()
async def roles(ctx, server_id: int):
    source, ing = await _get_source(server_id)
    if not source:
        await ctx.send("❌ Server not found.")
        return
    if source.id == ctx.guild.id:
        await ctx.send("❌ Cannot clone roles from the same server.")
        return
    await ctx.send(f"🔄 Cloning roles from `{source.name}`...")
    count = await _copy_roles(source, ctx.guild)
    await ctx.send(f"✅ Created {count} roles from `{source.name}`")


@clone.command()
@commands.is_owner()
async def channels(ctx, server_id: int):
    source = discord.utils.get(bot.guilds, id=server_id)
    if not source:
        await ctx.send("❌ Bot must be in that server to clone channels.")
        return
    if source.id == ctx.guild.id:
        await ctx.send("❌ Cannot clone channels from the same server.")
        return
    await ctx.send(f"🔄 Cloning channels from `{source.name}`...")
    await _copy_channels(source, ctx.guild)
    await ctx.send(f"✅ Channels cloned from `{source.name}`")


@clone.command()
@commands.is_owner()
async def emojis(ctx, server_id: int):
    source, ing = await _get_source(server_id)
    if not source:
        await ctx.send("❌ Server not found.")
        return
    await ctx.send(f"🔄 Cloning emojis from `{source.name}`...")
    count = await _copy_emojis(source, ctx.guild)
    await ctx.send(f"✅ Copied {count} emojis from `{source.name}`")


@clone.command()
@commands.is_owner()
async def all(ctx, server_id: int):
    source, ing = await _get_source(server_id)
    if not source:
        await ctx.send("❌ Server not found.")
        return
    await ctx.send(f"🔄 Full clone from `{source.name}` started...")
    await _copy_server(source, ctx.guild)
    await _copy_roles(source, ctx.guild)
    await _copy_emojis(source, ctx.guild)
    if ing and source.id != ctx.guild.id:
        await _copy_channels(source, ctx.guild)
    elif source.id == ctx.guild.id:
        pass
    else:
        await ctx.send("⚠️ Bot not in target server — channels skipped.")
    await ctx.send(f"✅ Server fully cloned from `{source.name}`")


# ══════════════════════════════════════════════════════════════
# 🚀 ЗАПУСК
# ══════════════════════════════════════════════════════════════

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)


async def setup_hook():
    await load_cogs()

bot.setup_hook = setup_hook


async def main():
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    if not TOKEN:
        print("❌ Установи DISCORD_TOKEN в переменных окружения Render")
        return
    await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
