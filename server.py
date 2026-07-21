import os, json, threading, datetime, asyncio, difflib
from datetime import datetime as dt, timedelta

import requests, aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import View, Modal
from flask import Flask, request, jsonify, render_template_string


# ══════════════════════════════════════════════════════════════
# ⚙️ КОНФИГУРАЦИЯ
# ══════════════════════════════════════════════════════════════

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = 0
PREFIX = "!"

ADMIN_ROLE_ID = 1527423541538979972
GUILD_ID = 1083127357818277938
PUBLIC_REVIEWS_CHANNEL_ID = 1517980239341424800
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1523045988401549396/NxEa66M65uPCdyN68E-pdv4byp7EehCxR0biNUt7ZaZ_XN7qPtkXC3zDyYhRB1LUlNEN"
MASCOT_THUMBNAIL_URL = "https://i.imgur.com/your_mascot.png"
BETA_DURATION_DAYS = 30
KEYS_FILE = "keys.json"
REVIEWS_FILE = "reviews.json"
BLACKLISTED_HWIDS_FILE = "blacklisted_hwids.json"
BRUTE_FORCE_LIMIT = 10
BRUTE_FORCE_WINDOW_MIN = 10
SERVER_URL = "https://scaredopti-api.onrender.com"


# ══════════════════════════════════════════════════════════════
# 🔐 БАЗА КЛЮЧЕЙ
# ══════════════════════════════════════════════════════════════

KEYS_PREFIX = "SCARED"

ALL_KEYS_DATA = {}
_basic = ["0GRF5A4M","0MVAPYIX","0P55CST0","0UPJ6X4H","16FYFTFQ","1KX1H92I","39VA4A62","3DRANVCN","53AF32WY","5TCSMO0W","5ZX65IFA","7BY9KLBA","7F969OL7","7GIU1GUY","7TWIKDSV","88050UMG","8I0L9S1Y","B6U9UEJF","B99CKJZ0","CAU78JM9","CERGLLHO","ED1AYH81","EXFSSLHB","EXGIMMN3","FJSNY16U","G2SJ4AVQ","G94PU2YO","GYLFJYWQ","HG9LJYEW","HO4I7JRF","HYKMDOZE","I0YY22MP","I2KKGZ7Y","IDU3649G","IEAR3TKM","JAP4LKQ7","LGWYVT61","MHU0TIHC","MRJNU1PJ","N5YCZ0G2","NHQ0K4N7","O4TGRRZ6","O6GV9ZJ1","P3MQPS3O","PMZJME7A","Q0XE3ZJL","Q60ORSWJ","SIY657E3","SLSRV5EV","SPHHRT5Z","TB1YJ3KV","TFVVX548","U6GB3KOY","V5Z15U46","V9RPP3FY","VV7IP3O1","XLZQDCKM","Z9Q2FXE7","ZIMZNHJR","ZT0JRIYO"]
_prem = ["01LEM9O1","0FBM2MPP","107RQOJ1","10LN3WBH","1CKMM6R7","1MZIFYIK","3027OZNN","329P0GOA","3PSYL9FS","40YBBXCE","46XTOAMS","4BZPTGJ3","4J9L0ARQ","53HEFPAW","6BVERWWU","6HKXW9S3","7C9OBUS0","AFGB3VQI","AHAA21MF","AJH2HHRE","CT055VX9","EGGURNEY","F38KD12Z","F7U9VNZF","G3HJ1UBF","IIHRFPQV","JG6G8V42","JNCWF97A","K3SP5MWO","KEN8FDS8","KGVM7TBN","KJY3WDUE","KO68N7SD","LL2M2Q5C","M8Y7FF8O","OE53FDZ9","QSI9HVC5","QU6VA5BJ","SZANYS01","TGRWR6TF","THPZLWMV","U5VXE1KR","UPFODCFH","VASUPEW2","VSKC4FV4","VUJBV74K","VXECK2LR","W2JPAW11","WLJOV9NV","X1L9H8TS","XC27B7YC","XEG1S1OD","XMT2J7HZ","XOZ3WSIU","XWQ28MKC","YB2JXI6A","YJUMV7LT","YO2EMVKN","ZR3SGYI0","ZUVBT0RX"]
_owner = ["GODMODE","ALPHA01","BETA002","DELTA03"]

