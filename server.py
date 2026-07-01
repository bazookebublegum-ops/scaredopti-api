from flask import Flask, request, jsonify, render_template_string
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# ═══════════════════════════════════════════════
# ⚙️ КОНФИГУРАЦИЯ И КЛЮЧИ
# ═══════════════════════════════════════════════
KEYS_FILE = "keys.json"
BETA_DURATION_DAYS = 30

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
            "expires_at": None, "banned": False
        }
    save_keys()
    print(f"[OK] Initialized {len(keys)} keys")

# ═══════════════════════════════════════════════
# 🎨 АДМИНКА С 3 ПЛАШКАМИ И СОРТИРОВКОЙ
# ═══════════════════════════════════════════════
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Scared Opti Admin</title>
    <style>
        :root { --bg: #000; --surface: #0a0a0a; --border: #1a1a1a; --text: #fff; --muted: #666; --danger: #ff0000; --success: #00ff00; --gold: #ffd700; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Courier New', monospace; }
        body { background: var(--bg); color: var(--text); padding: 40px; min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; }
        
        header { border-bottom: 1px solid var(--border); padding-bottom: 20px; margin-bottom: 40px; display: flex; justify-content: space-between; align-items: center; }
        h1 { font-size: 24px; font-weight: normal; letter-spacing: 2px; text-transform: uppercase; }
        
        /* 3 СПЕЦИАЛЬНЫЕ ПЛАШКИ */
        .tier-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 40px; }
        .tier-card { background: var(--surface); border: 1px solid var(--border); padding: 24px; position: relative; overflow: hidden; }
        .tier-card::before { content:''; position:absolute; top:0; left:0; right:0; height:2px; }
        .tier-card.basic::before { background: #444; }
        .tier-card.premium::before { background: var(--gold); }
        .tier-card.owner::before { background: var(--danger); }
        
        .tier-label { font-size: 10px; color: var(--muted); text-transform: uppercase; margin-bottom: 12px; letter-spacing: 1px; }
        .tier-count { font-size: 36px; font-weight: bold; margin-bottom: 8px; }
        .tier-sub { font-size: 11px; color: var(--muted); }
        .tier-sub span { color: var(--text); }
        
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 1px solid var(--border); }
        .tab { padding: 10px 20px; cursor: pointer; color: var(--muted); text-transform: uppercase; font-size: 12px; border-bottom: 2px solid transparent; transition: all 0.2s; }
        .tab:hover { color: var(--text); }
        .tab.active { color: var(--text); border-bottom-color: var(--text); }
        
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
        .badge-premium { border-color: var(--gold); color: var(--gold); }
        .badge-owner { border-color: var(--danger); color: var(--danger); }
        
        .status-active { color: var(--success); }
        .status-banned { color: var(--danger); font-weight: bold; }
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
            <div style="font-size: 10px; color: var(--muted);">v2.2 TIER CARDS</div>
        </header>
        
        <!-- 3 СПЕЦИАЛЬНЫЕ ПЛАШКИ -->
        <div class="tier-cards">
            <div class="tier-card basic">
                <div class="tier-label">Basic Keys</div>
                <div class="tier-count" id="basicCount">0</div>
                <div class="tier-sub"><span id="basicUsed">0</span> used / <span id="basicTotal">0</span> total</div>
            </div>
            <div class="tier-card premium">
                <div class="tier-label">Premium Keys</div>
                <div class="tier-count" id="premCount">0</div>
                <div class="tier-sub"><span id="premUsed">0</span> used / <span id="premTotal">0</span> total</div>
            </div>
            <div class="tier-card owner">
                <div class="tier-label">Owner Keys</div>
                <div class="tier-count" id="ownerCount">0</div>
                <div class="tier-sub"><span id="ownerUsed">0</span> used / <span id="ownerTotal">0</span> total</div>
            </div>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="switchTab('all')" id="tab-all">All Keys</div>
            <div class="tab" onclick="switchTab('used')" id="tab-used">Used Keys</div>
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
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="keysTable"></tbody>
        </table>
    </div>

    <script>
        let currentTab = 'all';
        let sortField = 'key';
        let sortAsc = true;
        let allKeysData = [];

        async function load() {
            const res = await fetch('/api/admin/keys');
            const data = await res.json();
            allKeysData = data.keys;
            
            // Обновляем 3 специальные плашки
            const tiers = { BASIC: {total:0, used:0}, PREMIUM: {total:0, used:0}, OWNER: {total:0, used:0} };
            data.keys.forEach(k => {
                if(tiers[k.tier]) {
                    tiers[k.tier].total++;
                    if(k.used) tiers[k.tier].used++;
                }
            });
            
            document.getElementById('basicTotal').textContent = tiers.BASIC.total;
            document.getElementById('basicUsed').textContent = tiers.BASIC.used;
            document.getElementById('basicCount').textContent = tiers.BASIC.total - tiers.BASIC.used;
            
            document.getElementById('premTotal').textContent = tiers.PREMIUM.total;
            document.getElementById('premUsed').textContent = tiers.PREMIUM.used;
            document.getElementById('premCount').textContent = tiers.PREMIUM.total - tiers.PREMIUM.used;
            
            document.getElementById('ownerTotal').textContent = tiers.OWNER.total;
            document.getElementById('ownerUsed').textContent = tiers.OWNER.used;
            document.getElementById('ownerCount').textContent = tiers.OWNER.total - tiers.OWNER.used;
            
            renderTable();
        }
        
        function switchTab(tab) {
            currentTab = tab;
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById(`tab-${tab}`).classList.add('active');
            renderTable();
        }
        
        function sortTable(field) {
            if (sortField === field) sortAsc = !sortAsc;
            else { sortField = field; sortAsc = true; }
            
            document.querySelectorAll('.sort-arrow').forEach(a => a.textContent = '');
            document.getElementById(`arrow-${field}`).textContent = sortAsc ? '▲' : '▼';
            
            renderTable();
        }
        
        function renderTable() {
            let filtered = currentTab === 'used' ? allKeysData.filter(k => k.used) : allKeysData;
            
            filtered.sort((a, b) => {
                let valA = a[sortField] || '';
                let valB = b[sortField] || '';
                
                if (sortField === 'status') {
                    valA = a.banned ? 2 : (a.used ? 1 : 0);
                    valB = b.banned ? 2 : (b.used ? 1 : 0);
                }
                
                if (valA < valB) return sortAsc ? -1 : 1;
                if (valA > valB) return sortAsc ? 1 : -1;
                return 0;
            });
            
            document.getElementById('keysTable').innerHTML = filtered.map(k => `
                <tr style="${k.banned ? 'opacity:0.5' : ''}">
                    <td style="font-family:monospace">${k.key}</td>
                    <td><span class="badge badge-${k.tier.toLowerCase()}">${k.tier}</span></td>
                    <td class="${k.banned ? 'status-banned' : (k.used ? 'status-active' : 'status-unused')}">
                        ${k.banned ? 'BANNED' : (k.used ? 'ACTIVE' : 'UNUSED')}
                    </td>
                    <td style="color:var(--muted); font-size:10px;">
                        ${k.hwid ? k.hwid.substring(0,12)+'...' : '-'}<br>
                        ${k.first_ip || '-'}
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
        
        async function ban(key) { await fetch('/api/admin/ban', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({key})}); load(); }
        async function unban(key) { await fetch('/api/admin/unban', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({key})}); load(); }
        async function del(key) { if(confirm('Delete '+key+'?')) { await fetch('/api/admin/delete', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({key})}); load(); } }
        
        load();
        setInterval(load, 5000);
    </script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(ADMIN_HTML)

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
        return jsonify({"status": "banned", "message": "SHARING DETECTED. Contact support in discord."})
    
    if k.get("expires_at"):
        try:
            if datetime.now() > datetime.fromisoformat(k["expires_at"]):
                return jsonify({"status": "expired", "message": "License expired"})
        except: pass
    
    if not k["used"]:
        now = datetime.now()
        expires = now + timedelta(days=BETA_DURATION_DAYS)
        k.update({"used": True, "hwid": hwid, "first_ip": client_ip, "activated_at": now.isoformat(), "expires_at": expires.isoformat()})
        save_keys()
        return jsonify({"status": "ok", "tier": k["tier"], "expires_at": int(expires.timestamp())})
    
    if k["hwid"] != hwid:
        k["banned"] = True
        save_keys()
        return jsonify({"status": "banned", "message": "SHARING DETECTED. Contact support in discord."})
    
    exp_ts = 0
    if k.get("expires_at"):
        try: exp_ts = int(datetime.fromisoformat(k["expires_at"]).timestamp())
        except: pass
        
    return jsonify({"status": "ok", "tier": k["tier"], "expires_at": exp_ts})

@app.route("/api/admin/keys")
def admin_keys():
    keys_list = []
    for key, data in keys.items():
        keys_list.append({"key": key, "tier": data["tier"], "used": data["used"], "hwid": data["hwid"], "first_ip": data["first_ip"], "activated_at": data["activated_at"], "banned": data["banned"]})
    return jsonify({"keys": keys_list})

@app.route("/api/admin/add", methods=["POST"])
def admin_add():
    d = request.json
    if d["key"] in keys: return jsonify({"status": "error"})
    keys[d["key"]] = {"used":False,"tier":d["tier"],"hwid":None,"first_ip":None,"activated_at":None,"expires_at":None,"banned":False}
    save_keys()
    return jsonify({"status": "ok"})

@app.route("/api/admin/ban", methods=["POST"])
def admin_ban():
    k = request.json["key"]
    if k in keys: keys[k]["banned"] = True; save_keys()
    return jsonify({"status": "ok"})

@app.route("/api/admin/unban", methods=["POST"])
def admin_unban():
    k = request.json["key"]
    if k in keys: keys[k]["banned"] = False; save_keys()
    return jsonify({"status": "ok"})

@app.route("/api/admin/delete", methods=["POST"])
def admin_del():
    k = request.json["key"]
    if k in keys: del keys[k]; save_keys()
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🔐 Scared Opti Server v2.2 | Port: {port} | Keys: {len(keys)}")
    app.run(host="0.0.0.0", port=port, debug=False)
