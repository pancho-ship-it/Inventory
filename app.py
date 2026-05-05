
import os, sys, json, uuid, webbrowser, threading, requests
from datetime import datetime
from functools import wraps
from flask import Flask, jsonify, request, render_template, session, redirect, url_for

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── SUPABASE CONFIG ─────────────────────────────────────────────────────────
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
    url = f"{SUPABASE_URL}/rest/v1/{table}?{params}"
    r = requests.get(url, headers=sb_headers(), timeout=10)
    return r.json() if r.ok else []

def sb_post(table, data):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    r = requests.post(url, headers=sb_headers(), json=data, timeout=10)
    result = r.json()
    return result[0] if isinstance(result, list) and result else result

def sb_patch(table, match_col, match_val, data):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{match_col}=eq.{match_val}"
    r = requests.patch(url, headers=sb_headers(), json=data, timeout=10)
    return r.ok

def sb_delete(table, match_col, match_val):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{match_col}=eq.{match_val}"
    r = requests.delete(url, headers=sb_headers(), timeout=10)
    return r.ok

USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)

# Fallback file-based storage (used if Supabase not configured)
_tmp_data = '/tmp/rmgc_data.json'
_local_data = os.path.join(BASE_DIR, 'data.json')
DATA_FILE = _tmp_data if not os.access(BASE_DIR, os.W_OK) else _local_data


# Use Flask default templates/ folder next to app.py
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'rmgc-change-this-secret-2024')

# ── USER ACCOUNTS ─────────────────────────────────────────────────────────────
# To add/remove users, edit this dictionary: { 'username': 'password' }
USERS = {
    'admin':   'rmgc2024',
    'manager': 'golf2024',
    'staff':   'staff2024',
}

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

DEFAULT_PRODUCTS = [
  {"id":"1","name":"Grisu (Iprodione)","category":"Fungicide","activeIngredient":"Iprodione","unitSize":1.0,"unit":"L","packCost":41.5,"supplier":"Ortis","stock":0.5,"reorderLevel":2.0,"notes":""},
  {"id":"2","name":"Emerald Fungicide","category":"Fungicide","activeIngredient":"Boscalid 70% WG (FRAC 7 SDHI)","unitSize":1.0,"unit":"kg","packCost":25.0,"supplier":"Ortis","stock":1.0,"reorderLevel":2.0,"notes":""},
  {"id":"3","name":"Aliette WG","category":"Fungicide","activeIngredient":"Fosetyl-Aluminium 80%","unitSize":1.0,"unit":"kg","packCost":28.50,"supplier":"Ortis","stock":2.0,"reorderLevel":2.0,"notes":"FRAC P07 – Pythium prevention"},
  {"id":"4","name":"Previter","category":"Fungicide","activeIngredient":"Propiconazole 250 g/L","unitSize":1.0,"unit":"L","packCost":22.00,"supplier":"Ortis","stock":1.0,"reorderLevel":2.0,"notes":"FRAC 3 – DMI triazole"},
  {"id":"5","name":"Eagle 20EW","category":"Fungicide","activeIngredient":"Myclobutanil 20%","unitSize":1.0,"unit":"L","packCost":30.5,"supplier":"Ortis","stock":2.0,"reorderLevel":2.0,"notes":"FRAC 3 – DMI triazole"},
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
  {"id":"20","name":"Lepinox","category":"Insecticide","activeIngredient":"Bacillus thuringiensis","unitSize":2.0,"unit":"kg","packCost":29.92,"supplier":"Ortis","stock":1.0,"reorderLevel":2.0,"notes":"Biological – Poa annua larvae"},
  {"id":"21","name":"Mospilan 20 SG","category":"Insecticide","activeIngredient":"Acetamiprid 20%","unitSize":0.5,"unit":"kg","packCost":132.0,"supplier":"Ortis","stock":1.5,"reorderLevel":2.0,"notes":"IRAC 4A – Neonicotinoid"},
  {"id":"22","name":"Deltagri EC","category":"Insecticide","activeIngredient":"Deltamethrin 2.5%","unitSize":1.0,"unit":"L","packCost":30.0,"supplier":"Ortis","stock":2.0,"reorderLevel":2.0,"notes":"IRAC 3A – Pyrethroid. HIGH HAZARD near water"},
  {"id":"23","name":"Maintain PGR","category":"PGR","activeIngredient":"Trinexapac-ethyl 120 g/L","unitSize":5.0,"unit":"L","packCost":243.99,"supplier":"RT","stock":11.0,"reorderLevel":3.0,"notes":"Group 16 – gibberellin inhibitor"},
  {"id":"24","name":"Duraline Flush Thru","category":"Wetting Agent","activeIngredient":"Pipe cleaner / flush agent","unitSize":10.0,"unit":"L","packCost":20.0,"supplier":"RT","stock":1.0,"reorderLevel":1.0,"notes":""},
  {"id":"25","name":"Revolution Wetting Agent","category":"Wetting Agent","activeIngredient":"Proprietary polyether polymers","unitSize":10.0,"unit":"L","packCost":202.0,"supplier":"Rimesa","stock":0.0,"reorderLevel":5.0,"notes":"20 L/ha on greens Mar–Sep"},
  {"id":"26","name":"K 0-0-50 WS","category":"Fertiliser","activeIngredient":"Potassium sulphate 0-0-50","unitSize":25.0,"unit":"kg","packCost":10.0,"supplier":"Agius","stock":12.0,"reorderLevel":3.0,"notes":"Water soluble – foliar/fertigation"},
  {"id":"27","name":"Microlite TE","category":"Fertiliser","activeIngredient":"Trace elements blend","unitSize":20.0,"unit":"kg","packCost":44.71,"supplier":"RT","stock":5.0,"reorderLevel":2.0,"notes":"Foliar trace elements – greens"},
  {"id":"28","name":"Trimate (Amino+Fulvic)","category":"Fertiliser","activeIngredient":"L-form amino acids, Fulvic Acid","unitSize":5.0,"unit":"L","packCost":34.33,"supplier":"RT","stock":7.0,"reorderLevel":2.0,"notes":"Biostimulant – stress resistance"},
  {"id":"29","name":"Urea 46-0-0","category":"Fertiliser","activeIngredient":"Urea 46%N","unitSize":25.0,"unit":"kg","packCost":13.78,"supplier":"Ortis","stock":1.0,"reorderLevel":3.0,"notes":"150 kg/ha on fairways & rough"},
  {"id":"30","name":"12-12-17 Granular","category":"Fertiliser","activeIngredient":"NPK 12-12-17","unitSize":25.0,"unit":"kg","packCost":23.82,"supplier":"Ortis","stock":0.0,"reorderLevel":3.0,"notes":"150 kg/ha on tees & surrounds"},
  {"id":"31","name":"Calcium Nitrate","category":"Fertiliser","activeIngredient":"Calcium Nitrate 15.5% N","unitSize":25.0,"unit":"kg","packCost":18.50,"supplier":"Ortis","stock":0.0,"reorderLevel":2.0,"notes":""},
  {"id":"32","name":"Potassium Nitrate","category":"Fertiliser","activeIngredient":"Potassium Nitrate 13% N 46% K","unitSize":25.0,"unit":"kg","packCost":24.00,"supplier":"Ortis","stock":1.0,"reorderLevel":2.0,"notes":""},
  {"id":"33","name":"Magnesium Nitrate","category":"Fertiliser","activeIngredient":"Magnesium Nitrate 11% N 15% Mg","unitSize":25.0,"unit":"kg","packCost":21.50,"supplier":"Ortis","stock":1.0,"reorderLevel":2.0,"notes":""},
  {"id":"34","name":"Greenlawnger","category":"Colorant","activeIngredient":"Green pigment / colorant blend","unitSize":1.0,"unit":"L","packCost":23.35,"supplier":"AGV","stock":0.0,"reorderLevel":3.0,"notes":"5 L/ha on greens – winter colour"},
  {"id":"35","name":"Duraline Spray Paint Yellow","category":"Paint","activeIngredient":"Aerosol paint – yellow","unitSize":6.0,"unit":"cans","packCost":4.27,"supplier":"RT","stock":6.0,"reorderLevel":2.0,"notes":"Box of 6"},
  {"id":"36","name":"Duraline Spray Paint White","category":"Paint","activeIngredient":"Aerosol paint – white","unitSize":6.0,"unit":"cans","packCost":4.27,"supplier":"RT","stock":6.0,"reorderLevel":2.0,"notes":"Box of 6"},
  {"id":"37","name":"Duraline Spray Paint Red","category":"Paint","activeIngredient":"Aerosol paint – red","unitSize":6.0,"unit":"cans","packCost":4.27,"supplier":"RT","stock":3.0,"reorderLevel":2.0,"notes":"Box of 6"},
  {"id":"38","name":"Par Aide Blue","category":"Paint","activeIngredient":"Line marking paint – blue","unitSize":500.0,"unit":"gr","packCost":11.7,"supplier":"Duchell","stock":8.0,"reorderLevel":3.0,"notes":""},
  {"id":"39","name":"Par Aide Red","category":"Paint","activeIngredient":"Line marking paint – red","unitSize":500.0,"unit":"gr","packCost":11.7,"supplier":"Duchell","stock":15.0,"reorderLevel":3.0,"notes":""},
  {"id":"40","name":"Par Aide Yellow","category":"Paint","activeIngredient":"Line marking paint – yellow","unitSize":500.0,"unit":"gr","packCost":11.7,"supplier":"Duchell","stock":28.0,"reorderLevel":5.0,"notes":""},
  {"id":"41","name":"Par Aide White","category":"Paint","activeIngredient":"Line marking paint – white","unitSize":500.0,"unit":"gr","packCost":8.9,"supplier":"Duchell","stock":7.0,"reorderLevel":3.0,"notes":""},
  {"id":"42","name":"Par Aide Green","category":"Paint","activeIngredient":"Line marking paint – green","unitSize":500.0,"unit":"gr","packCost":11.7,"supplier":"Duchell","stock":6.0,"reorderLevel":3.0,"notes":""},
  {"id":"43","name":"Thunder Ryegrass","category":"Seeds","activeIngredient":"Perennial ryegrass blend","unitSize":22.7,"unit":"kg","packCost":70.14,"supplier":"Navarro M.","stock":0.0,"reorderLevel":1.0,"notes":"Tees overseeding Nov–Dec"},
  {"id":"44","name":"Bentgrass Tour Pro","category":"Seeds","activeIngredient":"Creeping bentgrass","unitSize":11.0,"unit":"kg","packCost":489.36,"supplier":"Navarro M.","stock":2.0,"reorderLevel":1.0,"notes":"Greens renovation"},
  {"id":"45","name":"Rugby Pitch Paint","category":"Seeds","activeIngredient":"White line marking paint","unitSize":5.0,"unit":"kg","packCost":16.0,"supplier":"Big Mat","stock":4.0,"reorderLevel":2.0,"notes":""}
]

DEFAULT_SURFACES = [
  {"id":"s1","name":"Greens","grass":"Creeping Bentgrass","count":"21 greens","mowingHeight":3.5,"areaSqm":10000},
  {"id":"s2","name":"Aprons & Surrounds","grass":"Kikuyu / Bermudagrass","count":"18 aprons+surrounds","mowingHeight":12,"areaSqm":20000},
  {"id":"s3","name":"Tees","grass":"Bermudagrass","count":"18 tees","mowingHeight":12,"areaSqm":10000},
  {"id":"s4","name":"Fairways","grass":"Kikuyu / Bermudagrass","count":"18 fairways","mowingHeight":12,"areaSqm":100000},
  {"id":"s5","name":"Rough","grass":"Kikuyu / Bermudagrass","count":"18 rough","mowingHeight":57,"areaSqm":120000}
]
# Total: 260,000 m² = 26 ha