for s in _basic: ALL_KEYS_DATA[f"{KEYS_PREFIX}-BASIC-{s}"] = "BASIC"
for s in _prem: ALL_KEYS_DATA[f"{KEYS_PREFIX}-PREM-{s}"] = "PREMIUM"
for s in _owner: ALL_KEYS_DATA[f"{KEYS_PREFIX}-OWNER-{s}"] = "OWNER"


def load_keys():
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, 'r') as f:
            raw = json.load(f)
            migrated = {}
            for k, v in raw.items():
                for old_prefix in ("SKYEREV-", "SCARED-"):
                    k = k.replace(old_prefix, f"{KEYS_PREFIX}-")
                migrated[k] = v
            return migrated
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
            "last_login_at": None, "banned": False, "ban_reason": None
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
                "footer": {"text": "ScaredOpti Security"}
            }]
        }
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        print(f"[WEBHOOK ERROR] {e}")


# brute-force tracker
brute_force_tracker: dict = {}  # ip -> list of timestamps


def load_blacklisted_hwids():
    if os.path.exists(BLACKLISTED_HWIDS_FILE):
        with open(BLACKLISTED_HWIDS_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_blacklisted_hwids():
    with open(BLACKLISTED_HWIDS_FILE, "w") as f:
        json.dump(list(blacklisted_hwids), f)


blacklisted_hwids = load_blacklisted_hwids()


def is_bruteforce(ip):
    now = dt.now()
    window = timedelta(minutes=BRUTE_FORCE_WINDOW_MIN)
    attempts = brute_force_tracker.get(ip, [])
    attempts = [t for t in attempts if now - t < window]
    brute_force_tracker[ip] = attempts
    return len(attempts) >= BRUTE_FORCE_LIMIT


def record_failed_attempt(ip):
    if ip not in brute_force_tracker:
        brute_force_tracker[ip] = []
    brute_force_tracker[ip].append(dt.now())


# ══════════════════════════════════════════════════════════════
# 🎨 FLASK — API АКТИВАЦИИ
# ══════════════════════════════════════════════════════════════

app = Flask(__name__)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "scaredopti"})


@app.route("/activate", methods=["POST"])
def activate():
    data = request.json
    key = data.get("key", "").strip().upper()
    hwid = data.get("hwid", "").strip()
    client_ip = request.remote_addr

    # brute-force check first
    if is_bruteforce(client_ip):
        return jsonify({"status": "bruteforce_blocked", "message": "Too many failed attempts. Try again later."})

    # HWID blacklist check
    if hwid and hwid in blacklisted_hwids:
        record_failed_attempt(client_ip)
        return jsonify({"status": "hwid_blacklisted", "message": "Your hardware is blacklisted."})

    if not key or key not in keys:
        record_failed_attempt(client_ip)
        return jsonify({"status": "invalid", "message": "Invalid key"})

    k = keys[key]
    if k.get("banned"):
        return jsonify({"status": "banned", "message": f"KEY BANNED ({k.get('ban_reason', 'UNKNOWN')}). Contact support."})

    # permanent keys — no expiry check

    if not k["used"]:
        k.update({
            "used": True, "hwid": hwid, "first_ip": client_ip,
            "activated_at": dt.now().isoformat(), "last_login_at": dt.now().isoformat(),
            "banned": False, "ban_reason": None
        })
        save_keys()
        send_discord_alert("✅ New Activation", f"**Key:** `{key}`\n**Tier:** {k['tier']}\n**IP:** {client_ip}\n**HWID:** `{hwid[:12]}...`", color=0x00FF00)
        return jsonify({"status": "ok", "tier": k["tier"]})

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

    return jsonify({"status": "ok", "tier": k["tier"]})


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


