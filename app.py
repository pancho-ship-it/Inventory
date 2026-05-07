
import os, json, uuid
from datetime import datetime
from functools import wraps
from flask import Flask, jsonify, request, render_template, session, redirect, url_for

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── SUPABASE CONFIG ───────────────────────────────────────────────────────────
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_ANON_KEY', '')

def sb_headers():
    return {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }

def sb_get(table, params=''):
    import urllib.request
    url = f"{SUPABASE_URL}/rest/v1/{table}?{params}"
    req = urllib.request.Request(url, headers=sb_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"sb_get error [{table}]: {e}"); return []

def sb_post(table, data):
    import urllib.request
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    req = urllib.request.Request(url, data=json.dumps(data).encode(), method='POST', headers=sb_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
            return result[0] if isinstance(result, list) and result else result
    except urllib.error.HTTPError as e:
        print(f"sb_post error [{table}] {e.code}: {e.read().decode()}"); return {}
    except Exception as e:
        print(f"sb_post error [{table}]: {e}"); return {}

def sb_patch(table, match_col, match_val, data):
    import urllib.request
    url = f"{SUPABASE_URL}/rest/v1/{table}?{match_col}=eq.{match_val}"
    print(f"sb_patch [{table}] url={url} data={json.dumps(data)}")
    req = urllib.request.Request(url, data=json.dumps(data).encode(), method='PATCH', headers=sb_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body = r.read().decode()
            print(f"sb_patch [{table}] status={r.status} body={body}")
            return r.status < 300
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"sb_patch error [{table}] {e.code}: {err}"); return False
    except Exception as e:
        print(f"sb_patch error [{table}]: {e}"); return False

def sb_delete(table, match_col, match_val):
    import urllib.request
    url = f"{SUPABASE_URL}/rest/v1/{table}?{match_col}=eq.{match_val}"
    req = urllib.request.Request(url, method='DELETE', headers=sb_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status < 300
    except Exception as e:
        print(f"sb_delete error [{table}]: {e}"); return False

USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)
print(f"USE_SUPABASE = {USE_SUPABASE}")

# ── FLASK APP ─────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder=BASE_DIR)
app.secret_key = os.environ.get('SECRET_KEY', 'rmgc-change-this-secret-2024')

USERS = {
    'admin':  os.environ.get('PASS_ADMIN',  'NP2026'),
    'greens': os.environ.get('PASS_GREENS', 'LB2026'),
}

# ── DEFAULT DATA (file fallback only) ─────────────────────────────────────────
DEFAULT_PRODUCTS = [
  {"id":"1","name":"Grisu (Iprodione)","category":"Fungicide","activeIngredient":"Iprodione","unitSize":1.0,"unit":"L","packCost":41.5,"supplier":"Ortis","stock":0.5,"reorderLevel":2.0,"notes":""},
  {"id":"2","name":"Emerald Fungicide","category":"Fungicide","activeIngredient":"Boscalid 70% WG","unitSize":1.0,"unit":"kg","packCost":25.0,"supplier":"Ortis","stock":1.0,"reorderLevel":2.0,"notes":""},
  {"id":"3","name":"Aliette WG","category":"Fungicide","activeIngredient":"Fosetyl-Aluminium 80%","unitSize":1.0,"unit":"kg","packCost":28.50,"supplier":"Ortis","stock":2.0,"reorderLevel":2.0,"notes":"FRAC P07"},
  {"id":"4","name":"Previter","category":"Fungicide","activeIngredient":"Propiconazole 250 g/L","unitSize":1.0,"unit":"L","packCost":22.00,"supplier":"Ortis","stock":1.0,"reorderLevel":2.0,"notes":"FRAC 3"},
  {"id":"5","name":"Eagle 20EW","category":"Fungicide","activeIngredient":"Myclobutanil 20%","unitSize":1.0,"unit":"L","packCost":30.5,"supplier":"Ortis","stock":2.0,"reorderLevel":2.0,"notes":"FRAC 3"},
  {"id":"6","name":"Feinzin (Metribuzin)","category":"Herbicide","activeIngredient":"Metribuzin 35 g/kg","unitSize":0.5,"unit":"kg","packCost":5.0,"supplier":"Ortis","stock":10.0,"reorderLevel":3.0,"notes":""},
  {"id":"7","name":"Foxtail (Fenoxaprop)","category":"Herbicide","activeIngredient":"Fenoxaprop 28 g/L","unitSize":1.0,"unit":"L","packCost":5.0,"supplier":"Ortis","stock":9.0,"reorderLevel":3.0,"notes":""},
  {"id":"8","name":"Hi Aktiv","category":"Herbicide","activeIngredient":"Glyphosate 490 g/L","unitSize":5.0,"unit":"L","packCost":40.89,"supplier":"RT","stock":4.0,"reorderLevel":2.0,"notes":""},
  {"id":"9","name":"Junction (Florasulam+2,4D)","category":"Herbicide","activeIngredient":"Florasulam + 2,4-D","unitSize":5.0,"unit":"L","packCost":231.79,"supplier":"RT","stock":10.0,"reorderLevel":3.0,"notes":""},
  {"id":"10","name":"Titus + Vibolt","category":"Herbicide","activeIngredient":"Rimsulfuron + Adjuvant","unitSize":0.5,"unit":"kg","packCost":33.93,"supplier":"Nexles","stock":4.0,"reorderLevel":2.0,"notes":""},
  {"id":"11","name":"Mavrik","category":"Herbicide","activeIngredient":"Tau-fluvalinate","unitSize":5.0,"unit":"mL","packCost":1.45,"supplier":"Nexles","stock":10.0,"reorderLevel":3.0,"notes":""},
  {"id":"12","name":"Dicopur Top + Cerlit","category":"Herbicide","activeIngredient":"MCPA + Dicamba / Mecoprop-P","unitSize":1.0,"unit":"L","packCost":19.7,"supplier":"Nexles","stock":13.0,"reorderLevel":3.0,"notes":""},
  {"id":"13","name":"Kerb Flo 400 SC","category":"Herbicide","activeIngredient":"Propyzamide 400 g/L","unitSize":1.0,"unit":"L","packCost":80.0,"supplier":"Agius","stock":1.0,"reorderLevel":2.0,"notes":"Apply soil temp <10°C"},
  {"id":"14","name":"Kerb 80","category":"Herbicide","activeIngredient":"Propyzamide 800 g/kg","unitSize":1.0,"unit":"kg","packCost":132.0,"supplier":"Agius","stock":0.0,"reorderLevel":1.0,"notes":""},
  {"id":"15","name":"Stomp","category":"Herbicide","activeIngredient":"Pendimethalin 330 g/L","unitSize":1.0,"unit":"L","packCost":28.91,"supplier":"Nexles","stock":2.0,"reorderLevel":2.0,"notes":""},
  {"id":"16","name":"Cerlit","category":"Herbicide","activeIngredient":"Mecoprop-P","unitSize":1.0,"unit":"L","packCost":61.04,"supplier":"Nexles","stock":12.0,"reorderLevel":3.0,"notes":""},
  {"id":"17","name":"Pendimethalin 33 EC","category":"Herbicide","activeIngredient":"Pendimethalin 330 g/L","unitSize":5.0,"unit":"L","packCost":38.50,"supplier":"Various","stock":4.0,"reorderLevel":2.0,"notes":"Pre-emergent – Poa annua"},
  {"id":"18","name":"Euiq","category":"Herbicide","activeIngredient":"Foramsulfuron","unitSize":1.0,"unit":"L","packCost":50.0,"supplier":"","stock":10.0,"reorderLevel":2.0,"notes":""},
  {"id":"19","name":"Clearcast Herbicide","category":"Insecticide","activeIngredient":"Ammonium salt of imazamox 12.1%","unitSize":10.0,"unit":"L","packCost":45.0,"supplier":"RT","stock":1.0,"reorderLevel":2.0,"notes":""},
  {"id":"20","name":"Lepinox","category":"Insecticide","activeIngredient":"Bacillus thuringiensis","unitSize":2.0,"unit":"kg","packCost":29.92,"supplier":"Ortis","stock":1.0,"reorderLevel":2.0,"notes":"Biological"},
  {"id":"21","name":"Mospilan 20 SG","category":"Insecticide","activeIngredient":"Acetamiprid 20%","unitSize":0.5,"unit":"kg","packCost":132.0,"supplier":"Ortis","stock":1.5,"reorderLevel":2.0,"notes":"IRAC 4A"},
  {"id":"22","name":"Deltagri EC","category":"Insecticide","activeIngredient":"Deltamethrin 2.5%","unitSize":1.0,"unit":"L","packCost":30.0,"supplier":"Ortis","stock":2.0,"reorderLevel":2.0,"notes":"HIGH HAZARD near water"},
  {"id":"23","name":"Maintain PGR","category":"PGR","activeIngredient":"Trinexapac-ethyl 120 g/L","unitSize":5.0,"unit":"L","packCost":243.99,"supplier":"RT","stock":11.0,"reorderLevel":3.0,"notes":"Group 16"},
  {"id":"24","name":"Duraline Flush Thru","category":"Wetting Agent","activeIngredient":"Pipe cleaner / flush agent","unitSize":10.0,"unit":"L","packCost":20.0,"supplier":"RT","stock":1.0,"reorderLevel":1.0,"notes":""},
  {"id":"25","name":"Revolution Wetting Agent","category":"Wetting Agent","activeIngredient":"Proprietary polyether polymers","unitSize":10.0,"unit":"L","packCost":202.0,"supplier":"Rimesa","stock":0.0,"reorderLevel":5.0,"notes":"20 L/ha on greens Mar–Sep"},
  {"id":"26","name":"K 0-0-50 WS","category":"Fertiliser","activeIngredient":"Potassium sulphate 0-0-50","unitSize":25.0,"unit":"kg","packCost":10.0,"supplier":"Agius","stock":12.0,"reorderLevel":3.0,"notes":""},
  {"id":"27","name":"Microlite TE","category":"Fertiliser","activeIngredient":"Trace elements blend","unitSize":20.0,"unit":"kg","packCost":44.71,"supplier":"RT","stock":5.0,"reorderLevel":2.0,"notes":""},
  {"id":"28","name":"Trimate (Amino+Fulvic)","category":"Fertiliser","activeIngredient":"L-form amino acids, Fulvic Acid","unitSize":5.0,"unit":"L","packCost":34.33,"supplier":"RT","stock":7.0,"reorderLevel":2.0,"notes":"Biostimulant"},
  {"id":"29","name":"Urea 46-0-0","category":"Fertiliser","activeIngredient":"Urea 46%N","unitSize":25.0,"unit":"kg","packCost":13.78,"supplier":"Ortis","stock":1.0,"reorderLevel":3.0,"notes":""},
  {"id":"30","name":"12-12-17 Granular","category":"Fertiliser","activeIngredient":"NPK 12-12-17","unitSize":25.0,"unit":"kg","packCost":23.82,"supplier":"Ortis","stock":0.0,"reorderLevel":3.0,"notes":""},
  {"id":"31","name":"Calcium Nitrate","category":"Fertiliser","activeIngredient":"Calcium Nitrate 15.5% N","unitSize":25.0,"unit":"kg","packCost":18.50,"supplier":"Ortis","stock":0.0,"reorderLevel":2.0,"notes":""},
  {"id":"32","name":"Potassium Nitrate","category":"Fertiliser","activeIngredient":"Potassium Nitrate 13% N 46% K","unitSize":25.0,"unit":"kg","packCost":24.00,"supplier":"Ortis","stock":1.0,"reorderLevel":2.0,"notes":""},
  {"id":"33","name":"Magnesium Nitrate","category":"Fertiliser","activeIngredient":"Magnesium Nitrate 11% N 15% Mg","unitSize":25.0,"unit":"kg","packCost":21.50,"supplier":"Ortis","stock":1.0,"reorderLevel":2.0,"notes":""},
  {"id":"34","name":"Greenlawnger","category":"Colorant","activeIngredient":"Green pigment / colorant blend","unitSize":1.0,"unit":"L","packCost":23.35,"supplier":"AGV","stock":0.0,"reorderLevel":3.0,"notes":""},
  {"id":"35","name":"Duraline Spray Paint Yellow","category":"Paint","activeIngredient":"Aerosol paint – yellow","unitSize":6.0,"unit":"cans","packCost":4.27,"supplier":"RT","stock":6.0,"reorderLevel":2.0,"notes":"Box of 6"},
  {"id":"36","name":"Duraline Spray Paint White","category":"Paint","activeIngredient":"Aerosol paint – white","unitSize":6.0,"unit":"cans","packCost":4.27,"supplier":"RT","stock":6.0,"reorderLevel":2.0,"notes":"Box of 6"},
  {"id":"37","name":"Duraline Spray Paint Red","category":"Paint","activeIngredient":"Aerosol paint – red","unitSize":6.0,"unit":"cans","packCost":4.27,"supplier":"RT","stock":3.0,"reorderLevel":2.0,"notes":"Box of 6"},
  {"id":"38","name":"Par Aide Blue","category":"Paint","activeIngredient":"Line marking paint – blue","unitSize":500.0,"unit":"gr","packCost":11.7,"supplier":"Duchell","stock":8.0,"reorderLevel":3.0,"notes":""},
  {"id":"39","name":"Par Aide Red","category":"Paint","activeIngredient":"Line marking paint – red","unitSize":500.0,"unit":"gr","packCost":11.7,"supplier":"Duchell","stock":15.0,"reorderLevel":3.0,"notes":""},
  {"id":"40","name":"Par Aide Yellow","category":"Paint","activeIngredient":"Line marking paint – yellow","unitSize":500.0,"unit":"gr","packCost":11.7,"supplier":"Duchell","stock":28.0,"reorderLevel":5.0,"notes":""},
  {"id":"41","name":"Par Aide White","category":"Paint","activeIngredient":"Line marking paint – white","unitSize":500.0,"unit":"gr","packCost":8.9,"supplier":"Duchell","stock":7.0,"reorderLevel":3.0,"notes":""},
  {"id":"42","name":"Par Aide Green","category":"Paint","activeIngredient":"Line marking paint – green","unitSize":500.0,"unit":"gr","packCost":11.7,"supplier":"Duchell","stock":6.0,"reorderLevel":3.0,"notes":""},
  {"id":"43","name":"Thunder Ryegrass","category":"Seeds","activeIngredient":"Perennial ryegrass blend","unitSize":22.7,"unit":"kg","packCost":70.14,"supplier":"Navarro M.","stock":0.0,"reorderLevel":1.0,"notes":""},
  {"id":"44","name":"Bentgrass Tour Pro","category":"Seeds","activeIngredient":"Creeping bentgrass","unitSize":11.0,"unit":"kg","packCost":489.36,"supplier":"Navarro M.","stock":2.0,"reorderLevel":1.0,"notes":"Greens renovation"},
  {"id":"45","name":"Rugby Pitch Paint","category":"Seeds","activeIngredient":"White line marking paint","unitSize":5.0,"unit":"kg","packCost":16.0,"supplier":"Big Mat","stock":4.0,"reorderLevel":2.0,"notes":""}
]

DEFAULT_SPRAY_LOG = [
  {"id":"sl1","date":"05/01/2026","product":"Pendimethalin 33 EC","ai":"Pendimethalin 330 g/L","type":"Herbicide","zone":"Fairways","areaha":5,"rate":3.3,"total":16.5,"notes":"Pre-emergent – Poa annua"},
  {"id":"sl2","date":"06/02/2026","product":"Pendimethalin 33 EC","ai":"Pendimethalin 330 g/L","type":"Herbicide","zone":"Rough","areaha":5,"rate":3.3,"total":16.5,"notes":"Pre-emergent – Poa annua"},
  {"id":"sl3","date":"10/02/2026","product":"Emerald Fungicide","ai":"Boscalid 70% WG","type":"Fungicide","zone":"Fairways","areaha":2,"rate":1,"total":2,"notes":"Post-emergence fungicide"},
  {"id":"sl4","date":"25/02/2026","product":"Dicopur Top + Cerlit","ai":"MCPA + Dicamba / Mecoprop-P","type":"Herbicide","zone":"Fairways","areaha":2,"rate":1,"total":2,"notes":"Post-emergence weed control"},
  {"id":"sl5","date":"26/02/2026","product":"Dicopur Top + Cerlit","ai":"MCPA + Dicamba / Mecoprop-P","type":"Herbicide","zone":"Rough","areaha":2,"rate":1,"total":2,"notes":"Post-emergence weed control"},
  {"id":"sl6","date":"27/02/2026","product":"Emerald Fungicide","ai":"Boscalid 70% WG","type":"Fungicide","zone":"Fairways","areaha":1,"rate":1,"total":1,"notes":"Post-emergence fungicide"},
  {"id":"sl7","date":"27/02/2026","product":"Hi Aktiv","ai":"Glyphosate 490 g/L","type":"Herbicide","zone":"Rough","areaha":None,"rate":None,"total":None,"notes":"Post-emergence weed control"},
  {"id":"sl8","date":"02/03/2026","product":"Emerald Fungicide","ai":"Boscalid 70% WG","type":"Fungicide","zone":"Fairways","areaha":2,"rate":1,"total":2,"notes":"Post-emergence fungicide"},
  {"id":"sl9","date":"02/03/2026","product":"Dicopur Top + Cerlit","ai":"MCPA + Dicamba / Mecoprop-P","type":"Herbicide","zone":"Rough","areaha":2,"rate":1,"total":2,"notes":"Post-emergence weed control"},
  {"id":"sl10","date":"06/03/2026","product":"Emerald Fungicide","ai":"Boscalid 70% WG","type":"Fungicide","zone":"Fairways","areaha":1,"rate":1,"total":1,"notes":"Post-emergence fungicide"},
  {"id":"sl11","date":"09/03/2026","product":"Revolution Wetting Agent","ai":"Proprietary polyether polymers","type":"Wetting Agent","zone":"Greens","areaha":1,"rate":20,"total":20,"notes":"Wetting agent"},
  {"id":"sl12","date":"11/03/2026","product":"Dicopur Top + Cerlit","ai":"MCPA + Dicamba / Mecoprop-P","type":"Herbicide","zone":"Tees","areaha":1,"rate":1,"total":1,"notes":"Post-emergence weed control"},
  {"id":"sl13","date":"11/03/2026","product":"Dicopur Top + Cerlit","ai":"MCPA + Dicamba / Mecoprop-P","type":"Herbicide","zone":"Bunker faces","areaha":None,"rate":1,"total":None,"notes":"Weed control + growth regulator"},
  {"id":"sl14","date":"12/03/2026","product":"Mospilan 20 SG","ai":"Acetamiprid 20%","type":"Insecticide","zone":"Palm trees","areaha":None,"rate":None,"total":None,"notes":"Red weevil control"},
  {"id":"sl15","date":"16/03/2026","product":"Emerald Fungicide","ai":"Boscalid 70% WG","type":"Fungicide","zone":"Fairways","areaha":2,"rate":1,"total":2,"notes":"Post-emergence fungicide"},
  {"id":"sl16","date":"18/03/2026","product":"Stomp","ai":"Pendimethalin 330 g/L","type":"Herbicide","zone":"Greens","areaha":1,"rate":1,"total":1,"notes":"Pre-emergent – Poa annua"}
]

# ── FILE FALLBACK ─────────────────────────────────────────────────────────────
_tmp_data   = '/tmp/rmgc_data.json'
_local_data = os.path.join(BASE_DIR, 'data.json')
DATA_FILE   = _tmp_data if not os.access(BASE_DIR, os.W_OK) else _local_data

def load_data():
    if not os.path.exists(DATA_FILE):
        data = {"products": DEFAULT_PRODUCTS, "log": [], "sprayLog": DEFAULT_SPRAY_LOG}
        save_data(data); return data
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if "sprayLog" not in data: data["sprayLog"] = DEFAULT_SPRAY_LOG
    return data

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── SUPABASE-AWARE GETTERS ────────────────────────────────────────────────────
def get_products_data():
    if USE_SUPABASE:
        rows = sb_get('rmgc_products', 'order=name.asc')
        return rows if isinstance(rows, list) else []
    return load_data()['products']

def get_spraylog_data():
    if USE_SUPABASE:
        rows = sb_get('rmgc_spraylog', 'order=date.desc')
        return rows if isinstance(rows, list) else []
    return load_data()['sprayLog']

def get_stocklog_data():
    if USE_SUPABASE:
        rows = sb_get('rmgc_stock_log', 'order=date.desc&limit=500')
        return rows if isinstance(rows, list) else []
    return load_data().get('log', [])

# ── AUTH ──────────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RMGC Stock Manager – Login</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:#0e0f11;color:#f0f0f0;font-family:'Segoe UI',system-ui,sans-serif;
       min-height:100vh;display:flex;align-items:center;justify-content:center}
  .card{background:#1a1b1e;border:1px solid #2a2b2e;border-radius:12px;padding:40px 36px;width:100%;max-width:380px}
  .logo{text-align:center;margin-bottom:28px}
  .logo img{height:60px;border-radius:8px}
  .logo h1{font-size:20px;font-weight:600;margin-top:12px}
  .logo p{font-size:13px;color:#888;margin-top:4px}
  label{display:block;font-size:13px;color:#aaa;margin-bottom:6px}
  input{width:100%;background:#0e0f11;border:1px solid #333;border-radius:8px;
        padding:10px 14px;color:#f0f0f0;font-size:14px;margin-bottom:18px;outline:none}
  input:focus{border-color:#4ade80}
  button{width:100%;background:#16a34a;color:#fff;border:none;border-radius:8px;
         padding:11px;font-size:15px;font-weight:600;cursor:pointer}
  button:hover{background:#15803d}
  .err{color:#f87171;font-size:13px;margin-top:12px;text-align:center}
</style>
</head>
<body>
<div class="card">
  <div class="logo">
    <img src="/logo" onerror="this.style.display='none'" alt="RMGC">
    <h1>RMGC Stock Manager</h1>
    <p>Royal Malta Golf Club</p>
  </div>
  <label>Username</label>
  <input id="u" type="text" placeholder="username" autocomplete="username">
  <label>Password</label>
  <input id="p" type="password" placeholder="password" autocomplete="current-password">
  <button onclick="doLogin()">Sign In</button>
  <div class="err" id="err"></div>
</div>
<script>
  document.addEventListener('keydown',e=>{if(e.key==='Enter')doLogin()});
  async function doLogin(){
    const r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({username:document.getElementById('u').value.trim(),
                           password:document.getElementById('p').value})});
    if(r.ok)window.location='/';
    else{const d=await r.json();document.getElementById('err').textContent=d.error||'Login failed';}
  }
</script>
</body></html>"""

# ── ROUTES ────────────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET'])
def login_page():
    if 'user' in session: return redirect(url_for('index'))
    return LOGIN_HTML

@app.route('/login', methods=['POST'])
def do_login():
    data = request.get_json() or {}
    u = data.get('username', '').strip().lower()
    p = data.get('password', '')
    if u in USERS and USERS[u] == p:
        session['user'] = u; return jsonify({'ok': True})
    return jsonify({'error': 'Invalid username or password'}), 401

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login_page'))

@app.route('/')
@login_required
def index():
    return render_template('index.html', current_user=session.get('user'))

@app.route('/logo')
def get_logo():
    from flask import send_file
    for ext in ['jpg','jpeg','png','gif','svg']:
        path = os.path.join(BASE_DIR, f'RMGC_LOGO.{ext}')
        if os.path.exists(path): return send_file(path)
    return '', 404

# ── PRODUCTS ──────────────────────────────────────────────────────────────────
@app.route('/api/products', methods=['GET'])
@login_required
def get_products(): return jsonify(get_products_data())

@app.route('/api/products', methods=['POST'])
@login_required
def add_product():
    p = request.json; p['id'] = str(uuid.uuid4())
    p.setdefault('stock', 0); p.setdefault('reorderLevel', 2); p.setdefault('notes', '')
    if USE_SUPABASE:
        supabase_p = {**p}
        if 'containerCount' in supabase_p:
            supabase_p['reorderLevel'] = supabase_p.pop('containerCount')
        return jsonify(sb_post('rmgc_products', supabase_p)), 201
    data = load_data(); data['products'].append(p); save_data(data)
    return jsonify(p), 201

@app.route('/api/products/<pid>', methods=['PUT'])
@login_required
def update_product(pid):
    body = request.json; body.pop('id', None)
    if USE_SUPABASE:
        supabase_body = {**body}
        if 'containerCount' in supabase_body:
            supabase_body['reorderLevel'] = supabase_body.pop('containerCount')
        sb_patch('rmgc_products', 'id', pid, supabase_body)
        updated = sb_get('rmgc_products', f'id=eq.{pid}')
        return jsonify(updated[0] if updated else {'id': pid, **body})
    data = load_data()
    for i, p in enumerate(data['products']):
        if str(p['id']) == str(pid):
            data['products'][i] = {**p, **body, 'id': pid}; save_data(data)
            return jsonify(data['products'][i])
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/products/<pid>', methods=['DELETE'])
@login_required
def delete_product(pid):
    if USE_SUPABASE:
        sb_delete('rmgc_products', 'id', pid); return jsonify({'ok': True})
    data = load_data()
    data['products'] = [p for p in data['products'] if str(p['id']) != str(pid)]
    save_data(data); return jsonify({'ok': True})

# ── STOCK MOVEMENTS ───────────────────────────────────────────────────────────
@app.route('/api/stock/<pid>', methods=['POST'])
@login_required
def update_stock(pid):
    body  = request.json
    qty   = float(body.get('qty', 0))
    mtype = body.get('type', 'usage')
    note  = body.get('note', '')

    if USE_SUPABASE:
        prods = sb_get('rmgc_products', f'id=eq.{pid}')
        if not prods: return jsonify({'error': 'Not found'}), 404
        p = prods[0]; old = float(p.get('stock', 0))
        if   mtype == 'delivery': new_stock = round(old + qty, 4)
        elif mtype == 'usage':    new_stock = round(max(0, old - qty), 4)
        elif mtype == 'adjust':   new_stock = round(qty, 4)
        else:                     new_stock = old
        sb_patch('rmgc_products', 'id', pid, {'stock': new_stock})
        p['stock'] = new_stock
        entry = {'id': str(uuid.uuid4()), 'productId': pid, 'product': p['name'],
                 'type': mtype, 'qty': qty, 'before': old, 'after': new_stock,
                 'unit': p.get('unit', ''), 'note': note,
                 'date': datetime.now().strftime('%d/%m/%Y %H:%M')}
        try: sb_post('rmgc_stock_log', entry)
        except: pass
        return jsonify({'product': p, 'entry': entry})

    data = load_data()
    for p in data['products']:
        if str(p['id']) == str(pid):
            old = float(p.get('stock', 0))
            if   mtype == 'delivery': p['stock'] = round(old + qty, 4)
            elif mtype == 'usage':    p['stock'] = round(max(0, old - qty), 4)
            elif mtype == 'adjust':   p['stock'] = round(qty, 4)
            entry = {'id': str(uuid.uuid4()), 'productId': pid, 'product': p['name'],
                     'type': mtype, 'qty': qty, 'before': old, 'after': p['stock'],
                     'unit': p.get('unit', ''), 'note': note,
                     'date': datetime.now().strftime('%d/%m/%Y %H:%M')}
            data['log'].insert(0, entry); data['log'] = data['log'][:500]
            save_data(data); return jsonify({'product': p, 'entry': entry})
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/log', methods=['GET'])
@login_required
def get_log(): return jsonify(get_stocklog_data())

@app.route('/api/summary', methods=['GET'])
@login_required
def get_summary():
    products = get_products_data()
    tv  = sum(float(p.get('packCost', 0)) * float(p.get('stock', 0)) for p in products)
    low = [p for p in products if 0 < float(p.get('stock', 0)) <= float(p.get('reorderLevel', 2))]
    out = [p for p in products if float(p.get('stock', 0)) == 0]
    cats = {}
    for p in products: c = p.get('category', 'Other'); cats[c] = cats.get(c, 0) + 1
    return jsonify({'totalProducts': len(products), 'totalValue': round(tv, 2),
                    'lowStock': len(low), 'outOfStock': len(out), 'byCategory': cats})

# ── SPRAY LOG ─────────────────────────────────────────────────────────────────
@app.route('/api/spraylog', methods=['GET'])
@login_required
def get_spraylog(): return jsonify(get_spraylog_data())

@app.route('/api/spraylog', methods=['POST'])
@login_required
def add_spray():
    entry = request.json; entry['id'] = str(uuid.uuid4())
    if USE_SUPABASE:
        return jsonify(sb_post('rmgc_spraylog', entry)), 201
    data = load_data(); data['sprayLog'].insert(0, entry); save_data(data)
    return jsonify(entry), 201

@app.route('/api/spraylog/<eid>', methods=['DELETE'])
@login_required
def del_spray(eid):
    if USE_SUPABASE:
        sb_delete('rmgc_spraylog', 'id', eid); return jsonify({'ok': True})
    data = load_data()
    data['sprayLog'] = [e for e in data['sprayLog'] if str(e['id']) != str(eid)]
    save_data(data); return jsonify({'ok': True})

# ── SDS ──────────────────────────────────────────────────────────────────────
def get_sds_data():
    if USE_SUPABASE:
        rows = sb_get('rmgc_sds', 'order=name.asc')
        return rows if isinstance(rows, list) else []
    return []

@app.route('/api/sds', methods=['GET'])
@login_required
def get_sds(): return jsonify(get_sds_data())

@app.route('/api/sds', methods=['POST'])
@login_required
def add_sds():
    entry = request.json; entry['id'] = str(uuid.uuid4())
    if USE_SUPABASE:
        return jsonify(sb_post('rmgc_sds', entry)), 201
    return jsonify(entry), 201

@app.route('/api/sds/<sid>', methods=['PUT'])
@login_required
def upd_sds(sid):
    body = request.json; body.pop('id', None)
    if USE_SUPABASE:
        sb_patch('rmgc_sds', 'id', sid, body)
        return jsonify({'id': sid, **body})
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/sds/<sid>', methods=['DELETE'])
@login_required
def del_sds(sid):
    if USE_SUPABASE:
        sb_delete('rmgc_sds', 'id', sid)
        return jsonify({'ok': True})
    return jsonify({'ok': True})

# ── DEBUG ─────────────────────────────────────────────────────────────────────
@app.route('/api/debug')
@login_required
def debug():
    return jsonify({'USE_SUPABASE': USE_SUPABASE,
                    'SUPABASE_URL_SET': bool(SUPABASE_URL),
                    'SUPABASE_KEY_SET': bool(SUPABASE_KEY)})

@app.errorhandler(500)
def internal_error(e):
    import traceback
    return f"<pre>500 Internal Server Error:\n{traceback.format_exc()}</pre>", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)