DEFAULT_SPRAY_LOG = [
  {"id":"sl1","date":"05/01/2026","product":"Pendimethalin 33 EC","ai":"Pendimethalin 330 g/L","type":"Herbicide","zone":"Fairways","areaha":5,"rate":3.3,"total":16.5,"notes":"Pre-emergent weed control – Poa annua prevention"},
  {"id":"sl2","date":"06/02/2026","product":"Pendimethalin 33 EC","ai":"Pendimethalin 330 g/L","type":"Herbicide","zone":"Rough","areaha":5,"rate":3.3,"total":16.5,"notes":"Pre-emergent weed control – Poa annua prevention"},
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
  {"id":"sl13","date":"11/03/2026","product":"Dicopur Top + Cerlit","ai":"MCPA + Dicamba / Mecoprop-P","type":"Herbicide","zone":"Bunker faces","areaha":None,"rate":1,"total":None,"notes":"Post-emergence weed control + growth regulator"},
  {"id":"sl14","date":"12/03/2026","product":"Dicopur Top + Cerlit","ai":"MCPA + Dicamba / Mecoprop-P","type":"Herbicide","zone":"Bunker faces","areaha":None,"rate":1,"total":None,"notes":"Post-emergence weed control + growth regulator"},
  {"id":"sl15","date":"12/03/2026","product":"Mospilan 20 SG","ai":"Acetamiprid 20%","type":"Insecticide","zone":"Palm trees","areaha":None,"rate":None,"total":None,"notes":"Red weevil control"},
  {"id":"sl16","date":"16/03/2026","product":"Emerald Fungicide","ai":"Boscalid 70% WG","type":"Fungicide","zone":"Fairways","areaha":2,"rate":1,"total":2,"notes":"Post-emergence fungicide"},
  {"id":"sl17","date":"17/03/2026","product":"Emerald Fungicide","ai":"Boscalid 70% WG","type":"Fungicide","zone":"Fairways","areaha":2,"rate":1,"total":2,"notes":"Post-emergence fungicide"},
  {"id":"sl18","date":"18/03/2026","product":"Stomp","ai":"Pendimethalin 330 g/L","type":"Herbicide","zone":"Greens","areaha":1,"rate":1,"total":1,"notes":"Pre-emergent weed control – Poa annua prevention"}
]