ADMIN_HTML = """<!DOCTYPE html>
<html lang=ru><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>ScaredOpti Admin</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px}
h1{color:#58a6ff;margin-bottom:20px}
.stats{display:flex;gap:15px;flex-wrap:wrap;margin-bottom:25px}
.stat{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:15px 25px;min-width:120px}
.stat .n{font-size:28px;font-weight:700}
.stat .l{font-size:12px;color:#8b949e;margin-top:4px}
.stat.green .n{color:#3fb950}
.stat.red .n{color:#f85149}
.stat.orange .n{color:#d29922}
.stat.blue .n{color:#58a6ff}
section{margin-bottom:30px}
section h2{color:#58a6ff;font-size:18px;margin-bottom:12px}
.search{margin-bottom:15px}
.search input{background:#0d1117;border:1px solid #30363d;color:#c9d1d9;padding:8px 12px;border-radius:6px;width:300px}
table{width:100%;border-collapse:collapse;background:#161b22;border:1px solid #30363d;border-radius:8px;overflow:hidden}
th,td{padding:8px 12px;text-align:left;border-bottom:1px solid #30363d;font-size:13px}
th{background:#21262d;color:#8b949e;font-weight:600}
tr:hover{background:#1c2128}
.key{font-family:monospace;font-size:12px;color:#58a6ff}
.status-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.dot-green{background:#3fb950}
.dot-red{background:#f85149}
.dot-yellow{background:#d29922}
.dot-gray{background:#484f58}
.btn{padding:4px 10px;border-radius:6px;border:1px solid;cursor:pointer;font-size:12px;background:0 0;color:#c9d1d9;margin:0 2px}
.btn-reset{border-color:#d29922;color:#d29922}
.btn-ban{border-color:#f85149;color:#f85149}
.btn-unban{border-color:#3fb950;color:#3fb950}
.tier-basic{color:#8b949e}
.tier-premium{color:#d29922}
.tier-owner{color:#f85149}
.reason{font-size:11px;color:#8b949e}
.blacklist-box{display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap}
.blacklist-box input{background:#0d1117;border:1px solid #30363d;color:#c9d1d9;padding:8px 12px;border-radius:6px;width:300px}
.blacklist-box button{border-color:#f85149;color:#f85149}
</style></head>
<body>
<h1>ScaredOpti Admin</h1>
<div class=stats>
<div class=stat blue><div class=n>{{stats.total}}</div><div class=l>Total</div></div>
<div class=stat green><div class=n>{{stats.active}}</div><div class=l>Active</div></div>
<div class=stat orange><div class=n>{{stats.sharing}}</div><div class=l>Sharing</div></div>
<div class=stat red><div class=n>{{stats.banned}}</div><div class=l>Banned</div></div>
<div class=stat><div class=n>{{stats.unused}}</div><div class=l>Unused</div></div>
</div>
<section>
<h2>HWID Blacklist</h2>
<div class=blacklist-box>
<input id=hwidInput placeholder="HWID to blacklist...">
<button class="btn btn-ban" id="addHwidBtn">Add HWID</button>
</div>
<div id=hwidList></div>
</section>
<section>
<h2>Keys</h2>
<div class=search><input id=search placeholder="Search key / HWID / IP / reason..."></div>
<table><thead><tr><th>Key</th><th>Tier</th><th>Status</th><th>Reason</th><th>HWID</th><th>IP</th><th>Activated</th><th>Actions</th></tr></thead>
<tbody id=tbody>
{% for k,d in keys.items() %}
<tr>
<td class=key>{{k}}</td>
<td class="tier-{{d.tier.lower()}}">{{d.tier}}</td>
<td>{% if d.banned %}<span class=status-dot.dot-red></span>BANNED{% elif d.used %}<span class=status-dot.dot-green></span>Active{% else %}<span class=status-dot.dot-gray></span>Unused{% endif %}</td>
<td class=reason>{{d.ban_reason if d.ban_reason else '-'}}</td>
<td>{{d.hwid[:16] if d.hwid else '-'}}</td>
<td>{{d.first_ip if d.first_ip else '-'}}</td>
<td>{{d.activated_at[:10] if d.activated_at else '-'}}</td>
<td>
<button class="btn btn-reset" data-action="reset" data-key="{{k}}">Reset</button>
{% if d.banned %}
<button class="btn btn-unban" data-action="unban" data-key="{{k}}">Unban</button>
{% else %}
<button class="btn btn-ban" data-action="ban" data-key="{{k}}">Ban</button>
{% endif %}
</td></tr>
{% endfor %}
</tbody></table>
</section>
<script>
function filterTable() {
  var q = document.getElementById('search').value.toLowerCase();
  document.querySelectorAll('#tbody tr').forEach(function(r) {
    r.style.display = r.innerText.toLowerCase().includes(q) ? '' : 'none';
  });
}
function api(a, k) {
  if (a === 'reset' && !confirm('Reset ' + k + '?')) return;
  if (a === 'ban' && !confirm('Ban ' + k + '?')) return;
  fetch('/api/admin/key/' + a, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({key: k})
  })
  .then(function(r) { return r.json(); })
  .then(function(d) {
    if (d.status === 'ok') location.reload();
    else alert(d.error || 'Error');
  });
}
function loadHwids() {
  fetch('/api/admin/blacklist/hwid')
  .then(function(r) { return r.json(); })
  .then(function(d) {
    var el = document.getElementById('hwidList');
    if (!d.hwids || d.hwids.length === 0) {
      el.innerHTML = '<span class=reason>No blacklisted HWIDs</span>';
      return;
    }
    el.innerHTML = d.hwids.map(function(h) {
      return '<span class="hwid-chip">' + h + ' <a href="#" data-hwid="' + h + '" class="rm-hwid">X</a></span>';
    }).join('');
  });
}
function addHwid() {
  var v = document.getElementById('hwidInput').value.trim();
  if (!v) return;
  fetch('/api/admin/blacklist/hwid', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({hwid: v, action: 'add'})
  })
  .then(function(r) { return r.json(); })
  .then(function(d) {
    if (d.status === 'ok') {
      document.getElementById('hwidInput').value = '';
      loadHwids();
    } else alert(d.error || 'Error');
  });
}
function removeHwid(h) {
  if (!confirm('Remove HWID from blacklist?')) return;
  fetch('/api/admin/blacklist/hwid', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({hwid: h, action: 'remove'})
  })
  .then(function(r) { return r.json(); })
  .then(function(d) {
    if (d.status === 'ok') loadHwids();
    else alert(d.error || 'Error');
  });
}
document.addEventListener('DOMContentLoaded', function() {
  document.getElementById('addHwidBtn').addEventListener('click', addHwid);
  document.getElementById('search').addEventListener('input', filterTable);
  document.getElementById('hwidList').addEventListener('click', function(e) {
    if (e.target.classList.contains('rm-hwid')) {
      e.preventDefault();
      var hwid = e.target.getAttribute('data-hwid');
      removeHwid(hwid);
    }
  });
  document.getElementById('tbody').addEventListener('click', function(e) {
    var btn = e.target.closest('button[data-action]');
    if (!btn) return;
    var action = btn.getAttribute('data-action');
    var key = btn.getAttribute('data-key');
    api(action, key);
  });
  loadHwids();
});
</script>
<style>
.hwid-chip {
  display: inline-block;
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 4px;
  padding: 4px 8px;
  margin: 3px;
  font-family: monospace;
  font-size: 12px;
}
.rm-hwid {
  color: #f85149;
  text-decoration: none;
  margin-left: 4px;
}
</style>
</body></html>"""


@app.route("/admin")
def admin_panel():
    stats = {"total": 0, "active": 0, "banned": 0, "sharing": 0, "unused": 0}
    for data in keys.values():
        stats["total"] += 1
        if data["used"] and not data["banned"]:
            stats["active"] += 1
        elif data["banned"] and data.get("ban_reason") == "SHARING":
            stats["sharing"] += 1
        elif data["banned"]:
            stats["banned"] += 1
        else:
            stats["unused"] += 1

    return render_template_string(ADMIN_HTML, stats=stats, keys=keys)


@app.route("/api/admin/key/reset", methods=["POST"])
def admin_key_reset():
    key = request.json.get("key", "").strip().upper()
    if key not in keys:
        return jsonify({"error": "Key not found"}), 404
    keys[key].update({"used": False, "hwid": None, "first_ip": None,
                       "activated_at": None, "last_login_at": None,
                       "expires_at": None, "banned": False, "ban_reason": None})
    save_keys()
    send_discord_alert("🔄 Key Reset", f"**Key:** `{key}` ({keys[key]['tier']})", 0xFFA500)
    return jsonify({"status": "ok"})


@app.route("/api/admin/key/ban", methods=["POST"])
def admin_key_ban():
    key = request.json.get("key", "").strip().upper()
    reason = request.json.get("reason", "MANUAL")
    if key not in keys:
        return jsonify({"error": "Key not found"}), 404
    keys[key].update({"banned": True, "ban_reason": reason})
    save_keys()
    send_discord_alert("⛔ Key Banned", f"**Key:** `{key}` ({keys[key]['tier']})\n**Reason:** {reason}", 0xFF0000)
    return jsonify({"status": "ok"})