DEFAULT_HIST = {
  "2022":{"note":"Programme year 1: Baseline. Custodia (FRAC 3+11) spring/summer. Emphasis on pre-emergent weed control.","entries":[
    {"id":"2022-1","num":1,"date":"07/02/2022","product":"Pendimethalin 33 EC","ai":"Pendimethalin 330 g/L","type":"Herbicide","zone":"Fairways","area":"10","rate":"3.3 L","total":"33 L","notes":"Pre-emergent weed control"},
    {"id":"2022-2","num":2,"date":"07/02/2022","product":"Pendimethalin 33 EC","ai":"Pendimethalin 330 g/L","type":"Herbicide","zone":"Rough","area":"10","rate":"3.3 L","total":"33 L","notes":"Pre-emergent weed control"},
    {"id":"2022-3","num":3,"date":"10/02/2022","product":"Pendimethalin 33 EC","ai":"Pendimethalin 330 g/L","type":"Herbicide","zone":"Tees","area":"1","rate":"3.3 L","total":"3.3 L","notes":"Pre-emergent weed control"},
    {"id":"2022-4","num":4,"date":"14/03/2022","product":"Custodia","ai":"Azoxystrobin 120 g/L + Tebuconazole 200 g/L","type":"Fungicide","zone":"Greens","area":"1","rate":"0.75 L","total":"0.75 L","notes":"Preventative – dollar spot & brown patch"},
    {"id":"2022-5","num":5,"date":"14/03/2022","product":"Custodia","ai":"Azoxystrobin 120 g/L + Tebuconazole 200 g/L","type":"Fungicide","zone":"Tees","area":"1","rate":"0.75 L","total":"0.75 L","notes":"Preventative – dollar spot & brown patch"},
    {"id":"2022-6","num":6,"date":"07/04/2022","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Tees","area":"1","rate":"1 + 0.5 L","total":"1 + 0.5 L","notes":"Post-emergent broadleaf weed control"},
    {"id":"2022-7","num":7,"date":"08/04/2022","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Fairways","area":"10","rate":"1 + 0.5 L","total":"10 + 5 L","notes":"Post-emergent broadleaf weed control"},
    {"id":"2022-8","num":8,"date":"11/04/2022","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Rough","area":"10","rate":"1 + 0.5 L","total":"10 + 5 L","notes":"Rough threshold exceeded"},
    {"id":"2022-9","num":9,"date":"05/05/2022","product":"Revolution","ai":"Wetting agent blend","type":"Wetting Agent","zone":"Greens","area":"1","rate":"20 L","total":"20 L","notes":"Pre-summer heat stress management"},
    {"id":"2022-10","num":10,"date":"12/05/2022","product":"Emerald","ai":"Boscalid 70% WG","type":"Fungicide","zone":"Greens","area":"1","rate":"0.8 kg","total":"0.8 kg","notes":"Preventative anthracnose & dollar spot"},
    {"id":"2022-11","num":11,"date":"12/05/2022","product":"Emerald","ai":"Boscalid 70% WG","type":"Fungicide","zone":"Tees","area":"1","rate":"0.8 kg","total":"0.8 kg","notes":"Preventative anthracnose & dollar spot"},
    {"id":"2022-12","num":12,"date":"19/05/2022","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Greens","area":"1","rate":"4 kg","total":"4 kg","notes":"Pythium prevention"},
    {"id":"2022-13","num":13,"date":"19/05/2022","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Tees","area":"1","rate":"4 kg","total":"4 kg","notes":"Pythium prevention"},
    {"id":"2022-14","num":14,"date":"26/05/2022","product":"Mospilan","ai":"Acetamiprid 20%","type":"Insecticide","zone":"Greens","area":"1","rate":"250 g","total":"250 g","notes":"Aphid & leatherjacket threshold exceeded"},
    {"id":"2022-15","num":15,"date":"26/05/2022","product":"Mospilan","ai":"Acetamiprid 20%","type":"Insecticide","zone":"Tees","area":"1","rate":"250 g","total":"250 g","notes":"Aphid & leatherjacket threshold exceeded"},
    {"id":"2022-16","num":16,"date":"02/06/2022","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2022-17","num":17,"date":"09/06/2022","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Rough","area":"10","rate":"1.2 L","total":"12 L","notes":"Summer rough management"},
    {"id":"2022-18","num":18,"date":"16/06/2022","product":"Custodia","ai":"Azoxystrobin 120 g/L + Tebuconazole 200 g/L","type":"Fungicide","zone":"Greens","area":"1","rate":"0.75 L","total":"0.75 L","notes":"Brown patch prevention"},
    {"id":"2022-19","num":19,"date":"16/06/2022","product":"Custodia","ai":"Azoxystrobin 120 g/L + Tebuconazole 200 g/L","type":"Fungicide","zone":"Tees","area":"1","rate":"0.75 L","total":"0.75 L","notes":"Brown patch prevention"},
    {"id":"2022-20","num":20,"date":"23/06/2022","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2022-21","num":21,"date":"27/06/2022","product":"Deltagri","ai":"Deltamethrin 2.5%","type":"Insecticide","zone":"Greens","area":"1","rate":"1 L","total":"1 L","notes":"Chafer beetle / cutworm"},
    {"id":"2022-22","num":22,"date":"27/06/2022","product":"Deltagri","ai":"Deltamethrin 2.5%","type":"Insecticide","zone":"Tees","area":"1","rate":"1 L","total":"1 L","notes":"Chafer beetle / cutworm"},
    {"id":"2022-23","num":23,"date":"28/06/2022","product":"Deltagri","ai":"Deltamethrin 2.5%","type":"Insecticide","zone":"Fairways","area":"10","rate":"1 L","total":"10 L","notes":"Chafer beetle – fairway outbreak"},
    {"id":"2022-24","num":24,"date":"29/06/2022","product":"Deltagri","ai":"Deltamethrin 2.5%","type":"Insecticide","zone":"Rough","area":"10","rate":"1 L","total":"10 L","notes":"Chafer beetle – buffer zone"},
    {"id":"2022-25","num":25,"date":"30/06/2022","product":"Revolution","ai":"Wetting agent blend","type":"Wetting Agent","zone":"Greens","area":"1","rate":"20 L","total":"20 L","notes":"Monthly wetting agent"},
    {"id":"2022-26","num":26,"date":"04/07/2022","product":"Junction","ai":"Mancozeb + Copper Hydroxide","type":"Fungicide","zone":"Greens","area":"1","rate":"5 kg","total":"5 kg","notes":"Multi-site contact fungicide"},
    {"id":"2022-27","num":27,"date":"04/07/2022","product":"Junction","ai":"Mancozeb + Copper Hydroxide","type":"Fungicide","zone":"Tees","area":"1","rate":"5 kg","total":"5 kg","notes":"Multi-site contact fungicide"},
    {"id":"2022-28","num":28,"date":"07/07/2022","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Rough","area":"10","rate":"1.2 L","total":"12 L","notes":"Summer rough management"},
    {"id":"2022-29","num":29,"date":"14/07/2022","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2022-30","num":30,"date":"21/07/2022","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Greens","area":"1","rate":"4 kg","total":"4 kg","notes":"Pythium root rot prevention"},
    {"id":"2022-31","num":31,"date":"21/07/2022","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Tees","area":"1","rate":"4 kg","total":"4 kg","notes":"Pythium root rot prevention"},
    {"id":"2022-32","num":32,"date":"03/08/2022","product":"Revolution","ai":"Wetting agent blend","type":"Wetting Agent","zone":"Greens","area":"1","rate":"20 L","total":"20 L","notes":"Monthly wetting agent"},
    {"id":"2022-33","num":33,"date":"04/08/2022","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2022-34","num":34,"date":"04/08/2022","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Rough","area":"10","rate":"1.2 L","total":"12 L","notes":"Summer rough management"},
    {"id":"2022-35","num":35,"date":"08/08/2022","product":"Eagle","ai":"Myclobutanil 20%","type":"Fungicide","zone":"Greens","area":"1","rate":"1 L","total":"1 L","notes":"DMI follow-up – dollar spot"},
    {"id":"2022-36","num":36,"date":"08/08/2022","product":"Eagle","ai":"Myclobutanil 20%","type":"Fungicide","zone":"Tees","area":"1","rate":"1 L","total":"1 L","notes":"DMI follow-up – dollar spot"},
    {"id":"2022-37","num":37,"date":"25/08/2022","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2022-38","num":38,"date":"01/09/2022","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Rough","area":"10","rate":"1.2 L","total":"12 L","notes":"Summer rough management"},
    {"id":"2022-39","num":39,"date":"01/09/2022","product":"Revolution","ai":"Wetting agent blend","type":"Wetting Agent","zone":"Greens","area":"1","rate":"20 L","total":"20 L","notes":"Late summer wetting agent"},
    {"id":"2022-40","num":40,"date":"14/09/2022","product":"Mospilan","ai":"Acetamiprid 20%","type":"Insecticide","zone":"Fairways","area":"10","rate":"250 g","total":"2.5 kg","notes":"Aphid population threshold exceeded"},
    {"id":"2022-41","num":41,"date":"15/09/2022","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2022-42","num":42,"date":"15/09/2022","product":"Mospilan","ai":"Acetamiprid 20%","type":"Insecticide","zone":"Rough","area":"10","rate":"250 g","total":"2.5 kg","notes":"Aphid control buffer zone"},
    {"id":"2022-43","num":43,"date":"22/09/2022","product":"Custodia","ai":"Azoxystrobin 120 g/L + Tebuconazole 200 g/L","type":"Fungicide","zone":"Greens","area":"1","rate":"0.75 L","total":"0.75 L","notes":"Autumn disease protection"},
    {"id":"2022-44","num":44,"date":"22/09/2022","product":"Custodia","ai":"Azoxystrobin 120 g/L + Tebuconazole 200 g/L","type":"Fungicide","zone":"Tees","area":"1","rate":"0.75 L","total":"0.75 L","notes":"Autumn disease protection"},
    {"id":"2022-45","num":45,"date":"12/10/2022","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Greens","area":"1","rate":"4 kg","total":"4 kg","notes":"Autumn Pythium protection"},
    {"id":"2022-46","num":46,"date":"12/10/2022","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Tees","area":"1","rate":"4 kg","total":"4 kg","notes":"Autumn Pythium protection"},
    {"id":"2022-47","num":47,"date":"20/10/2022","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Tees","area":"1","rate":"1 + 0.5 L","total":"1 + 0.5 L","notes":"Autumn broadleaf flush"},
    {"id":"2022-48","num":48,"date":"21/10/2022","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Fairways","area":"10","rate":"1 + 0.5 L","total":"10 + 5 L","notes":"Autumn broadleaf flush"},
    {"id":"2022-49","num":49,"date":"10/11/2022","product":"Kerb Flo","ai":"Propyzamide 400 g/L","type":"Herbicide","zone":"Tees","area":"1","rate":"2.5 L","total":"2.5 L","notes":"Annual meadow grass pre-emergent"},
    {"id":"2022-50","num":50,"date":"11/11/2022","product":"Kerb Flo","ai":"Propyzamide 400 g/L","type":"Herbicide","zone":"Fairways","area":"10","rate":"2.5 L","total":"25 L","notes":"Annual meadow grass pre-emergent"},
    {"id":"2022-51","num":51,"date":"14/11/2022","product":"Kerb Flo","ai":"Propyzamide 400 g/L","type":"Herbicide","zone":"Rough","area":"10","rate":"2.5 L","total":"25 L","notes":"Annual meadow grass pre-emergent"},
    {"id":"2022-52","num":52,"date":"08/12/2022","product":"Greenlawnger","ai":"Green pigment colorant","type":"Colorant","zone":"Greens","area":"1","rate":"5 L","total":"5 L","notes":"Winter aesthetics"}
  ]},
  "2023":{"note":"Programme year 2: Junction replaces Custodia spring. Eagle (FRAC 3) DMI. Reduced insecticide – IPM threshold not reached.","entries":[
    {"id":"2023-1","num":1,"date":"27/01/2023","product":"Pendimethalin 33 EC","ai":"Pendimethalin 330 g/L","type":"Herbicide","zone":"Tees","area":"1","rate":"3.3 L","total":"3.3 L","notes":"Pre-emergent"},
    {"id":"2023-2","num":2,"date":"03/02/2023","product":"Pendimethalin 33 EC","ai":"Pendimethalin 330 g/L","type":"Herbicide","zone":"Fairways","area":"10","rate":"3.3 L","total":"33 L","notes":"Pre-emergent"},
    {"id":"2023-3","num":3,"date":"06/02/2023","product":"Pendimethalin 33 EC","ai":"Pendimethalin 330 g/L","type":"Herbicide","zone":"Rough","area":"10","rate":"3.3 L","total":"33 L","notes":"Pre-emergent"},
    {"id":"2023-4","num":4,"date":"13/03/2023","product":"Junction","ai":"Mancozeb + Copper Hydroxide","type":"Fungicide","zone":"Greens","area":"1","rate":"5 kg","total":"5 kg","notes":"Contact fungicide rotation"},
    {"id":"2023-5","num":5,"date":"13/03/2023","product":"Junction","ai":"Mancozeb + Copper Hydroxide","type":"Fungicide","zone":"Tees","area":"1","rate":"5 kg","total":"5 kg","notes":"Contact fungicide rotation"},
    {"id":"2023-6","num":6,"date":"10/04/2023","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Tees","area":"1","rate":"1 + 0.5 L","total":"1 + 0.5 L","notes":"Post-emergent broadleaf"},
    {"id":"2023-7","num":7,"date":"10/04/2023","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Fairways","area":"10","rate":"1 + 0.5 L","total":"10 + 5 L","notes":"Post-emergent broadleaf"},
    {"id":"2023-8","num":8,"date":"24/04/2023","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Greens","area":"1","rate":"4 kg","total":"4 kg","notes":"Pythium prevention – wet spring"},
    {"id":"2023-9","num":9,"date":"24/04/2023","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Tees","area":"1","rate":"4 kg","total":"4 kg","notes":"Pythium prevention – wet spring"},
    {"id":"2023-10","num":10,"date":"05/05/2023","product":"Revolution","ai":"Wetting agent blend","type":"Wetting Agent","zone":"Greens","area":"1","rate":"20 L","total":"20 L","notes":"Pre-summer heat stress"},
    {"id":"2023-11","num":11,"date":"15/05/2023","product":"Eagle","ai":"Myclobutanil 20%","type":"Fungicide","zone":"Greens","area":"1","rate":"1 L","total":"1 L","notes":"DMI rotation"},
    {"id":"2023-12","num":12,"date":"15/05/2023","product":"Eagle","ai":"Myclobutanil 20%","type":"Fungicide","zone":"Tees","area":"1","rate":"1 L","total":"1 L","notes":"DMI rotation"},
    {"id":"2023-13","num":13,"date":"26/05/2023","product":"Mospilan","ai":"Acetamiprid 20%","type":"Insecticide","zone":"Greens","area":"1","rate":"250 g","total":"250 g","notes":"Aphid & leatherjacket"},
    {"id":"2023-14","num":14,"date":"26/05/2023","product":"Mospilan","ai":"Acetamiprid 20%","type":"Insecticide","zone":"Tees","area":"1","rate":"250 g","total":"250 g","notes":"Aphid & leatherjacket"},
    {"id":"2023-15","num":15,"date":"02/06/2023","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2023-16","num":16,"date":"09/06/2023","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Rough","area":"10","rate":"1.2 L","total":"12 L","notes":"Summer rough management"},
    {"id":"2023-17","num":17,"date":"16/06/2023","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Tees","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Extended PGR to tees"},
    {"id":"2023-18","num":18,"date":"16/06/2023","product":"Custodia","ai":"Azoxystrobin 120 g/L + Tebuconazole 200 g/L","type":"Fungicide","zone":"Greens","area":"1","rate":"0.75 L","total":"0.75 L","notes":"Brown patch prevention"},
    {"id":"2023-19","num":19,"date":"16/06/2023","product":"Custodia","ai":"Azoxystrobin 120 g/L + Tebuconazole 200 g/L","type":"Fungicide","zone":"Tees","area":"1","rate":"0.75 L","total":"0.75 L","notes":"Brown patch prevention"},
    {"id":"2023-20","num":20,"date":"23/06/2023","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2023-21","num":21,"date":"30/06/2023","product":"Revolution","ai":"Wetting agent blend","type":"Wetting Agent","zone":"Greens","area":"1","rate":"20 L","total":"20 L","notes":"Monthly wetting agent"},
    {"id":"2023-22","num":22,"date":"03/07/2023","product":"Deltagri","ai":"Deltamethrin 2.5%","type":"Insecticide","zone":"Greens","area":"1","rate":"1 L","total":"1 L","notes":"Low-level chafer activity"},
    {"id":"2023-23","num":23,"date":"03/07/2023","product":"Deltagri","ai":"Deltamethrin 2.5%","type":"Insecticide","zone":"Tees","area":"1","rate":"1 L","total":"1 L","notes":"Low-level chafer activity"},
    {"id":"2023-24","num":24,"date":"07/07/2023","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Rough","area":"10","rate":"1.2 L","total":"12 L","notes":"Summer rough management"},
    {"id":"2023-25","num":25,"date":"14/07/2023","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2023-26","num":26,"date":"14/07/2023","product":"Emerald","ai":"Boscalid 70% WG","type":"Fungicide","zone":"Greens","area":"1","rate":"0.8 kg","total":"0.8 kg","notes":"SDHI mid-season"},
    {"id":"2023-27","num":27,"date":"14/07/2023","product":"Emerald","ai":"Boscalid 70% WG","type":"Fungicide","zone":"Tees","area":"1","rate":"0.8 kg","total":"0.8 kg","notes":"SDHI mid-season"},
    {"id":"2023-28","num":28,"date":"21/07/2023","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Tees","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Extended PGR to tees"},
    {"id":"2023-29","num":29,"date":"21/07/2023","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Greens","area":"1","rate":"4 kg","total":"4 kg","notes":"Pythium prevention"},
    {"id":"2023-30","num":30,"date":"21/07/2023","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Tees","area":"1","rate":"4 kg","total":"4 kg","notes":"Pythium prevention"},
    {"id":"2023-31","num":31,"date":"03/08/2023","product":"Revolution","ai":"Wetting agent blend","type":"Wetting Agent","zone":"Greens","area":"1","rate":"20 L","total":"20 L","notes":"Monthly wetting agent"},
    {"id":"2023-32","num":32,"date":"04/08/2023","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2023-33","num":33,"date":"04/08/2023","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Rough","area":"10","rate":"1.2 L","total":"12 L","notes":"Summer rough management"},
    {"id":"2023-34","num":34,"date":"25/08/2023","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2023-35","num":35,"date":"01/09/2023","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Rough","area":"10","rate":"1.2 L","total":"12 L","notes":"Summer rough management"},
    {"id":"2023-36","num":36,"date":"01/09/2023","product":"Revolution","ai":"Wetting agent blend","type":"Wetting Agent","zone":"Greens","area":"1","rate":"20 L","total":"20 L","notes":"Late summer wetting agent"},
    {"id":"2023-37","num":37,"date":"15/09/2023","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2023-38","num":38,"date":"09/10/2023","product":"Eagle","ai":"Myclobutanil 20%","type":"Fungicide","zone":"Greens","area":"1","rate":"1 L","total":"1 L","notes":"DMI autumn"},
    {"id":"2023-39","num":39,"date":"09/10/2023","product":"Eagle","ai":"Myclobutanil 20%","type":"Fungicide","zone":"Tees","area":"1","rate":"1 L","total":"1 L","notes":"DMI autumn"},
    {"id":"2023-40","num":40,"date":"12/10/2023","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Greens","area":"1","rate":"4 kg","total":"4 kg","notes":"Autumn Pythium"},
    {"id":"2023-41","num":41,"date":"12/10/2023","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Tees","area":"1","rate":"4 kg","total":"4 kg","notes":"Autumn Pythium"},
    {"id":"2023-42","num":42,"date":"20/10/2023","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Tees","area":"1","rate":"1 + 0.5 L","total":"1 + 0.5 L","notes":"Autumn broadleaf flush"},
    {"id":"2023-43","num":43,"date":"23/10/2023","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Fairways","area":"10","rate":"1 + 0.5 L","total":"10 + 5 L","notes":"Autumn broadleaf flush"},
    {"id":"2023-44","num":44,"date":"23/10/2023","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Rough","area":"10","rate":"1 + 0.5 L","total":"10 + 5 L","notes":"Autumn broadleaf flush"},
    {"id":"2023-45","num":45,"date":"03/11/2023","product":"Deltagri","ai":"Deltamethrin 2.5%","type":"Insecticide","zone":"Greens","area":"1","rate":"1 L","total":"1 L","notes":"Autumn cutworm / armyworm"},
    {"id":"2023-46","num":46,"date":"03/11/2023","product":"Deltagri","ai":"Deltamethrin 2.5%","type":"Insecticide","zone":"Tees","area":"1","rate":"1 L","total":"1 L","notes":"Autumn cutworm / armyworm"},
    {"id":"2023-47","num":47,"date":"10/11/2023","product":"Kerb Flo","ai":"Propyzamide 400 g/L","type":"Herbicide","zone":"Tees","area":"1","rate":"2.5 L","total":"2.5 L","notes":"Pre-emergent Poa annua"},
    {"id":"2023-48","num":48,"date":"13/11/2023","product":"Kerb Flo","ai":"Propyzamide 400 g/L","type":"Herbicide","zone":"Fairways","area":"10","rate":"2.5 L","total":"25 L","notes":"Pre-emergent Poa annua"},
    {"id":"2023-49","num":49,"date":"08/12/2023","product":"Greenlawnger","ai":"Green pigment colorant","type":"Colorant","zone":"Greens","area":"1","rate":"5 L","total":"5 L","notes":"Winter aesthetics"}
  ]},
  "2024":{"note":"Programme year 3: Custodia spring / Emerald summer rotation. Pythium risk higher – Aliette brought forward to April.","entries":[
    {"id":"2024-1","num":1,"date":"05/02/2024","product":"Pendimethalin 33 EC","ai":"Pendimethalin 330 g/L","type":"Herbicide","zone":"Fairways","area":"10","rate":"3.3 L","total":"33 L","notes":"Pre-emergent"},
    {"id":"2024-2","num":2,"date":"06/02/2024","product":"Pendimethalin 33 EC","ai":"Pendimethalin 330 g/L","type":"Herbicide","zone":"Rough","area":"10","rate":"3.3 L","total":"33 L","notes":"Pre-emergent"},
    {"id":"2024-3","num":3,"date":"12/02/2024","product":"Pendimethalin 33 EC","ai":"Pendimethalin 330 g/L","type":"Herbicide","zone":"Tees","area":"1","rate":"3.3 L","total":"3.3 L","notes":"Pre-emergent"},
    {"id":"2024-4","num":4,"date":"14/03/2024","product":"Custodia","ai":"Azoxystrobin 120 g/L + Tebuconazole 200 g/L","type":"Fungicide","zone":"Greens","area":"1","rate":"0.75 L","total":"0.75 L","notes":"Spring preventative"},
    {"id":"2024-5","num":5,"date":"14/03/2024","product":"Custodia","ai":"Azoxystrobin 120 g/L + Tebuconazole 200 g/L","type":"Fungicide","zone":"Tees","area":"1","rate":"0.75 L","total":"0.75 L","notes":"Spring preventative"},
    {"id":"2024-6","num":6,"date":"08/04/2024","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Tees","area":"1","rate":"1 + 0.5 L","total":"1 + 0.5 L","notes":"Post-emergent broadleaf"},
    {"id":"2024-7","num":7,"date":"08/04/2024","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Fairways","area":"10","rate":"1 + 0.5 L","total":"10 + 5 L","notes":"Post-emergent broadleaf"},
    {"id":"2024-8","num":8,"date":"08/04/2024","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Rough","area":"10","rate":"1 + 0.5 L","total":"10 + 5 L","notes":"Post-emergent broadleaf"},
    {"id":"2024-9","num":9,"date":"06/05/2024","product":"Revolution","ai":"Wetting agent blend","type":"Wetting Agent","zone":"Greens","area":"1","rate":"20 L","total":"20 L","notes":"Pre-summer heat stress"},
    {"id":"2024-10","num":10,"date":"13/05/2024","product":"Emerald","ai":"Boscalid 70% WG","type":"Fungicide","zone":"Greens","area":"1","rate":"0.8 kg","total":"0.8 kg","notes":"Preventative anthracnose"},
    {"id":"2024-11","num":11,"date":"13/05/2024","product":"Emerald","ai":"Boscalid 70% WG","type":"Fungicide","zone":"Tees","area":"1","rate":"0.8 kg","total":"0.8 kg","notes":"Preventative anthracnose"},
    {"id":"2024-12","num":12,"date":"20/05/2024","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Greens","area":"1","rate":"4 kg","total":"4 kg","notes":"Pythium prevention"},
    {"id":"2024-13","num":13,"date":"20/05/2024","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Tees","area":"1","rate":"4 kg","total":"4 kg","notes":"Pythium prevention"},
    {"id":"2024-14","num":14,"date":"03/06/2024","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2024-15","num":15,"date":"10/06/2024","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Rough","area":"10","rate":"1.2 L","total":"12 L","notes":"Summer rough management"},
    {"id":"2024-16","num":16,"date":"17/06/2024","product":"Emerald","ai":"Boscalid 70% WG","type":"Fungicide","zone":"Greens","area":"1","rate":"0.8 kg","total":"0.8 kg","notes":"SDHI rotation"},
    {"id":"2024-17","num":17,"date":"17/06/2024","product":"Emerald","ai":"Boscalid 70% WG","type":"Fungicide","zone":"Tees","area":"1","rate":"0.8 kg","total":"0.8 kg","notes":"SDHI rotation"},
    {"id":"2024-18","num":18,"date":"24/06/2024","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2024-19","num":19,"date":"27/06/2024","product":"Deltagri","ai":"Deltamethrin 2.5%","type":"Insecticide","zone":"Greens","area":"1","rate":"1 L","total":"1 L","notes":"Chafer beetle"},
    {"id":"2024-20","num":20,"date":"27/06/2024","product":"Deltagri","ai":"Deltamethrin 2.5%","type":"Insecticide","zone":"Tees","area":"1","rate":"1 L","total":"1 L","notes":"Chafer beetle"},
    {"id":"2024-21","num":21,"date":"28/06/2024","product":"Deltagri","ai":"Deltamethrin 2.5%","type":"Insecticide","zone":"Fairways","area":"10","rate":"1 L","total":"10 L","notes":"Chafer beetle"},
    {"id":"2024-22","num":22,"date":"01/07/2024","product":"Revolution","ai":"Wetting agent blend","type":"Wetting Agent","zone":"Greens","area":"1","rate":"20 L","total":"20 L","notes":"Monthly wetting agent"},
    {"id":"2024-23","num":23,"date":"01/07/2024","product":"Deltagri","ai":"Deltamethrin 2.5%","type":"Insecticide","zone":"Rough","area":"10","rate":"1 L","total":"10 L","notes":"Chafer beetle buffer zone"},
    {"id":"2024-24","num":24,"date":"08/07/2024","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Rough","area":"10","rate":"1.2 L","total":"12 L","notes":"Summer rough management"},
    {"id":"2024-25","num":25,"date":"15/07/2024","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2024-26","num":26,"date":"15/07/2024","product":"Emerald","ai":"Boscalid 70% WG","type":"Fungicide","zone":"Greens","area":"1","rate":"0.8 kg","total":"0.8 kg","notes":"SDHI mid-season"},
    {"id":"2024-27","num":27,"date":"15/07/2024","product":"Emerald","ai":"Boscalid 70% WG","type":"Fungicide","zone":"Tees","area":"1","rate":"0.8 kg","total":"0.8 kg","notes":"SDHI mid-season"},
    {"id":"2024-28","num":28,"date":"22/07/2024","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Greens","area":"1","rate":"4 kg","total":"4 kg","notes":"Peak summer Pythium"},
    {"id":"2024-29","num":29,"date":"22/07/2024","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Tees","area":"1","rate":"4 kg","total":"4 kg","notes":"Peak summer Pythium"},
    {"id":"2024-30","num":30,"date":"05/08/2024","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2024-31","num":31,"date":"05/08/2024","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Rough","area":"10","rate":"1.2 L","total":"12 L","notes":"Summer rough management"},
    {"id":"2024-32","num":32,"date":"05/08/2024","product":"Revolution","ai":"Wetting agent blend","type":"Wetting Agent","zone":"Greens","area":"1","rate":"20 L","total":"20 L","notes":"Peak summer dry patch"},
    {"id":"2024-33","num":33,"date":"26/08/2024","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2024-34","num":34,"date":"02/09/2024","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Rough","area":"10","rate":"1.2 L","total":"12 L","notes":"Summer rough management"},
    {"id":"2024-35","num":35,"date":"02/09/2024","product":"Revolution","ai":"Wetting agent blend","type":"Wetting Agent","zone":"Greens","area":"1","rate":"20 L","total":"20 L","notes":"Late summer wetting agent"},
    {"id":"2024-36","num":36,"date":"16/09/2024","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2024-37","num":37,"date":"16/09/2024","product":"Mospilan","ai":"Acetamiprid 20%","type":"Insecticide","zone":"Fairways","area":"10","rate":"250 g","total":"2.5 kg","notes":"Aphid population threshold"},
    {"id":"2024-38","num":38,"date":"16/09/2024","product":"Mospilan","ai":"Acetamiprid 20%","type":"Insecticide","zone":"Rough","area":"10","rate":"250 g","total":"2.5 kg","notes":"Aphid control buffer zone"},
    {"id":"2024-39","num":39,"date":"07/10/2024","product":"Eagle","ai":"Myclobutanil 20%","type":"Fungicide","zone":"Greens","area":"1","rate":"1 L","total":"1 L","notes":"DMI autumn"},
    {"id":"2024-40","num":40,"date":"07/10/2024","product":"Eagle","ai":"Myclobutanil 20%","type":"Fungicide","zone":"Tees","area":"1","rate":"1 L","total":"1 L","notes":"DMI autumn"},
    {"id":"2024-41","num":41,"date":"14/10/2024","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Greens","area":"1","rate":"4 kg","total":"4 kg","notes":"Autumn Pythium"},
    {"id":"2024-42","num":42,"date":"14/10/2024","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Tees","area":"1","rate":"4 kg","total":"4 kg","notes":"Autumn Pythium"},
    {"id":"2024-43","num":43,"date":"21/10/2024","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Tees","area":"1","rate":"1 + 0.5 L","total":"1 + 0.5 L","notes":"Autumn broadleaf flush"},
    {"id":"2024-44","num":44,"date":"21/10/2024","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Fairways","area":"10","rate":"1 + 0.5 L","total":"10 + 5 L","notes":"Autumn broadleaf flush"},
    {"id":"2024-45","num":45,"date":"11/11/2024","product":"Kerb Flo","ai":"Propyzamide 400 g/L","type":"Herbicide","zone":"Tees","area":"1","rate":"2.5 L","total":"2.5 L","notes":"Pre-emergent Poa annua"},
    {"id":"2024-46","num":46,"date":"11/11/2024","product":"Kerb Flo","ai":"Propyzamide 400 g/L","type":"Herbicide","zone":"Fairways","area":"10","rate":"2.5 L","total":"25 L","notes":"Pre-emergent Poa annua"},
    {"id":"2024-47","num":47,"date":"12/11/2024","product":"Kerb Flo","ai":"Propyzamide 400 g/L","type":"Herbicide","zone":"Rough","area":"10","rate":"2.5 L","total":"25 L","notes":"Pre-emergent Poa annua"},
    {"id":"2024-48","num":48,"date":"09/12/2024","product":"Greenlawnger","ai":"Green pigment colorant","type":"Colorant","zone":"Greens","area":"1","rate":"5 L","total":"5 L","notes":"Winter aesthetics"}
  ]},
  "2025":{"note":"Programme year 4: Eagle spring DMI. Aliette pre-emptive April. Extended PGR to Tees. Two Deltagri – elevated cutworm pressure.","entries":[
    {"id":"2025-1","num":1,"date":"27/01/2025","product":"Pendimethalin 33 EC","ai":"Pendimethalin 330 g/L","type":"Herbicide","zone":"Tees","area":"1","rate":"3.3 L","total":"3.3 L","notes":"Pre-emergent"},
    {"id":"2025-2","num":2,"date":"03/02/2025","product":"Pendimethalin 33 EC","ai":"Pendimethalin 330 g/L","type":"Herbicide","zone":"Fairways","area":"10","rate":"3.3 L","total":"33 L","notes":"Pre-emergent"},
    {"id":"2025-3","num":3,"date":"04/02/2025","product":"Pendimethalin 33 EC","ai":"Pendimethalin 330 g/L","type":"Herbicide","zone":"Rough","area":"10","rate":"3.3 L","total":"33 L","notes":"Pre-emergent"},
    {"id":"2025-4","num":4,"date":"11/03/2025","product":"Junction","ai":"Mancozeb + Copper Hydroxide","type":"Fungicide","zone":"Greens","area":"1","rate":"5 kg","total":"5 kg","notes":"Contact fungicide rotation"},
    {"id":"2025-5","num":5,"date":"11/03/2025","product":"Junction","ai":"Mancozeb + Copper Hydroxide","type":"Fungicide","zone":"Tees","area":"1","rate":"5 kg","total":"5 kg","notes":"Contact fungicide rotation"},
    {"id":"2025-6","num":6,"date":"10/04/2025","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Tees","area":"1","rate":"1 + 0.5 L","total":"1 + 0.5 L","notes":"Post-emergent broadleaf"},
    {"id":"2025-7","num":7,"date":"11/04/2025","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Fairways","area":"10","rate":"1 + 0.5 L","total":"10 + 5 L","notes":"Post-emergent broadleaf"},
    {"id":"2025-8","num":8,"date":"14/04/2025","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Rough","area":"10","rate":"1 + 0.5 L","total":"10 + 5 L","notes":"Post-emergent broadleaf"},
    {"id":"2025-9","num":9,"date":"22/04/2025","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Greens","area":"1","rate":"4 kg","total":"4 kg","notes":"Pre-emptive Pythium – wet spring"},
    {"id":"2025-10","num":10,"date":"22/04/2025","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Tees","area":"1","rate":"4 kg","total":"4 kg","notes":"Pre-emptive Pythium"},
    {"id":"2025-11","num":11,"date":"05/05/2025","product":"Revolution","ai":"Wetting agent blend","type":"Wetting Agent","zone":"Greens","area":"1","rate":"20 L","total":"20 L","notes":"Pre-summer heat stress"},
    {"id":"2025-12","num":12,"date":"13/05/2025","product":"Eagle","ai":"Myclobutanil 20%","type":"Fungicide","zone":"Greens","area":"1","rate":"1 L","total":"1 L","notes":"DMI rotation"},
    {"id":"2025-13","num":13,"date":"13/05/2025","product":"Eagle","ai":"Myclobutanil 20%","type":"Fungicide","zone":"Tees","area":"1","rate":"1 L","total":"1 L","notes":"DMI rotation"},
    {"id":"2025-14","num":14,"date":"26/05/2025","product":"Mospilan","ai":"Acetamiprid 20%","type":"Insecticide","zone":"Greens","area":"1","rate":"250 g","total":"250 g","notes":"Aphid & leatherjacket"},
    {"id":"2025-15","num":15,"date":"26/05/2025","product":"Mospilan","ai":"Acetamiprid 20%","type":"Insecticide","zone":"Tees","area":"1","rate":"250 g","total":"250 g","notes":"Aphid & leatherjacket"},
    {"id":"2025-16","num":16,"date":"02/06/2025","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2025-17","num":17,"date":"09/06/2025","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Rough","area":"10","rate":"1.2 L","total":"12 L","notes":"Summer rough management"},
    {"id":"2025-18","num":18,"date":"16/06/2025","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Tees","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Extended PGR to tees"},
    {"id":"2025-19","num":19,"date":"16/06/2025","product":"Eagle","ai":"Myclobutanil 20%","type":"Fungicide","zone":"Greens","area":"1","rate":"1 L","total":"1 L","notes":"DMI continued"},
    {"id":"2025-20","num":20,"date":"16/06/2025","product":"Eagle","ai":"Myclobutanil 20%","type":"Fungicide","zone":"Tees","area":"1","rate":"1 L","total":"1 L","notes":"DMI continued"},
    {"id":"2025-21","num":21,"date":"23/06/2025","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2025-22","num":22,"date":"30/06/2025","product":"Revolution","ai":"Wetting agent blend","type":"Wetting Agent","zone":"Greens","area":"1","rate":"20 L","total":"20 L","notes":"Monthly wetting agent"},
    {"id":"2025-23","num":23,"date":"04/07/2025","product":"Junction","ai":"Mancozeb + Copper Hydroxide","type":"Fungicide","zone":"Greens","area":"1","rate":"5 kg","total":"5 kg","notes":"Multi-site resistance management"},
    {"id":"2025-24","num":24,"date":"04/07/2025","product":"Junction","ai":"Mancozeb + Copper Hydroxide","type":"Fungicide","zone":"Tees","area":"1","rate":"5 kg","total":"5 kg","notes":"Multi-site resistance management"},
    {"id":"2025-25","num":25,"date":"07/07/2025","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Rough","area":"10","rate":"1.2 L","total":"12 L","notes":"Summer rough management"},
    {"id":"2025-26","num":26,"date":"07/07/2025","product":"Deltagri","ai":"Deltamethrin 2.5%","type":"Insecticide","zone":"Greens","area":"1","rate":"1 L","total":"1 L","notes":"Cutworm damage observed"},
    {"id":"2025-27","num":27,"date":"07/07/2025","product":"Deltagri","ai":"Deltamethrin 2.5%","type":"Insecticide","zone":"Tees","area":"1","rate":"1 L","total":"1 L","notes":"Cutworm damage observed"},
    {"id":"2025-28","num":28,"date":"08/07/2025","product":"Deltagri","ai":"Deltamethrin 2.5%","type":"Insecticide","zone":"Fairways","area":"10","rate":"1 L","total":"10 L","notes":"Cutworm – fairway infestation"},
    {"id":"2025-29","num":29,"date":"14/07/2025","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2025-30","num":30,"date":"21/07/2025","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Tees","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Extended PGR to tees"},
    {"id":"2025-31","num":31,"date":"21/07/2025","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Greens","area":"1","rate":"4 kg","total":"4 kg","notes":"Peak summer Pythium"},
    {"id":"2025-32","num":32,"date":"21/07/2025","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Tees","area":"1","rate":"4 kg","total":"4 kg","notes":"Peak summer Pythium"},
    {"id":"2025-33","num":33,"date":"04/08/2025","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2025-34","num":34,"date":"04/08/2025","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Rough","area":"10","rate":"1.2 L","total":"12 L","notes":"Summer rough management"},
    {"id":"2025-35","num":35,"date":"04/08/2025","product":"Revolution","ai":"Wetting agent blend","type":"Wetting Agent","zone":"Greens","area":"1","rate":"20 L","total":"20 L","notes":"Peak summer dry patch"},
    {"id":"2025-36","num":36,"date":"25/08/2025","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2025-37","num":37,"date":"01/09/2025","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Rough","area":"10","rate":"1.2 L","total":"12 L","notes":"Summer rough management"},
    {"id":"2025-38","num":38,"date":"01/09/2025","product":"Revolution","ai":"Wetting agent blend","type":"Wetting Agent","zone":"Greens","area":"1","rate":"20 L","total":"20 L","notes":"Late summer wetting agent"},
    {"id":"2025-39","num":39,"date":"15/09/2025","product":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","zone":"Greens","area":"1","rate":"0.4 L","total":"0.4 L","notes":"Growth regulation"},
    {"id":"2025-40","num":40,"date":"22/09/2025","product":"Custodia","ai":"Azoxystrobin 120 g/L + Tebuconazole 200 g/L","type":"Fungicide","zone":"Greens","area":"1","rate":"0.75 L","total":"0.75 L","notes":"Autumn disease protection"},
    {"id":"2025-41","num":41,"date":"22/09/2025","product":"Custodia","ai":"Azoxystrobin 120 g/L + Tebuconazole 200 g/L","type":"Fungicide","zone":"Tees","area":"1","rate":"0.75 L","total":"0.75 L","notes":"Autumn disease protection"},
    {"id":"2025-42","num":42,"date":"13/10/2025","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Greens","area":"1","rate":"4 kg","total":"4 kg","notes":"Autumn Pythium"},
    {"id":"2025-43","num":43,"date":"13/10/2025","product":"Aliette","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","zone":"Tees","area":"1","rate":"4 kg","total":"4 kg","notes":"Autumn Pythium"},
    {"id":"2025-44","num":44,"date":"20/10/2025","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Tees","area":"1","rate":"1 + 0.5 L","total":"1 + 0.5 L","notes":"Autumn broadleaf flush"},
    {"id":"2025-45","num":45,"date":"21/10/2025","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Fairways","area":"10","rate":"1 + 0.5 L","total":"10 + 5 L","notes":"Autumn broadleaf flush"},
    {"id":"2025-46","num":46,"date":"22/10/2025","product":"Dicopur Top + Cerlit","ai":"MCPA+Dicamba / Mecoprop-P","type":"Herbicide","zone":"Rough","area":"10","rate":"1 + 0.5 L","total":"10 + 5 L","notes":"Autumn broadleaf flush"},
    {"id":"2025-47","num":47,"date":"03/11/2025","product":"Deltagri","ai":"Deltamethrin 2.5%","type":"Insecticide","zone":"Greens","area":"1","rate":"1 L","total":"1 L","notes":"Autumn cutworm / armyworm"},
    {"id":"2025-48","num":48,"date":"03/11/2025","product":"Deltagri","ai":"Deltamethrin 2.5%","type":"Insecticide","zone":"Tees","area":"1","rate":"1 L","total":"1 L","notes":"Autumn cutworm / armyworm"},
    {"id":"2025-49","num":49,"date":"10/11/2025","product":"Kerb Flo","ai":"Propyzamide 400 g/L","type":"Herbicide","zone":"Tees","area":"1","rate":"2.5 L","total":"2.5 L","notes":"Pre-emergent Poa annua"},
    {"id":"2025-50","num":50,"date":"11/11/2025","product":"Kerb Flo","ai":"Propyzamide 400 g/L","type":"Herbicide","zone":"Fairways","area":"10","rate":"2.5 L","total":"25 L","notes":"Pre-emergent Poa annua"},
    {"id":"2025-51","num":51,"date":"08/12/2025","product":"Greenlawnger","ai":"Green pigment colorant","type":"Colorant","zone":"Greens","area":"1","rate":"5 L","total":"5 L","notes":"Winter aesthetics"}
  ]}
}

DEFAULT_SDS = [
  {"id":"sds1","name":"Aliette WG","ai":"Fosetyl-Aluminium 80%","type":"Fungicide","manufacturer":"Bayer CropScience","frac":"FRAC P07 – Phosphonate","hazards":"H318 Serious eye damage. H302 Harmful if swallowed.","ppe":"Tight-sealing goggles, dust mask (P2), chemical-resistant gloves, protective coveralls","source":"Bayer CropScience official","link":"",
   "firstAid":"👁 EYES: Immediately flush with large amounts of water for at least 15 min, holding eyelids open. Seek medical attention urgently.\n🤢 SWALLOWED: Rinse mouth. Do NOT induce vomiting. Give water to drink if conscious. Seek medical attention immediately. Show this label.\n🖐 SKIN: Remove contaminated clothing. Wash skin thoroughly with soap and water for 15 min.\n🫁 INHALED: Move to fresh air. Rest. Seek medical attention if symptoms persist.\n📞 EMERGENCY: Call 112 (Malta) or Poisons Centre +356 2545 5000"},
  {"id":"sds2","name":"Custodia 320 SC","ai":"Azoxystrobin 120 g/L + Tebuconazole 200 g/L","type":"Fungicide","manufacturer":"ADAMA","frac":"FRAC 11 (QoI) + FRAC 3 (DMI)","hazards":"H361 Suspected reproductive toxicant. H317 Skin sensitisation. H410 Very toxic to aquatic life.","ppe":"Gloves, face shield/goggles, Type 5 coverall, rubber boots","source":"ADAMA UK official","link":"",
   "firstAid":"👁 EYES: Flush immediately with water for 15 min. Seek medical attention.\n🤢 SWALLOWED: Do NOT induce vomiting. Seek medical attention immediately. Show this label.\n🖐 SKIN: Remove clothing. Wash with soap and water. Seek medical attention if irritation persists.\n🫁 INHALED: Remove to fresh air. Rest. Seek medical attention if symptoms develop.\n📞 EMERGENCY: Call 112 (Malta) or Poisons Centre +356 2545 5000"},
  {"id":"sds3","name":"Dicopur Top + Cerlit","ai":"MCPA + Dicamba / Mecoprop-P","type":"Herbicide","manufacturer":"Nufarm / various","frac":"Synthetic auxin – Group O","hazards":"H318 Serious eye damage. H315 Skin irritation. H400 Aquatic toxicity.","ppe":"Gloves, goggles/face shield, protective clothing, rubber boots","source":"Nufarm official","link":"",
   "firstAid":"👁 EYES: Flush immediately with plenty of water for at least 15 min. Seek urgent medical attention — risk of serious eye damage.\n🤢 SWALLOWED: Rinse mouth. Do NOT induce vomiting. Seek immediate medical attention. Show this label.\n🖐 SKIN: Remove contaminated clothing immediately. Wash thoroughly with soap and water.\n🫁 INHALED: Move to fresh air. If breathing difficulty, seek medical attention.\n📞 EMERGENCY: Call 112 (Malta) or Poisons Centre +356 2545 5000"},
  {"id":"sds4","name":"Eagle 20EW","ai":"Myclobutanil 20%","type":"Fungicide","manufacturer":"Corteva Agriscience","frac":"FRAC 3 – DMI (Triazole)","hazards":"H361 Suspected reproductive toxicant. H400 Highly toxic to aquatic organisms.","ppe":"Gloves, splash-proof goggles, protective clothing, rubber boots","source":"Corteva official","link":"",
   "firstAid":"👁 EYES: Flush with water for 15 min. Seek medical attention.\n🤢 SWALLOWED: Do NOT induce vomiting. Seek immediate medical attention. Show this label — reproductive hazard.\n🖐 SKIN: Wash with soap and water. Remove contaminated clothing.\n🫁 INHALED: Fresh air. Rest. Seek medical attention if symptoms persist.\n📞 EMERGENCY: Call 112 (Malta) or Poisons Centre +356 2545 5000"},
  {"id":"sds5","name":"Emerald DG (Boscalid)","ai":"Boscalid 70.0% (C18H12Cl2N2O)","type":"Fungicide","manufacturer":"BASF Canada Inc.","frac":"FRAC 7 – SDHI (Carboxamide)","hazards":"Combustible Dust (Class 2). H302 Harmful if swallowed. Eye irritant. Contains allergen sulfite(s).","ppe":"NIOSH particulate respirator, chemical-resistant gloves, tightly fitting chemical goggles, protective coverall & boots","source":"BASF Canada Inc. – SDS v6.0 (2025/12/08)","link":"",
   "firstAid":"👁 EYES: Flush with water for 15 min. Seek medical attention if irritation persists.\n🤢 SWALLOWED: Rinse mouth. Do NOT induce vomiting. Seek medical attention. May cause allergic reaction in sulfite-sensitive individuals.\n🖐 SKIN: Wash thoroughly with soap and water. If allergic reaction occurs, seek medical attention.\n🫁 INHALED: Move to fresh air. If dust was inhaled heavily, seek medical attention — combustible dust hazard.\n⚠ NOTE: Contains sulfite allergen — inform medical staff.\n📞 EMERGENCY: Call 112 (Malta) or Poisons Centre +356 2545 5000"},
  {"id":"sds6","name":"Junction Fungicide","ai":"Mancozeb 15% + Copper Hydroxide 46.1%","type":"Fungicide","manufacturer":"SePRO Corporation","frac":"FRAC M3 + M1 – multi-site","hazards":"H318 Serious eye damage. H334 Respiratory sensitisation. H400 Very toxic to aquatic life.","ppe":"Goggles, P100 dust respirator, gloves, Type 5 coverall","source":"SePRO Corporation official","link":"",
   "firstAid":"👁 EYES: Flush immediately with water for at least 15 min. Seek urgent medical attention — risk of serious damage.\n🤢 SWALLOWED: Rinse mouth. Do NOT induce vomiting. Seek immediate medical attention.\n🖐 SKIN: Remove clothing. Wash with soap and water.\n🫁 INHALED: Move to fresh air immediately. Respiratory sensitiser — seek urgent medical attention even if symptoms are mild. Inform of copper/mancozeb exposure.\n📞 EMERGENCY: Call 112 (Malta) or Poisons Centre +356 2545 5000"},
  {"id":"sds7","name":"Kerb Flo 400 SC","ai":"Propyzamide 400 g/L","type":"Herbicide","manufacturer":"Corteva Agriscience","frac":"Amide – mitosis inhibitor (Group K1)","hazards":"H351 Suspected carcinogen. H317 Skin sensitisation. H410 Very toxic to aquatic life.","ppe":"Gloves, goggles, protective clothing, rubber boots","source":"Corteva Agriscience UK official","link":"",
   "firstAid":"👁 EYES: Flush with water for 15 min. Seek medical attention.\n🤢 SWALLOWED: Do NOT induce vomiting. Seek immediate medical attention. Suspected carcinogen — inform medical staff of product name and quantity.\n🖐 SKIN: Wash thoroughly with soap and water. Remove clothing. If allergic reaction, seek medical attention.\n🫁 INHALED: Move to fresh air. Seek medical attention.\n📞 EMERGENCY: Call 112 (Malta) or Poisons Centre +356 2545 5000"},
  {"id":"sds8","name":"Mospilan 20 SG","ai":"Acetamiprid 20%","type":"Insecticide","manufacturer":"Nippon Soda / Sumi-Agro","frac":"IRAC 4A – Neonicotinoid","hazards":"H302 Harmful if swallowed. H361d Suspected fetal toxicant. H400/H410 Very toxic to aquatic life.","ppe":"Gloves, goggles, protective clothing, dust mask. Do NOT apply near water.","source":"BASF equivalent SDS","link":"",
   "firstAid":"👁 EYES: Flush with water for 15 min. Seek medical attention.\n🤢 SWALLOWED: Rinse mouth. Do NOT induce vomiting. Seek immediate medical attention. Neonicotinoid — inform medical staff. Possible symptoms: nausea, tremors, dizziness.\n🖐 SKIN: Wash with soap and water. Remove contaminated clothing.\n🫁 INHALED: Move to fresh air. Rest. Seek medical attention if symptoms develop.\n⚠ PREGNANCY: Suspected fetal hazard — urgent medical attention if pregnant.\n📞 EMERGENCY: Call 112 (Malta) or Poisons Centre +356 2545 5000"},
  {"id":"sds9","name":"Pendimethalin 33 EC","ai":"Pendimethalin 330 g/L","type":"Herbicide","manufacturer":"Various (BASF, FMC)","frac":"Dinitroaniline – Group K1","hazards":"H304 Fatal if swallowed/enters airways. H351 Suspected carcinogen. H410 Very toxic to aquatic life.","ppe":"Gloves, goggles, protective clothing, rubber boots. Good ventilation.","source":"Generic Pendimethalin 33 EC SDS","link":"",
   "firstAid":"🚨 HIGH RISK — ASPIRATION HAZARD: If swallowed and enters airways, FATAL.\n👁 EYES: Flush immediately with water for 15 min. Seek urgent medical attention.\n🤢 SWALLOWED: Call 112 IMMEDIATELY. Do NOT induce vomiting — aspiration into lungs is fatal. Keep person calm and still. Show this label to medical staff.\n🖐 SKIN: Remove contaminated clothing. Wash with soap and water for 20 min.\n🫁 INHALED: Move to fresh air immediately. If breathing stops, give CPR. Call 112.\n📞 EMERGENCY: Call 112 IMMEDIATELY. Poisons Centre +356 2545 5000"},
  {"id":"sds10","name":"Primo Maxx","ai":"Trinexapac-ethyl 120 g/L","type":"PGR","manufacturer":"Syngenta","frac":"Gibberellin biosynthesis inhibitor – Group 16","hazards":"H317 Allergic skin reaction. H400 Very toxic to aquatic life.","ppe":"Gloves, safety glasses/goggles, protective clothing.","source":"Syngenta official","link":"",
   "firstAid":"👁 EYES: Flush with water for 15 min. Seek medical attention if irritation persists.\n🤢 SWALLOWED: Rinse mouth. Seek medical attention if large amount ingested.\n🖐 SKIN: Wash with soap and water. If allergic reaction (redness, swelling), seek medical attention.\n🫁 INHALED: Move to fresh air. Seek medical attention if symptoms persist.\n📞 EMERGENCY: Call 112 (Malta) or Poisons Centre +356 2545 5000"},
  {"id":"sds11","name":"Revolution Soil Surfactant","ai":"Wetting agent blend (proprietary)","type":"Wetting Agent","manufacturer":"Aquatrols","frac":"Non-pesticide – no FRAC code","hazards":"Low hazard. May cause eye/skin irritation on prolonged contact.","ppe":"Safety glasses, nitrile gloves, protective clothing.","source":"Aquatrols official (2022)","link":"",
   "firstAid":"👁 EYES: Flush with water for 15 min. Seek medical attention if irritation persists.\n🤢 SWALLOWED: Rinse mouth. Drink water. Seek medical attention if symptoms occur.\n🖐 SKIN: Wash with soap and water.\n🫁 INHALED: Move to fresh air.\n✅ LOW HAZARD product — standard first aid measures sufficient.\n📞 EMERGENCY: Call 112 (Malta) or Poisons Centre +356 2545 5000"},
  {"id":"sds12","name":"Deltagri EC","ai":"Deltamethrin 2.5%","type":"Insecticide","manufacturer":"Various (generic pyrethroid)","frac":"IRAC 3A – Pyrethroid","hazards":"H301+H311 Toxic if swallowed/on skin. H372 Nervous system damage. H400 Extremely toxic to fish.","ppe":"Full protective suit, gloves, face shield, rubber boots. HIGH HAZARD – do not apply near water.","source":"Sunnyside Corp SDS","link":"",
   "firstAid":"🚨 HIGH HAZARD — TOXIC ON SKIN AND IF SWALLOWED\n👁 EYES: Flush immediately with water for 15+ min. Seek urgent medical attention.\n🤢 SWALLOWED: Call 112 IMMEDIATELY. Do NOT induce vomiting. Pyrethroid poisoning symptoms: tingling, numbness, tremors, seizures. Inform medical staff of deltamethrin exposure.\n🖐 SKIN: Remove ALL contaminated clothing immediately. Wash skin thoroughly with soap and water for 20 min. Toxic through skin contact.\n🫁 INHALED: Move to fresh air immediately. If breathing difficulty or unconscious, call 112. Give CPR if needed.\n⚠ NERVOUS SYSTEM HAZARD: Symptoms may be delayed. Monitor for tremors, difficulty breathing.\n📞 EMERGENCY: Call 112 IMMEDIATELY. Poisons Centre +356 2545 5000"},
  {"id":"sds13","name":"Greenlawnger","ai":"Green pigment / colorant blend","type":"Colorant","manufacturer":"Various","frac":"No mode of action – aesthetic","hazards":"Low hazard. May cause temporary skin/eye staining.","ppe":"Standard nitrile gloves, safety glasses","source":"Contact supplier directly","link":"",
   "firstAid":"👁 EYES: Flush with water for 10 min. Staining is temporary — no lasting harm expected.\n🤢 SWALLOWED: Rinse mouth. Drink water. Seek medical attention if large quantity ingested.\n🖐 SKIN: Wash with soap and water. Staining will fade naturally.\n✅ LOW HAZARD product.\n📞 EMERGENCY: Call 112 (Malta) or Poisons Centre +356 2545 5000"},
  {"id":"sds14","name":"Hi Aktiv","ai":"Glyphosate 490 g/L","type":"Herbicide","manufacturer":"Various","frac":"EPSPS inhibitor – Group 9","hazards":"H317 Skin sensitisation. H373 Repeated exposure may cause organ damage.","ppe":"Gloves, goggles, protective clothing, rubber boots.","source":"Check product label","link":"",
   "firstAid":"👁 EYES: Flush with water for 15 min. Seek medical attention.\n🤢 SWALLOWED: Rinse mouth. Do NOT induce vomiting. Seek immediate medical attention. Glyphosate formulations can cause serious internal damage — inform medical staff.\n🖐 SKIN: Remove contaminated clothing. Wash with soap and water. If allergic reaction, seek medical attention.\n🫁 INHALED: Move to fresh air. Seek medical attention if symptoms develop.\n📞 EMERGENCY: Call 112 (Malta) or Poisons Centre +356 2545 5000"},
  {"id":"sds15","name":"Clearcast Herbicide","ai":"Ammonium salt of imazamox 12.1%","type":"Herbicide","manufacturer":"SePRO Corporation","frac":"ALS inhibitor – Group B/2","hazards":"H361 Suspected of damaging unborn child. H400 Very toxic to aquatic life.","ppe":"Chemical-resistant gloves, goggles, protective clothing, rubber boots.","source":"SePRO Corporation official","link":"",
   "firstAid":"👁 EYES: Flush with water for 15 min. Seek medical attention.\n🤢 SWALLOWED: Rinse mouth. Seek immediate medical attention. Show this label.\n🖐 SKIN: Remove clothing. Wash with soap and water.\n🫁 INHALED: Move to fresh air. Seek medical attention if symptoms persist.\n⚠ PREGNANCY: Suspected fetal hazard — seek urgent medical attention if pregnant.\n📞 EMERGENCY: Call 112 (Malta) or Poisons Centre +356 2545 5000"},
  {"id":"sds16","name":"Dicopur Top + Cerlit + Maintain","ai":"MCPA + Dicamba + Trinexapac-ethyl","type":"Herbicide/PGR","manufacturer":"Nufarm / Syngenta","frac":"Group O + Group 16","hazards":"H318 Serious eye damage. H315 Skin irritation. H400 Aquatic toxicity.","ppe":"Gloves, goggles, protective clothing, rubber boots.","source":"Combined – see individual products","link":"",
   "firstAid":"👁 EYES: Flush immediately with water for at least 15 min. Seek urgent medical attention — risk of serious eye damage.\n🤢 SWALLOWED: Do NOT induce vomiting. Seek immediate medical attention. Show this label — combined product.\n🖐 SKIN: Remove clothing immediately. Wash with soap and water.\n🫁 INHALED: Move to fresh air. Seek medical attention if breathing affected.\n📞 EMERGENCY: Call 112 (Malta) or Poisons Centre +356 2545 5000"}
]

DEFAULT_CALC = [
  {"id":"c1","category":"AERATION & TOPDRESSING","operation":"Greens – Mini-tine aeration","product":"","surface":"Greens","nApplications":10,"qty":None,"cost":None},
  {"id":"c2","category":"AERATION & TOPDRESSING","operation":"Greens – Core aeration + topdress","product":"","surface":"Greens","nApplications":2,"qty":None,"cost":None},
  {"id":"c3","category":"AERATION & TOPDRESSING","operation":"Greens – Light topdress","product":"","surface":"Greens","nApplications":6,"qty":None,"cost":None},
  {"id":"c4","category":"AERATION & TOPDRESSING","operation":"Aprons – Core aeration + topdress","product":"","surface":"Aprons & Surrounds","nApplications":3,"qty":None,"cost":None},
  {"id":"c5","category":"AERATION & TOPDRESSING","operation":"Tees – Core aeration + topdress","product":"","surface":"Tees","nApplications":1,"qty":None,"cost":None},
  {"id":"c6","category":"AERATION & TOPDRESSING","operation":"Tees – Overseeding (80 g/m²)","product":"","surface":"Tees","nApplications":2,"qty":None,"cost":None},
  {"id":"c7","category":"AERATION & TOPDRESSING","operation":"Fairways & Rough – Solid tine","product":"","surface":"Fairways","nApplications":1,"qty":None,"cost":None},
  {"id":"c8","category":"AERATION & TOPDRESSING","operation":"Fairways – Verticutt","product":"","surface":"Fairways","nApplications":3,"qty":None,"cost":None},
  {"id":"c9","category":"NUTRITION","operation":"Greens – Foliar Nutrition","product":"Foliar Fertiliser (Greens)","surface":"Greens","nApplications":7,"qty":None,"cost":None},
  {"id":"c10","category":"NUTRITION","operation":"Greens – Granular Nutrition","product":"Granular Fertiliser (Greens)","surface":"Greens","nApplications":4,"qty":None,"cost":None},
  {"id":"c11","category":"NUTRITION","operation":"Tees – 12-12-17 Granular","product":"12-12-17 Granular","surface":"Tees","nApplications":4,"qty":None,"cost":None},
  {"id":"c12","category":"NUTRITION","operation":"Surrounds – 12-12-17 Granular","product":"12-12-17 Granular","surface":"Aprons & Surrounds","nApplications":4,"qty":None,"cost":None},
  {"id":"c13","category":"NUTRITION","operation":"Fairways – Urea 46-0-0","product":"Urea 46-0-0","surface":"Fairways","nApplications":2,"qty":None,"cost":None},
  {"id":"c14","category":"NUTRITION","operation":"Rough – Urea 46-0-0","product":"Urea 46-0-0","surface":"Rough","nApplications":2,"qty":None,"cost":None},
  {"id":"c15","category":"WETTING AGENTS","operation":"Revolution – Greens","product":"Revolution Wetting Agent","surface":"Greens","nApplications":7,"qty":None,"cost":None},
  {"id":"c16","category":"PLANT PROTECTION","operation":"Fungicide – Greens","product":"Fungicide – Greens","surface":"Greens","nApplications":5,"qty":None,"cost":None},
  {"id":"c17","category":"PLANT PROTECTION","operation":"Fungicide – Fairways","product":"Fungicide – Fairways/Rough","surface":"Fairways","nApplications":3,"qty":None,"cost":None},
  {"id":"c18","category":"PLANT PROTECTION","operation":"Fungicide – Rough","product":"Fungicide – Fairways/Rough","surface":"Rough","nApplications":3,"qty":None,"cost":None},
  {"id":"c19","category":"PLANT PROTECTION","operation":"Herbicide – Kerb Flo Fairways","product":"Kerb Flo 400 SC","surface":"Fairways","nApplications":3,"qty":None,"cost":None},
  {"id":"c20","category":"PLANT PROTECTION","operation":"Herbicide – Kerb Flo Rough","product":"Kerb Flo 400 SC","surface":"Rough","nApplications":3,"qty":None,"cost":None},
  {"id":"c21","category":"PLANT PROTECTION","operation":"Herbicide – Spot POST-em Fairways","product":"Dicopur Top + Cerlit","surface":"Fairways","nApplications":2,"qty":None,"cost":None},
  {"id":"c22","category":"PLANT PROTECTION","operation":"Insecticide – White Grubs Fairways","product":"Insecticide – White Grubs","surface":"Fairways","nApplications":3,"qty":None,"cost":None},
  {"id":"c23","category":"PLANT PROTECTION","operation":"Insecticide – White Grubs Rough","product":"Insecticide – White Grubs","surface":"Rough","nApplications":3,"qty":None,"cost":None},
  {"id":"c24","category":"PLANT PROTECTION","operation":"Insecticide – Greens","product":"Insecticide – Greens","surface":"Greens","nApplications":5,"qty":None,"cost":None},
  {"id":"c25","category":"PLANT PROTECTION","operation":"Palm Trees – Insecticide","product":"Mospilan 20 SG","surface":"Greens","nApplications":6,"qty":None,"cost":None}
]

def load_data():
    if not os.path.exists(DATA_FILE):
        data = {"products":DEFAULT_PRODUCTS,"log":[],"surfaces":DEFAULT_SURFACES,
                "sprayLog":DEFAULT_SPRAY_LOG,"histLog":DEFAULT_HIST,
                "sds":DEFAULT_SDS}
        save_data(data); return data
    with open(DATA_FILE,'r',encoding='utf-8') as f: data = json.load(f)
    if "surfaces"  not in data: data["surfaces"]  = DEFAULT_SURFACES
    if "sprayLog"  not in data: data["sprayLog"]  = DEFAULT_SPRAY_LOG
    if "histLog"   not in data: data["histLog"]   = DEFAULT_HIST
    if "sds"       not in data: data["sds"]       = DEFAULT_SDS
    return data

def save_data(data):
    with open(DATA_FILE,'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)

# ── SUPABASE-AWARE API HELPERS ───────────────────────────────────────────────
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

LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RMGC Stock Manager – Login</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    background: #0e0f11;
    color: #f0f0f0;
    font-family: 'Segoe UI', system-ui, sans-serif;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .card {
    background: #161719;
    border: 1px solid #2a2c31;
    border-radius: 12px;
    padding: 2.5rem 2rem;
    width: 100%;
    max-width: 380px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
  }
  .logo-wrap {
    text-align: center;
    margin-bottom: 2rem;
  }
  .logo-wrap img {
    height: 72px;
    object-fit: contain;
    border-radius: 8px;
  }
  .logo-wrap h1 {
    font-size: 1.3rem;
    font-weight: 700;
    color: #f0f0f0;
    margin-top: 0.75rem;
    letter-spacing: 0.03em;
  }
  .logo-wrap p {
    color: #7a7d85;
    font-size: 0.85rem;
    margin-top: 0.25rem;
  }
  label {
    display: block;
    font-size: 0.8rem;
    font-weight: 600;
    color: #7a7d85;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.4rem;
    margin-top: 1.1rem;
  }
  input {
    width: 100%;
    background: #1e2024;
    border: 1px solid #2a2c31;
    border-radius: 8px;
    padding: 0.7rem 0.9rem;
    color: #f0f0f0;
    font-size: 0.95rem;
    outline: none;
    transition: border-color 0.2s;
  }
  input:focus { border-color: #e8442a; }
  .btn {
    width: 100%;
    margin-top: 1.6rem;
    padding: 0.8rem;
    background: #e8442a;
    color: #fff;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    cursor: pointer;
    transition: background 0.2s, transform 0.1s;
  }
  .btn:hover { background: #c73a23; }
  .btn:active { transform: scale(0.98); }
  .btn:disabled { background: #555; cursor: not-allowed; }
  .error {
    margin-top: 1rem;
    background: rgba(239,68,68,0.15);
    border: 1px solid rgba(239,68,68,0.4);
    border-radius: 8px;
    padding: 0.6rem 0.9rem;
    color: #ef4444;
    font-size: 0.88rem;
    display: none;
    text-align: center;
  }
</style>
</head>
<body>
<div class="card">
  <div class="logo-wrap">
    <img src="/logo" alt="RMGC Logo" onerror="this.style.display='none'">
    <h1>RMGC Stock Manager</h1>
    <p>Sign in to continue</p>
  </div>

  <label for="username">Username</label>
  <input type="text" id="username" placeholder="Enter username" autocomplete="username">

  <label for="password">Password</label>
  <input type="password" id="password" placeholder="Enter password" autocomplete="current-password">

  <div class="error" id="error-msg">Invalid username or password.</div>

  <button class="btn" id="login-btn" onclick="doLogin()">Sign In</button>
</div>

<script>
  // Allow pressing Enter to submit
  document.addEventListener('keydown', e => {
    if (e.key === 'Enter') doLogin();
  });

  async function doLogin() {
    const btn = document.getElementById('login-btn');
    const err = document.getElementById('error-msg');
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    err.style.display = 'none';
    if (!username || !password) {
      err.textContent = 'Please enter your username and password.';
      err.style.display = 'block';
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Signing in…';

    try {
      const res = await fetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (data.ok) {
        window.location.href = '/';
      } else {
        err.textContent = data.error || 'Invalid username or password.';
        err.style.display = 'block';
        btn.disabled = false;
        btn.textContent = 'Sign In';
      }
    } catch(e) {
      err.textContent = 'Connection error. Please try again.';
      err.style.display = 'block';
      btn.disabled = false;
      btn.textContent = 'Sign In';
    }
  }
</script>
</body>
</html>
"""

@app.route('/login', methods=['GET'])
def login_page():
    if 'user' in session:
        return redirect(url_for('index'))
    return LOGIN_HTML

@app.route('/login', methods=['POST'])
def do_login():
    data = request.get_json() or {}
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')
    if username in USERS and USERS[username] == password:
        session['user'] = username
        return jsonify({'ok': True})
    return jsonify({'error': 'Invalid username or password'}), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/')
@login_required
def index():
    return render_template('index.html', current_user=session.get('user'))

@app.route('/logo')
@login_required
def get_logo():
    from flask import send_file
    for ext in ['jpg','jpeg','png','gif','svg']:
        path = os.path.join(BASE_DIR, f'RMGC_LOGO.{ext}')
        if os.path.exists(path):
            return send_file(path)
    return '', 404

@app.route('/api/products',methods=['GET'])
@login_required
def get_products(): return jsonify(get_products_data())
@app.route('/api/products',methods=['POST'])
@login_required
def add_product():
    p=request.json; p['id']=str(uuid.uuid4())
    p.setdefault('stock',0); p.setdefault('reorderLevel',2); p.setdefault('notes','')
    if USE_SUPABASE:
        result = sb_post('rmgc_products', p); return jsonify(result),201
    data=load_data(); data['products'].append(p); save_data(data); return jsonify(p),201
@app.route('/api/products/<pid>',methods=['PUT'])
@login_required
def update_product(pid):
    body=request.json; body.pop('id',None)
    if USE_SUPABASE:
        sb_patch('rmgc_products','id',pid,body); return jsonify({'id':pid,**body})
    data=load_data()
    for i,p in enumerate(data['products']):
        if str(p['id'])==str(pid): data['products'][i]={**p,**body,'id':pid}; save_data(data); return jsonify(data['products'][i])
    return jsonify({'error':'Not found'}),404
@app.route('/api/products/<pid>',methods=['DELETE'])
@login_required
def delete_product(pid):
    if USE_SUPABASE:
        sb_delete('rmgc_products','id',pid); return jsonify({'ok':True})
    data=load_data(); data['products']=[p for p in data['products'] if str(p['id'])!=str(pid)]
    save_data(data); return jsonify({'ok':True})
@app.route('/api/stock/<pid>',methods=['POST'])
@login_required
def update_stock(pid):
    body=request.json
    qty=float(body.get('qty',0)); mtype=body.get('type','usage'); note=body.get('note','')
    if USE_SUPABASE:
        prods=sb_get('rmgc_products',f'id=eq.{pid}')
        if not prods: return jsonify({'error':'Not found'}),404
        p=prods[0]; old=float(p.get('stock',0))
        if mtype=='delivery': new_stock=round(old+qty,4)
        elif mtype=='usage':  new_stock=round(max(0,old-qty),4)
        elif mtype=='adjust': new_stock=round(qty,4)
        else: new_stock=old
        sb_patch('rmgc_products','id',pid,{'stock':new_stock})
        p['stock']=new_stock
        log_entry={'id':str(uuid.uuid4()),'productId':pid,'product':p['name'],'type':mtype,
                   'qty':qty,'before':old,'after':new_stock,'unit':p.get('unit',''),
                   'note':note,'date':datetime.now().strftime('%d/%m/%Y %H:%M')}
        try: sb_post('rmgc_stock_log', log_entry)
        except: pass
        return jsonify({'product':p,'entry':log_entry})
    data=load_data(); body=body
    for p in data['products']:
        if str(p['id'])==str(pid):
            old=float(p.get('stock',0))
            if mtype=='delivery': p['stock']=round(old+qty,4)
            elif mtype=='usage':  p['stock']=round(max(0,old-qty),4)
            elif mtype=='adjust': p['stock']=round(qty,4)
            entry={'id':str(uuid.uuid4()),'productId':pid,'product':p['name'],'type':mtype,'qty':qty,
                   'before':old,'after':p['stock'],'unit':p.get('unit',''),'note':note,
                   'date':datetime.now().strftime('%d/%m/%Y %H:%M')}
            data['log'].insert(0,entry); data['log']=data['log'][:500]; save_data(data)
            return jsonify({'product':p,'entry':entry})
    return jsonify({'error':'Not found'}),404
@app.route('/api/log',methods=['GET'])
@login_required
def get_log(): return jsonify(load_data().get('log',[]))
@app.route('/api/summary',methods=['GET'])
@login_required
def get_summary():
    data=load_data(); products=data['products']
    tv=sum(float(p.get('packCost',0))*float(p.get('stock',0)) for p in products)
    low=[p for p in products if 0<float(p.get('stock',0))<=float(p.get('reorderLevel',2))]
    out=[p for p in products if float(p.get('stock',0))==0]
    cats={}
    for p in products: c=p.get('category','Other'); cats[c]=cats.get(c,0)+1
    return jsonify({'totalProducts':len(products),'totalValue':round(tv,2),'lowStock':len(low),'outOfStock':len(out),'byCategory':cats})

@app.route('/api/surfaces',methods=['GET'])
@login_required
def get_surfaces(): return jsonify(load_data()['surfaces'])
@app.route('/api/surfaces/<sid>',methods=['PUT'])
@login_required
def update_surface(sid):
    data=load_data()
    for i,s in enumerate(data['surfaces']):
        if str(s['id'])==str(sid): data['surfaces'][i]={**s,**request.json,'id':sid}; save_data(data); return jsonify(data['surfaces'][i])
    return jsonify({'error':'Not found'}),404

@app.route('/api/spraylog',methods=['GET'])
@login_required
def get_spraylog(): return jsonify(get_spraylog_data())
@app.route('/api/spraylog',methods=['POST'])
@login_required
def add_spray():
    entry=request.json; entry['id']=str(uuid.uuid4())
    if USE_SUPABASE:
        result=sb_post('rmgc_spraylog',entry); return jsonify(result),201
    data=load_data(); data['sprayLog'].insert(0,entry); save_data(data); return jsonify(entry),201
@app.route('/api/spraylog/<eid>',methods=['DELETE'])
@login_required
def del_spray(eid):
    if USE_SUPABASE:
        sb_delete('rmgc_spraylog','id',eid); return jsonify({'ok':True})
    data=load_data(); data['sprayLog']=[e for e in data['sprayLog'] if str(e['id'])!=str(eid)]
    save_data(data); return jsonify({'ok':True})

@app.route('/api/histlog',methods=['GET'])
@login_required
def get_histlog(): return jsonify(load_data().get('histLog',DEFAULT_HIST))

@app.route('/api/sds',methods=['GET'])
@login_required
def get_sds(): return jsonify(load_data()['sds'])
@app.route('/api/sds',methods=['POST'])
@login_required
def add_sds():
    data=load_data(); entry=request.json; entry['id']=str(uuid.uuid4())
    data['sds'].append(entry); save_data(data); return jsonify(entry),201
@app.route('/api/sds/<sid>',methods=['PUT'])
@login_required
def upd_sds(sid):
    data=load_data()
    for i,s in enumerate(data['sds']):
        if str(s['id'])==str(sid): data['sds'][i]={**s,**request.json,'id':sid}; save_data(data); return jsonify(data['sds'][i])
    return jsonify({'error':'Not found'}),404
@app.route('/api/sds/<sid>',methods=['DELETE'])
@login_required
def del_sds(sid):
    data=load_data(); data['sds']=[s for s in data['sds'] if str(s['id'])!=str(sid)]
    save_data(data); return jsonify({'ok':True})

@app.route('/api/calc',methods=['GET'])
@login_required
def get_calc(): return jsonify(load_data()['calc'])
@app.route('/api/calc',methods=['POST'])
@login_required
def add_calc():
    data=load_data(); entry=request.json; entry['id']=str(uuid.uuid4())
    data['calc'].append(entry); save_data(data); return jsonify(entry),201
@app.route('/api/calc/<cid>',methods=['PUT'])
@login_required
def upd_calc(cid):
    data=load_data()
    for i,c in enumerate(data['calc']):
        if str(c['id'])==str(cid): data['calc'][i]={**c,**request.json,'id':cid}; save_data(data); return jsonify(data['calc'][i])
    return jsonify({'error':'Not found'}),404
@app.route('/api/calc/<cid>',methods=['DELETE'])
@login_required
def del_calc(cid):
    data=load_data(); data['calc']=[c for c in data['calc'] if str(c['id'])!=str(cid)]
    save_data(data); return jsonify({'ok':True})

@app.errorhandler(500)
def internal_error(e):
    import traceback
    return f"<pre>500 Internal Server Error:\n{traceback.format_exc()}</pre>", 500

if __name__=='__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)