@app.route("/api/admin/key/unban", methods=["POST"])
def admin_key_unban():
    key = request.json.get("key", "").strip().upper()
    if key not in keys:
        return jsonify({"error": "Key not found"}), 404
    keys[key].update({"banned": False, "ban_reason": None})
    save_keys()
    send_discord_alert("✅ Key Unbanned", f"**Key:** `{key}` ({keys[key]['tier']})", 0x00FF00)
    return jsonify({"status": "ok"})


@app.route("/api/admin/key/extend", methods=["POST"])
def admin_key_extend():
    key = request.json.get("key", "").strip().upper()
    days = int(request.json.get("days", 30))
    if key not in keys:
        return jsonify({"error": "Key not found"}), 404
    try:
        cur = dt.fromisoformat(keys[key]["expires_at"]) if keys[key].get("expires_at") else dt.now()
    except:
        cur = dt.now()
    keys[key]["expires_at"] = (cur + timedelta(days=days)).isoformat()
    if not keys[key]["used"]:
        keys[key]["used"] = True
        keys[key]["activated_at"] = keys[key].get("activated_at") or dt.now().isoformat()
    save_keys()
    return jsonify({"status": "ok", "expires_at": keys[key]["expires_at"]})


@app.route("/api/admin/blacklist/hwid", methods=["GET", "POST"])
def admin_blacklist_hwid():
    if request.method == "GET":
        return jsonify({"hwids": list(blacklisted_hwids)})
    data = request.json
    hwid = data.get("hwid", "").strip()
    action = data.get("action", "add")
    if not hwid:
        return jsonify({"error": "No HWID"}), 400
    if action == "add":
        blacklisted_hwids.add(hwid)
    elif action == "remove":
        blacklisted_hwids.discard(hwid)
    save_blacklisted_hwids()
    return jsonify({"status": "ok"})


@app.route("/api/check", methods=["POST"])
def api_check():
    data = request.json
    key = data.get("key", "").strip().upper()
    if key not in keys:
        return jsonify({"status": "invalid"})
    k = keys[key]
    if k.get("banned"):
        return jsonify({"status": "banned", "reason": k.get("ban_reason", "MANUAL")})
    return jsonify({"status": "ok", "tier": k["tier"]})


def run_flask():
    port = int(os.environ.get("PORT", 10000))
    print(f"[+] API server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


# ══════════════════════════════════════════════════════════════
# 🤖 DISCORD БОТ
# ══════════════════════════════════════════════════════════════

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)
bot.owner_id = OWNER_ID


# ══════════════════════════════════════════════════════════════
# ⭐ СИСТЕМА ОТЗЫВОВ
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


class LicenseResult:
    def __init__(self, valid: bool, reason: str = "", tier: str = ""):
        self.valid = valid
        self.reason = reason
        self.tier = tier


async def check_license(key):
    normalized = key.strip().upper()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{SERVER_URL}/activate",
                json={"key": normalized, "hwid": "discord_bot_check"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return LicenseResult(False, reason=f"api_error_{resp.status}")
                data = await resp.json()
                if data.get("status") == "ok":
                    return LicenseResult(True, tier=data.get("tier", ""))
                if data.get("status") == "expired":
                    return LicenseResult(False, reason="expired")
                if data.get("status") == "banned":
                    return LicenseResult(False, reason="banned_unknown")
                return LicenseResult(False, reason=data.get("message", "invalid_key"))
    except Exception as e:
        return LicenseResult(False, reason=f"connection_error: {e}")


REASON_TEXT = {
    "invalid_key": "❌ Ключ не найден в базе.",
    "unused": "⚠️ Ключ ещё не активирован — сначала запусти прогу.",
    "banned_sharing": "🚫 Ключ заблокирован за шаринг.",
    "banned_ip_change": "🌐 Ключ заблокирован из-за смены IP.",
    "banned_manual": "⛔ Ключ заблокирован вручную.",
    "banned_unknown": "⛔ Ключ заблокирован.",
    "expired": "⏰ Срок действия ключа истёк.",
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
    if reason.startswith("Invalid"):
        return "❌ Ключ не найден."
    return f"❌ {reason}"

def stars(rating):
    return "⭐" * rating + "☆" * (5 - rating)


def build_review_embed(review, member):
    fb = review["fps_before"]
    fa = review["fps_after"]
    gain = round(((fa - fb) / fb) * 100) if fb else 0

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
    embed.set_footer(text="ScaredOpti Reviews")
    return embed


class LicenseModal(Modal, title="Проверка лицензии"):
    license_key = discord.ui.TextInput(label="Лицензионный ключ", placeholder="SCARED-BASIC-XXXXXXXX", required=True, max_length=100)

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
    channel = bot.get_channel(PUBLIC_REVIEWS_CHANNEL_ID)
    if channel is None:
        await interaction.response.send_message("⚠️ Канал отзывов не настроен.", ephemeral=True)
        return
    member = interaction.user
    embed = build_review_embed(entry, member)
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="📸 BEFORE", url=entry["before_url"]))
    view.add_item(discord.ui.Button(label="📸 AFTER", url=entry["after_url"]))
    await channel.send(embed=embed, view=view)
    await interaction.response.send_message("🎉 Отзыв опубликован!", ephemeral=True)


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

    @discord.ui.button(label="📝 Оставить отзыв", style=discord.ButtonStyle.primary, custom_id="scaredopti:start_review")
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
            f"ticket-{user.name.lower().replace(' ', '-')}", category=category,
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
        try: await self.channel.delete()
        except: pass

    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        await interaction.response.edit_message(content="❌ Отменено.", view=None, delete_after=3)


class TicketActions(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎖️ Выдать роль", style=discord.ButtonStyle.success, custom_id="ticket:role")
    async def assign_role(self, interaction, button):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Только администратор.", ephemeral=True)
            return
        if not interaction.channel.topic or "Роль:" not in interaction.channel.topic:
            await interaction.response.send_message("❌ Информация о роли не найдена.", ephemeral=True)
            return
        try:
            parts = interaction.channel.topic.split(" | ")
            desired_role_name = parts[0].replace("Роль: ", "")
            user_id = int(parts[1].replace("ID: ", ""))
        except:
            await interaction.response.send_message("❌ Ошибка чтения.", ephemeral=True)
            return
        member = interaction.guild.get_member(user_id)
        if not member:
            await interaction.response.send_message("❌ Пользователь не на сервере.", ephemeral=True)
            return
        matches = [r for r in interaction.guild.roles if r.name.lower() == desired_role_name.lower()]
        if not matches:
            close = difflib.get_close_matches(desired_role_name, [r.name for r in interaction.guild.roles], n=3, cutoff=0.5)
            matches = [r for r in interaction.guild.roles if r.name in close]
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

    @discord.ui.button(label="🔒 Закрыть", style=discord.ButtonStyle.danger, custom_id="ticket:close")
    async def close(self, interaction, button):
        embed = discord.Embed(title="Закрыть тикет?", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, view=ConfirmClose(interaction.channel))

    @discord.ui.button(label="➕ Добавить", style=discord.ButtonStyle.success, custom_id="ticket:add")
    async def add_user(self, interaction, button):
        await interaction.response.send_modal(AddUserModal(channel=interaction.channel))


class OpenTicketBtn(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.primary, custom_id="persistent:ticket_open")
    async def create(self, interaction, button):
        await interaction.response.send_modal(AppModal(self.bot))


# ══════════════════════════════════════════════════════════════
# 🤖 СОБЫТИЯ И КОМАНДЫ
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


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)


@bot.command()
async def review(ctx):
    embed = discord.Embed(
        title="📝 Оставить отзыв",
        description="Нажми кнопку ниже, подтверди ключ и напиши отзыв об оптимизации.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=ReviewPanelView())


@bot.command()
@commands.is_owner()
async def ticket(ctx, action: str = None, member: discord.Member = None):
    if not action:
        embed = discord.Embed(title="Команды тикетов", description="`!ticket setup` — Панель\n`!ticket close` — Закрыть\n`!ticket add @user` — Добавить\n`!ticket remove @user` — Убрать", color=discord.Color.blue())
        await ctx.send(embed=embed)
        return
    if action == "setup":
        embed = discord.Embed(title="Подача заявки в клан", description="Нажмите кнопку ниже.\n\nТребования: **от 2 000 часов**.", color=discord.Color.blue())
        await ctx.send(embed=embed, view=OpenTicketBtn(bot))
    elif action == "close":
        if not ctx.channel.name.startswith("ticket-"):
            await ctx.send("❌ Это не тикет.")
            return
        await ctx.send(embed=discord.Embed(title="Закрыть тикет?", color=discord.Color.red()), view=ConfirmClose(ctx.channel))
    elif action == "add":
        if not ctx.channel.name.startswith("ticket-"):
            await ctx.send("❌ Это не тикет.")
            return
        if not member: return await ctx.send("Использование: `!ticket add @user`")
        await ctx.channel.set_permissions(member, read_messages=True, send_messages=True, attach_files=True, embed_links=True)
        await ctx.send(f"✅ {member.mention} добавлен.")
    elif action == "remove":
        if not ctx.channel.name.startswith("ticket-"):
            await ctx.send("❌ Это не тикет.")
            return
        if not member: return await ctx.send("Использование: `!ticket remove @user`")
        await ctx.channel.set_permissions(member, overwrite=None)
        await ctx.send(f"✅ {member.mention} убран.")


@bot.command()
@commands.is_owner()
async def say(ctx, *, message: str):
    await ctx.send(message)


@bot.command()
@commands.is_owner()
async def ping(ctx):
    await ctx.send(f"🏓 {round(bot.latency * 1000)}ms")


# ══════════════════════════════════════════════════════════════
# 🚀 ЗАПУСК
# ══════════════════════════════════════════════════════════════

async def main():
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    if not TOKEN:
        print("❌ Установи DISCORD_TOKEN в переменных окружения Render")
        return
    await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
