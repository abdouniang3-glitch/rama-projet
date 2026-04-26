# ============================================================
# RAMA - Application Flask complète
# Compatible Google Colab (Flask + SQLite + Jinja2)
# ============================================================
import sqlite3, os, hashlib, json
from datetime import datetime, date, timedelta
from functools import wraps
from flask import (Flask, render_template_string, request,
                   redirect, url_for, session, jsonify, g)

app = Flask(__name__)
app.secret_key = 'rama_secret_2026_change_in_production'
DB_PATH = 'rama.db'

# ─────────────────────────────────────────────
# Helpers DB
# ─────────────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

def query(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv

def mutate(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid

def hash_pwd(p): return hashlib.sha256(p.encode()).hexdigest()

def init_db():
    with open('schema.sql') as f:
        get_db().executescript(f.read())

# ─────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def deco(*a, **kw):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*a, **kw)
    return deco

def current_user():
    if 'user_id' not in session: return None
    return query("SELECT * FROM utilisateur WHERE id=?", [session['user_id']], one=True)

def notif_count():
    if 'user_id' not in session: return 0
    r = query("SELECT COUNT(*) as n FROM notification WHERE destinataire_id=? AND lu=0",
              [session['user_id']], one=True)
    return r['n'] if r else 0

def push_notif(dest_id, titre, msg, typ='info', lien=None):
    mutate("INSERT INTO notification(destinataire_id,titre,message,type,lien_reference) VALUES(?,?,?,?,?)",
           [dest_id, titre, msg, typ, lien])

# ─────────────────────────────────────────────
# BASE TEMPLATE (inline Jinja)
# ─────────────────────────────────────────────
BASE = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{% block title %}RAMA{% endblock %}</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<style>
:root{
  --bg:#0d1117;--bg2:#161b22;--bg3:#21262d;--border:#30363d;
  --text:#e6edf3;--text2:#8b949e;--text3:#484f58;
  --acc:#3fb950;--acc2:#238636;--blue:#58a6ff;--amber:#f0883e;
  --red:#f85149;--purple:#bc8cff;
  --rad:10px;--font:'Plus Jakarta Sans',sans-serif;--mono:'JetBrains Mono',monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--font);background:var(--bg);color:var(--text);min-height:100vh;display:flex;flex-direction:column}
a{color:var(--blue);text-decoration:none}
a:hover{text-decoration:underline}
/* Layout */
.shell{display:flex;flex:1}
.sidebar{width:240px;background:var(--bg2);border-right:1px solid var(--border);padding:0;display:flex;flex-direction:column;position:sticky;top:0;height:100vh;overflow-y:auto}
.sidebar-logo{padding:20px 20px 12px;border-bottom:1px solid var(--border)}
.sidebar-logo .wordmark{font-weight:700;font-size:18px;letter-spacing:-0.5px;color:var(--text)}
.sidebar-logo .sub{font-size:11px;color:var(--text2);font-family:var(--mono)}
.sidebar-nav{padding:12px 0;flex:1}
.nav-section{padding:6px 16px 4px;font-size:10px;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:1px}
.nav-item{display:flex;align-items:center;gap:10px;padding:8px 16px;color:var(--text2);font-size:13.5px;font-weight:500;transition:all .15s;cursor:pointer;border-left:3px solid transparent}
.nav-item:hover{background:var(--bg3);color:var(--text);text-decoration:none}
.nav-item.active{background:rgba(63,185,80,.08);color:var(--acc);border-left-color:var(--acc)}
.nav-item .icon{font-size:15px;width:18px;text-align:center}
.sidebar-footer{padding:16px;border-top:1px solid var(--border)}
.user-chip{display:flex;align-items:center;gap:10px}
.avatar{width:32px;height:32px;border-radius:50%;background:var(--acc2);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;color:#fff;flex-shrink:0}
.user-info .name{font-size:13px;font-weight:600}
.user-info .role{font-size:11px;color:var(--text2)}
/* Main */
.main{flex:1;display:flex;flex-direction:column;overflow:auto}
.topbar{background:var(--bg2);border-bottom:1px solid var(--border);padding:14px 28px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:10}
.topbar h1{font-size:17px;font-weight:700;letter-spacing:-.3px}
.topbar-actions{display:flex;align-items:center;gap:12px}
.content{padding:28px;flex:1}
/* Cards */
.card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--rad);padding:20px}
.card-sm{padding:16px}
.card h3{font-size:14px;font-weight:600;color:var(--text2);margin-bottom:12px;text-transform:uppercase;letter-spacing:.6px}
/* Grid */
.grid{display:grid;gap:16px}
.g2{grid-template-columns:repeat(2,1fr)}
.g3{grid-template-columns:repeat(3,1fr)}
.g4{grid-template-columns:repeat(4,1fr)}
/* Stats */
.stat-val{font-size:28px;font-weight:700;font-family:var(--mono);letter-spacing:-1px}
.stat-label{font-size:12px;color:var(--text2);margin-top:4px}
.stat-delta{font-size:11px;margin-top:6px}
/* Badges */
.badge{display:inline-flex;align-items:center;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;font-family:var(--mono)}
.b-green{background:rgba(63,185,80,.15);color:var(--acc)}
.b-amber{background:rgba(240,136,62,.15);color:var(--amber)}
.b-red{background:rgba(248,81,73,.15);color:var(--red)}
.b-blue{background:rgba(88,166,255,.15);color:var(--blue)}
.b-purple{background:rgba(188,140,255,.15);color:var(--purple)}
.b-gray{background:var(--bg3);color:var(--text2)}
/* Table */
.tbl{width:100%;border-collapse:collapse;font-size:13.5px}
.tbl th{padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--text2);text-transform:uppercase;letter-spacing:.6px;border-bottom:1px solid var(--border);white-space:nowrap}
.tbl td{padding:10px 14px;border-bottom:1px solid var(--border);vertical-align:middle}
.tbl tr:last-child td{border-bottom:none}
.tbl tr:hover td{background:rgba(255,255,255,.02)}
/* Buttons */
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:7px;font-size:13px;font-weight:600;cursor:pointer;border:none;transition:all .15s;font-family:var(--font)}
.btn-primary{background:var(--acc2);color:#fff}
.btn-primary:hover{background:#2ea043;text-decoration:none}
.btn-secondary{background:var(--bg3);color:var(--text);border:1px solid var(--border)}
.btn-secondary:hover{background:var(--border);text-decoration:none}
.btn-danger{background:rgba(248,81,73,.15);color:var(--red);border:1px solid rgba(248,81,73,.3)}
.btn-sm{padding:5px 10px;font-size:12px}
/* Forms */
.form-group{margin-bottom:16px}
label{display:block;font-size:12px;font-weight:600;color:var(--text2);margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px}
input,select,textarea{width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:9px 12px;border-radius:7px;font-size:13.5px;font-family:var(--font);transition:border .15s}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--blue)}
textarea{resize:vertical;min-height:80px}
select option{background:var(--bg2)}
/* Progress bar */
.prog-wrap{background:var(--bg3);border-radius:4px;height:6px;overflow:hidden}
.prog-bar{height:6px;border-radius:4px;background:var(--acc);transition:width .4s}
/* Gantt */
.gantt-row{display:flex;align-items:center;gap:0;margin-bottom:6px;font-size:12px}
.gantt-label{width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--text);flex-shrink:0;padding-right:10px}
.gantt-track{flex:1;background:var(--bg3);border-radius:4px;height:22px;position:relative}
.gantt-bar{height:22px;border-radius:4px;position:absolute;display:flex;align-items:center;padding:0 6px;font-size:10px;font-weight:600;overflow:hidden;white-space:nowrap;color:#fff}
/* Notif dot */
.notif-badge{background:var(--red);color:#fff;border-radius:50%;width:18px;height:18px;font-size:10px;display:inline-flex;align-items:center;justify-content:center;font-weight:700}
/* Flash */
.flash{padding:10px 16px;border-radius:7px;margin-bottom:16px;font-size:13px}
.flash-ok{background:rgba(63,185,80,.1);border:1px solid rgba(63,185,80,.3);color:var(--acc)}
.flash-err{background:rgba(248,81,73,.1);border:1px solid rgba(248,81,73,.3);color:var(--red)}
/* Misc */
.divider{height:1px;background:var(--border);margin:20px 0}
.empty{text-align:center;padding:40px;color:var(--text2);font-size:14px}
.chip{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;background:var(--bg3);color:var(--text2);border:1px solid var(--border)}
@media(max-width:900px){.sidebar{display:none}.g4,.g3{grid-template-columns:1fr 1fr}.g2{grid-template-columns:1fr}}
</style>
</head>
<body>
{% if session.user_id %}
<div class="shell">
<nav class="sidebar">
  <div class="sidebar-logo">
    <div class="wordmark">● RAMA</div>
    <div class="sub">v1.0 · 2025-2026</div>
  </div>
  <div class="sidebar-nav">
    <div class="nav-section">Principal</div>
    <a class="nav-item {% if request.endpoint=='dashboard' %}active{% endif %}" href="{{ url_for('dashboard') }}">
      <span class="icon">◈</span> Tableau de bord</a>
    <a class="nav-item {% if request.endpoint=='activites' %}active{% endif %}" href="{{ url_for('activites') }}">
      <span class="icon">◉</span> Activités</a>
    <a class="nav-item {% if 'taches' in request.endpoint %}active{% endif %}" href="{{ url_for('taches_liste') }}">
      <span class="icon">◎</span> Tâches</a>
    <div class="nav-section">Analyse</div>
    <a class="nav-item {% if request.endpoint=='indicateurs' %}active{% endif %}" href="{{ url_for('indicateurs') }}">
      <span class="icon">▣</span> Indicateurs</a>
    <div class="nav-section">Communication</div>
    <a class="nav-item {% if request.endpoint=='notifications' %}active{% endif %}" href="{{ url_for('notifications') }}">
      <span class="icon">◈</span> Notifications
      {% if notif_count() > 0 %}<span class="notif-badge">{{ notif_count() }}</span>{% endif %}
    </a>
    <a class="nav-item {% if request.endpoint=='boite_idees' %}active{% endif %}" href="{{ url_for('boite_idees') }}">
      <span class="icon">◇</span> Boîte à idées</a>
    <a class="nav-item {% if request.endpoint=='signalements' %}active{% endif %}" href="{{ url_for('signalements') }}">
      <span class="icon">△</span> Signalements</a>
    {% if session.niveau >= 3 %}
    <div class="nav-section">Administration</div>
    <a class="nav-item {% if request.endpoint=='utilisateurs' %}active{% endif %}" href="{{ url_for('utilisateurs') }}">
      <span class="icon">◉</span> Utilisateurs</a>
    {% endif %}
  </div>
  <div class="sidebar-footer">
    <div class="user-chip">
      <div class="avatar">{{ session.initials }}</div>
      <div class="user-info">
        <div class="name">{{ session.fullname }}</div>
        <div class="role">{{ session.role }}</div>
      </div>
    </div>
    <a href="{{ url_for('logout') }}" class="btn btn-secondary btn-sm" style="margin-top:10px;width:100%;justify-content:center">Déconnexion</a>
  </div>
</nav>
<div class="main">
  <div class="topbar">
    <h1>{% block page_title %}{% endblock %}</h1>
    <div class="topbar-actions">{% block topbar_actions %}{% endblock %}</div>
  </div>
  <div class="content">
    {% if flash_msg %}<div class="flash flash-{{ flash_type }}">{{ flash_msg }}</div>{% endif %}
    {% block content %}{% endblock %}
  </div>
</div>
</div>
{% else %}
{% block auth_content %}{% endblock %}
{% endif %}
</body></html>'''

# ─────────────────────────────────────────────
# LOGIN / LOGOUT
# ─────────────────────────────────────────────
LOGIN_TPL = BASE.replace('{% block auth_content %}{% endblock %}', '''
<div style="min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--bg)">
  <div style="width:380px">
    <div style="text-align:center;margin-bottom:32px">
      <div style="font-size:36px;font-weight:800;letter-spacing:-2px">● RAMA</div>
      <div style="color:var(--text2);font-size:13px;margin-top:6px;font-family:var(--mono)">Reporting &amp; Monitoring Administratif</div>
    </div>
    <div class="card">
      {% if error %}<div class="flash flash-err">{{ error }}</div>{% endif %}
      <form method="post">
        <div class="form-group"><label>Adresse e-mail</label>
          <input type="email" name="email" required autofocus placeholder="vous@organisation.sn"></div>
        <div class="form-group"><label>Mot de passe</label>
          <input type="password" name="password" required placeholder="••••••••"></div>
        <button class="btn btn-primary" type="submit" style="width:100%;justify-content:center">Connexion →</button>
      </form>
    </div>
    <p style="text-align:center;margin-top:16px;font-size:12px;color:var(--text2)">Demo : dg@uidt.sn / password123</p>
  </div>
</div>''')

@app.route('/', methods=['GET','POST'])
@app.route('/login', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        u = query("SELECT * FROM utilisateur WHERE email=? AND actif=1",
                  [request.form['email']], one=True)
        if u and u['mot_de_passe_hash'] == hash_pwd(request.form['password']):
            session.update({
                'user_id': u['id'],
                'fullname': f"{u['prenom']} {u['nom']}",
                'initials': (u['prenom'][0]+u['nom'][0]).upper(),
                'role': u['role'],
                'niveau': u['niveau_hierarchique'],
                'service_id': u['service_id']
            })
            return redirect(url_for('dashboard'))
        error = "Email ou mot de passe incorrect."
    return render_template_string(LOGIN_TPL, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────
DASH_TPL = BASE + '''
{% block page_title %}Tableau de bord{% endblock %}
{% block content %}
<div class="grid g4" style="margin-bottom:20px">
  <div class="card card-sm">
    <div class="stat-val" style="color:var(--blue)">{{ stats.activites }}</div>
    <div class="stat-label">Activités totales</div>
  </div>
  <div class="card card-sm">
    <div class="stat-val" style="color:var(--acc)">{{ stats.taches_terminees }}</div>
    <div class="stat-label">Tâches terminées</div>
  </div>
  <div class="card card-sm">
    <div class="stat-val" style="color:var(--amber)">{{ stats.taches_encours }}</div>
    <div class="stat-label">Tâches en cours</div>
  </div>
  <div class="card card-sm">
    <div class="stat-val" style="color:var(--red)">{{ stats.taches_retard }}</div>
    <div class="stat-label">Tâches en retard</div>
  </div>
</div>
<div class="grid g2">
  <div class="card">
    <h3>Avancement des activités</h3>
    {% for a in avancements %}
    <div style="margin-bottom:14px">
      <div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:13px">
        <span>{{ a.titre[:40] }}</span>
        <span style="font-family:var(--mono);font-size:12px;color:var(--text2)">{{ a.pct_avancement or 0 }}%</span>
      </div>
      <div class="prog-wrap"><div class="prog-bar" style="width:{{ a.pct_avancement or 0 }}%;background:{% if (a.pct_avancement or 0) >= 80 %}var(--acc){% elif (a.pct_avancement or 0) >= 40 %}var(--amber){% else %}var(--red){% endif %}"></div></div>
    </div>
    {% else %}<div class="empty">Aucune activité</div>{% endfor %}
  </div>
  <div class="card">
    <h3>Mes tâches récentes</h3>
    <table class="tbl">
      <thead><tr><th>Tâche</th><th>Activité</th><th>Statut</th></tr></thead>
      <tbody>
      {% for t in mes_taches %}
      <tr>
        <td>{{ t.libelle[:35] }}</td>
        <td style="color:var(--text2)">{{ t.activite[:25] }}</td>
        <td>{% if t.statut=='terminee' %}<span class="badge b-green">✓ terminée</span>
            {% elif t.statut=='en_cours' %}<span class="badge b-blue">▶ en cours</span>
            {% elif t.statut=='en_retard' %}<span class="badge b-red">⚠ retard</span>
            {% else %}<span class="badge b-gray">○ non démarrée</span>{% endif %}</td>
      </tr>
      {% else %}<tr><td colspan="3" class="empty">Aucune tâche assignée</td></tr>{% endfor %}
      </tbody>
    </table>
  </div>
</div>
<div class="card" style="margin-top:16px">
  <h3>Répartition des types d'activités par service</h3>
  <canvas id="chartActivites" style="max-height:220px"></canvas>
</div>
<script>
(async()=>{
  const resp = await fetch('/api/chart-activites');
  const d = await resp.json();
  new Chart(document.getElementById('chartActivites'),{
    type:'bar',
    data:{labels:d.labels,datasets:d.datasets},
    options:{
      responsive:true,plugins:{legend:{labels:{color:'#8b949e',font:{size:11}}}},
      scales:{
        x:{ticks:{color:'#8b949e'},grid:{color:'#21262d'}},
        y:{ticks:{color:'#8b949e'},grid:{color:'#21262d'},beginAtZero:true}
      }
    }
  });
})();
</script>
{% endblock %}'''

@app.route('/dashboard')
@login_required
def dashboard():
    stats = {
        'activites': query("SELECT COUNT(*) n FROM activite", one=True)['n'],
        'taches_terminees': query("SELECT COUNT(*) n FROM tache WHERE statut='terminee'", one=True)['n'],
        'taches_encours':   query("SELECT COUNT(*) n FROM tache WHERE statut='en_cours'", one=True)['n'],
        'taches_retard':    query("SELECT COUNT(*) n FROM tache WHERE statut='en_retard' OR (statut!='terminee' AND date_fin_prevue < date('now'))", one=True)['n'],
    }
    avancements = query("SELECT titre, pct_avancement FROM v_avancement_activite LIMIT 6")
    mes_taches = query("""
        SELECT t.libelle, a.titre as activite, at.statut
        FROM affectation_tache at
        JOIN tache t ON t.id=at.tache_id
        JOIN activite a ON a.id=t.activite_id
        WHERE at.utilisateur_id=? AND at.statut='active'
        ORDER BY at.date_affectation DESC LIMIT 8
    """, [session['user_id']])
    return render_template_string(DASH_TPL,
        stats=stats, avancements=avancements, mes_taches=mes_taches,
        flash_msg=session.pop('flash_msg',None), flash_type=session.pop('flash_type','ok'))

@app.route('/api/chart-activites')
@login_required
def api_chart_activites():
    rows = query("SELECT service, type_activite, nb_activites FROM v_activite_par_service")
    services = list({r['service'] for r in rows})
    types = list({r['type_activite'] for r in rows})
    colors = ['#3fb950','#58a6ff','#f0883e','#bc8cff','#f85149','#79c0ff']
    datasets = []
    for i, t in enumerate(types):
        data = [next((r['nb_activites'] for r in rows if r['service']==s and r['type_activite']==t), 0) for s in services]
        datasets.append({'label': t, 'data': data, 'backgroundColor': colors[i % len(colors)]+'99', 'borderColor': colors[i % len(colors)], 'borderWidth': 1})
    return jsonify({'labels': services, 'datasets': datasets})

# ─────────────────────────────────────────────
# ACTIVITÉS
# ─────────────────────────────────────────────
ACT_TPL = BASE + '''
{% block page_title %}Activités{% endblock %}
{% block topbar_actions %}
<a href="{{ url_for('activite_new') }}" class="btn btn-primary">+ Nouvelle activité</a>
{% endblock %}
{% block content %}
<div class="card">
  <table class="tbl">
    <thead><tr><th>Titre</th><th>Type</th><th>Service</th><th>Période prévue</th><th>Avancement</th><th>Statut</th><th></th></tr></thead>
    <tbody>
    {% for a in activites %}
    <tr>
      <td><a href="{{ url_for('activite_detail', id=a.id) }}" style="font-weight:600;color:var(--text)">{{ a.titre }}</a></td>
      <td><span class="chip">{{ a.type }}</span></td>
      <td style="color:var(--text2)">{{ a.service or '—' }}</td>
      <td style="font-family:var(--mono);font-size:12px;color:var(--text2)">{{ a.date_debut_prevue }} → {{ a.date_fin_prevue }}</td>
      <td style="width:120px">
        <div class="prog-wrap"><div class="prog-bar" style="width:{{ a.pct or 0 }}%"></div></div>
        <span style="font-size:11px;color:var(--text2)">{{ a.pct or 0 }}%</span>
      </td>
      <td>{% if a.statut=='planifiee' %}<span class="badge b-blue">planifiée</span>
          {% elif a.statut=='en_cours' %}<span class="badge b-amber">en cours</span>
          {% elif a.statut=='terminee' %}<span class="badge b-green">terminée</span>
          {% else %}<span class="badge b-gray">{{ a.statut }}</span>{% endif %}</td>
      <td><a href="{{ url_for('activite_detail', id=a.id) }}" class="btn btn-secondary btn-sm">Détail →</a></td>
    </tr>
    {% else %}<tr><td colspan="7" class="empty">Aucune activité enregistrée</td></tr>{% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}'''

@app.route('/activites')
@login_required
def activites():
    rows = query("""
        SELECT a.id, a.titre, a.statut, a.date_debut_prevue, a.date_fin_prevue,
               ta.libelle as type, s.nom as service,
               v.pct_avancement as pct
        FROM activite a
        JOIN type_activite ta ON ta.id=a.type_activite_id
        LEFT JOIN service s ON s.id=a.service_id
        LEFT JOIN v_avancement_activite v ON v.id=a.id
        ORDER BY a.date_debut_prevue DESC
    """)
    return render_template_string(ACT_TPL, activites=rows,
        flash_msg=session.pop('flash_msg',None), flash_type=session.pop('flash_type','ok'))

@app.route('/activites/<int:id>')
@login_required
def activite_detail(id):
    a = query("""SELECT a.*,ta.libelle as type, s.nom as service_nom,
                        u.nom||' '||u.prenom as initiateur
                 FROM activite a
                 JOIN type_activite ta ON ta.id=a.type_activite_id
                 LEFT JOIN service s ON s.id=a.service_id
                 LEFT JOIN utilisateur u ON u.id=a.initiateur_id
                 WHERE a.id=?""", [id], one=True)
    if not a: return redirect(url_for('activites'))
    taches = query("""
        SELECT t.*, u.nom||' '||u.prenom as responsable
        FROM tache t
        LEFT JOIN affectation_tache at ON at.tache_id=t.id AND at.statut='active'
        LEFT JOIN utilisateur u ON u.id=at.utilisateur_id
        WHERE t.activite_id=? ORDER BY t.ordre
    """, [id])
    utilisateurs = query("SELECT id, nom, prenom, niveau_hierarchique FROM utilisateur WHERE actif=1 ORDER BY nom")
    avancement = query("SELECT pct_avancement FROM v_avancement_activite WHERE id=?", [id], one=True)
    DETAIL_TPL = BASE + '''
{% block page_title %}{{ a.titre[:50] }}{% endblock %}
{% block topbar_actions %}
<a href="{{ url_for('activites') }}" class="btn btn-secondary">← Retour</a>
<a href="{{ url_for('gantt', activite_id=a.id) }}" class="btn btn-secondary">📊 Gantt</a>
{% endblock %}
{% block content %}
{% if flash_msg %}<div class="flash flash-{{ flash_type }}">{{ flash_msg }}</div>{% endif %}
<div class="grid g2" style="margin-bottom:20px">
  <div class="card">
    <h3>Informations</h3>
    <table class="tbl">
      <tr><td style="color:var(--text2)">Type</td><td><span class="chip">{{ a.type }}</span></td></tr>
      <tr><td style="color:var(--text2)">Service</td><td>{{ a.service_nom or '—' }}</td></tr>
      <tr><td style="color:var(--text2)">Initiateur</td><td>{{ a.initiateur }}</td></tr>
      <tr><td style="color:var(--text2)">Période prévue</td><td style="font-family:var(--mono);font-size:12px">{{ a.date_debut_prevue }} → {{ a.date_fin_prevue }}</td></tr>
      <tr><td style="color:var(--text2)">Avancement</td>
          <td><div class="prog-wrap" style="margin-bottom:4px"><div class="prog-bar" style="width:{{ avancement.pct_avancement or 0 }}%"></div></div>{{ avancement.pct_avancement or 0 }}%</td></tr>
      <tr><td style="color:var(--text2)">Statut</td><td>{{ a.statut }}</td></tr>
    </table>
    {% if a.description %}<div class="divider"></div><p style="font-size:13px;color:var(--text2)">{{ a.description }}</p>{% endif %}
  </div>
  <div class="card">
    <h3>Ajouter une tâche</h3>
    <form method="post" action="{{ url_for('tache_create', activite_id=a.id) }}">
      <div class="form-group"><label>Libellé</label><input name="libelle" required></div>
      <div class="form-group"><label>Type de livrable</label>
        <select name="type_livrable"><option value="">—</option>
          {% for l in ['Convocation','TDR','Rapport','Compte-rendu','PV','Fiche technique','AMI','AAC','Dossier marché','Note de service'] %}
          <option>{{ l }}</option>{% endfor %}</select></div>
      <div class="grid g2">
        <div class="form-group"><label>Début prévu</label><input type="date" name="date_debut" required></div>
        <div class="form-group"><label>Fin prévue</label><input type="date" name="date_fin" required></div>
      </div>
      <button class="btn btn-primary" type="submit">Créer la tâche</button>
    </form>
  </div>
</div>
<div class="card">
  <h3>Tâches ({{ taches|length }})</h3>
  <table class="tbl">
    <thead><tr><th>#</th><th>Libellé</th><th>Livrable</th><th>Délais prévus</th><th>Responsable</th><th>Statut</th><th>Actions</th></tr></thead>
    <tbody>
    {% for t in taches %}
    <tr>
      <td style="font-family:var(--mono);color:var(--text2)">{{ loop.index }}</td>
      <td style="font-weight:500">{{ t.libelle }}</td>
      <td><span class="chip">{{ t.type_livrable or '—' }}</span></td>
      <td style="font-family:var(--mono);font-size:11px;color:var(--text2)">{{ t.date_debut_prevue }}<br>→ {{ t.date_fin_prevue }}</td>
      <td>{{ t.responsable or '<em style="color:var(--text3)">Non assigné</em>'|safe }}</td>
      <td>{% if t.statut=='terminee' %}<span class="badge b-green">✓</span>
          {% elif t.statut=='en_cours' %}<span class="badge b-blue">▶</span>
          {% elif t.statut=='en_retard' %}<span class="badge b-red">⚠</span>
          {% else %}<span class="badge b-gray">○</span>{% endif %}</td>
      <td style="display:flex;gap:6px;flex-wrap:wrap">
        {% if session.niveau > 1 %}
        <form method="post" action="{{ url_for('affecter_tache', tache_id=t.id) }}" style="display:flex;gap:4px">
          <select name="utilisateur_id" style="width:130px;padding:4px 6px;font-size:12px">
            {% for u in utilisateurs %}{% if u.niveau_hierarchique < session.niveau %}
            <option value="{{ u.id }}">{{ u.prenom }} {{ u.nom }}</option>
            {% endif %}{% endfor %}
          </select>
          <button class="btn btn-primary btn-sm" type="submit">Assigner</button>
        </form>
        {% endif %}
        <form method="post" action="{{ url_for('tache_statut', tache_id=t.id) }}" style="display:flex;gap:4px">
          <select name="statut" style="width:120px;padding:4px 6px;font-size:12px">
            {% for s in ['non_demarree','en_cours','terminee','en_retard','annulee'] %}
            <option {% if s==t.statut %}selected{% endif %}>{{ s }}</option>{% endfor %}
          </select>
          <button class="btn btn-secondary btn-sm" type="submit">Màj</button>
        </form>
      </td>
    </tr>
    {% else %}<tr><td colspan="7" class="empty">Aucune tâche pour cette activité</td></tr>{% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}'''
    return render_template_string(DETAIL_TPL, a=a, taches=taches, utilisateurs=utilisateurs,
        avancement=avancement or {'pct_avancement':0},
        flash_msg=session.pop('flash_msg',None), flash_type=session.pop('flash_type','ok'))

@app.route('/activites/new', methods=['GET','POST'])
@login_required
def activite_new():
    types = query("SELECT * FROM type_activite ORDER BY libelle")
    services = query("SELECT * FROM service ORDER BY nom")
    error = None
    if request.method == 'POST':
        f = request.form
        try:
            aid = mutate("""INSERT INTO activite
                (type_activite_id,initiateur_id,service_id,titre,description,lieu,
                 date_debut_prevue,date_fin_prevue,statut)
                VALUES(?,?,?,?,?,?,?,?,'planifiee')""",
                [f['type_id'], session['user_id'], f.get('service_id') or None,
                 f['titre'], f.get('description',''), f.get('lieu',''),
                 f['date_debut'], f['date_fin']])
            session['flash_msg'] = 'Activité créée avec succès.'
            session['flash_type'] = 'ok'
            return redirect(url_for('activite_detail', id=aid))
        except Exception as e:
            error = str(e)
    NEW_TPL = BASE + '''
{% block page_title %}Nouvelle activité{% endblock %}
{% block topbar_actions %}<a href="{{ url_for('activites') }}" class="btn btn-secondary">← Annuler</a>{% endblock %}
{% block content %}
<div class="card" style="max-width:640px">
  {% if error %}<div class="flash flash-err">{{ error }}</div>{% endif %}
  <form method="post">
    <div class="form-group"><label>Titre</label><input name="titre" required></div>
    <div class="grid g2">
      <div class="form-group"><label>Type d\'activité</label>
        <select name="type_id" required>{% for t in types %}<option value="{{ t.id }}">{{ t.libelle }}</option>{% endfor %}</select></div>
      <div class="form-group"><label>Service</label>
        <select name="service_id"><option value="">— Tous —</option>{% for s in services %}<option value="{{ s.id }}">{{ s.nom }}</option>{% endfor %}</select></div>
    </div>
    <div class="grid g2">
      <div class="form-group"><label>Date de début prévue</label><input type="date" name="date_debut" required></div>
      <div class="form-group"><label>Date de fin prévue</label><input type="date" name="date_fin" required></div>
    </div>
    <div class="form-group"><label>Lieu</label><input name="lieu" placeholder="Facultatif"></div>
    <div class="form-group"><label>Description</label><textarea name="description"></textarea></div>
    <button class="btn btn-primary" type="submit">Créer l\'activité →</button>
  </form>
</div>
{% endblock %}'''
    return render_template_string(NEW_TPL, types=types, services=services, error=error)

# ─────────────────────────────────────────────
# TÂCHES (actions)
# ─────────────────────────────────────────────
@app.route('/taches/<int:tache_id>/affecter', methods=['POST'])
@login_required
def affecter_tache(tache_id):
    uid = int(request.form['utilisateur_id'])
    cible = query("SELECT * FROM utilisateur WHERE id=?", [uid], one=True)
    if not cible or cible['niveau_hierarchique'] >= session['niveau']:
        session['flash_msg'] = 'Règle N+1 : vous ne pouvez assigner qu\'à un niveau inférieur.'
        session['flash_type'] = 'err'
    else:
        mutate("UPDATE affectation_tache SET statut='retiree' WHERE tache_id=? AND statut='active'", [tache_id])
        aid = mutate("INSERT INTO affectation_tache(tache_id,utilisateur_id,assigne_par_id,statut) VALUES(?,?,?,'active')",
                     [tache_id, uid, session['user_id']])
        mutate("INSERT INTO historique_affectation(affectation_id,nouvel_utilisateur_id,type_changement,effectue_par_id) VALUES(?,?,'attribution',?)",
               [aid, uid, session['user_id']])
        push_notif(uid, 'Nouvelle tâche assignée',
                   f"Une tâche vous a été assignée par {session['fullname']}.",
                   'affectation', f'/taches')
        session['flash_msg'] = f'Tâche assignée à {cible["prenom"]} {cible["nom"]}.'
        session['flash_type'] = 'ok'
    tache = query("SELECT activite_id FROM tache WHERE id=?", [tache_id], one=True)
    return redirect(url_for('activite_detail', id=tache['activite_id']))

@app.route('/taches/<int:tache_id>/statut', methods=['POST'])
@login_required
def tache_statut(tache_id):
    s = request.form['statut']
    updates = {'statut': s}
    if s == 'en_cours':
        mutate("UPDATE tache SET statut=?, date_debut_reelle=date('now') WHERE id=?", [s, tache_id])
    elif s == 'terminee':
        mutate("UPDATE tache SET statut=?, date_fin_reelle=date('now') WHERE id=?", [s, tache_id])
        mutate("UPDATE affectation_tache SET statut='terminee', date_realisation=date('now') WHERE tache_id=? AND statut='active'", [tache_id])
    else:
        mutate("UPDATE tache SET statut=? WHERE id=?", [s, tache_id])
    tache = query("SELECT activite_id FROM tache WHERE id=?", [tache_id], one=True)
    session['flash_msg'] = 'Statut mis à jour.'
    session['flash_type'] = 'ok'
    return redirect(url_for('activite_detail', id=tache['activite_id']))

@app.route('/taches/<int:activite_id>/create', methods=['POST'])
@login_required
def tache_create(activite_id):
    f = request.form
    mutate("INSERT INTO tache(activite_id,libelle,type_livrable,date_debut_prevue,date_fin_prevue,statut) VALUES(?,?,?,?,?,'non_demarree')",
           [activite_id, f['libelle'], f.get('type_livrable',''), f['date_debut'], f['date_fin']])
    session['flash_msg'] = 'Tâche créée.'
    session['flash_type'] = 'ok'
    return redirect(url_for('activite_detail', id=activite_id))

@app.route('/taches')
@login_required
def taches_liste():
    rows = query("""
        SELECT t.*, a.titre as activite, at.statut as aff_statut,
               u.nom||' '||u.prenom as responsable
        FROM tache t
        JOIN activite a ON a.id=t.activite_id
        LEFT JOIN affectation_tache at ON at.tache_id=t.id AND at.statut='active'
        LEFT JOIN utilisateur u ON u.id=at.utilisateur_id
        ORDER BY t.date_fin_prevue
    """)
    TPL = BASE + '''{% block page_title %}Toutes les tâches{% endblock %}
{% block content %}
<div class="card">
<table class="tbl">
<thead><tr><th>Tâche</th><th>Activité</th><th>Livrable</th><th>Fin prévue</th><th>Responsable</th><th>Statut</th></tr></thead>
<tbody>
{% for t in taches %}
<tr>
  <td style="font-weight:500">{{ t.libelle }}</td>
  <td style="color:var(--text2)">{{ t.activite }}</td>
  <td><span class="chip">{{ t.type_livrable or '—' }}</span></td>
  <td style="font-family:var(--mono);font-size:12px">{{ t.date_fin_prevue }}</td>
  <td>{{ t.responsable or '—' }}</td>
  <td>{% if t.statut=='terminee' %}<span class="badge b-green">✓ terminée</span>
      {% elif t.statut=='en_cours' %}<span class="badge b-blue">▶ en cours</span>
      {% elif t.statut=='en_retard' %}<span class="badge b-red">⚠ retard</span>
      {% else %}<span class="badge b-gray">○ non démarrée</span>{% endif %}</td>
</tr>
{% else %}<tr><td colspan="6" class="empty">Aucune tâche</td></tr>{% endfor %}
</tbody></table>
</div>
{% endblock %}'''
    return render_template_string(TPL, taches=rows)

# ─────────────────────────────────────────────
# GANTT
# ─────────────────────────────────────────────
@app.route('/gantt/<int:activite_id>')
@login_required
def gantt(activite_id):
    a = query("SELECT * FROM activite WHERE id=?", [activite_id], one=True)
    taches = query("SELECT * FROM tache WHERE activite_id=? ORDER BY ordre", [activite_id])
    GANTT_TPL = BASE + '''
{% block page_title %}Gantt : {{ a.titre[:40] }}{% endblock %}
{% block topbar_actions %}<a href="{{ url_for('activite_detail', id=a.id) }}" class="btn btn-secondary">← Retour</a>{% endblock %}
{% block content %}
<div class="card">
  <div id="gantt-container" style="overflow-x:auto"></div>
</div>
<script>
const taches = {{ taches_json|safe }};
const debut = new Date("{{ a.date_debut_prevue }}");
const fin   = new Date("{{ a.date_fin_prevue }}");
const total = (fin - debut) / 86400000 || 1;
const cont = document.getElementById('gantt-container');
const colors = {terminee:'#3fb950',en_cours:'#58a6ff',en_retard:'#f85149',non_demarree:'#484f58',annulee:'#484f58'};

let html = '<div style="padding:8px 0">';
taches.forEach(t => {
  const td = new Date(t.date_debut_prevue);
  const tf = new Date(t.date_fin_prevue);
  const left = Math.max(0, (td - debut)/86400000/total*100);
  const width = Math.max(2, (tf - td)/86400000/total*100);
  const color = colors[t.statut] || '#484f58';
  html += `<div class="gantt-row">
    <div class="gantt-label" title="${t.libelle}">${t.libelle}</div>
    <div class="gantt-track">
      <div class="gantt-bar" style="left:${left}%;width:${width}%;background:${color}">
        ${t.type_livrable||''}
      </div>
    </div>
  </div>`;
});
html += '</div>';
cont.innerHTML = html;
</script>
{% endblock %}'''
    import json as _json
    return render_template_string(GANTT_TPL, a=a,
        taches_json=_json.dumps([dict(t) for t in taches]))

# ─────────────────────────────────────────────
# INDICATEURS
# ─────────────────────────────────────────────
@app.route('/indicateurs')
@login_required
def indicateurs():
    prod = query("SELECT * FROM v_productivite_intervenant ORDER BY taux_completion_pct DESC NULLS LAST")
    ecarts = query("SELECT * FROM v_ecart_delais ORDER BY ecart_jours DESC LIMIT 10")
    IND_TPL = BASE + '''
{% block page_title %}Indicateurs de performance{% endblock %}
{% block content %}
<div class="grid g2">
<div class="card">
  <h3>Productivité par intervenant</h3>
  <table class="tbl">
    <thead><tr><th>Intervenant</th><th>Service</th><th>Assignées</th><th>Terminées</th><th>Taux</th></tr></thead>
    <tbody>
    {% for p in prod %}
    <tr>
      <td style="font-weight:600">{{ p.intervenant }}</td>
      <td style="color:var(--text2)">{{ p.service or '—' }}</td>
      <td style="font-family:var(--mono)">{{ p.total_taches_affectees }}</td>
      <td style="font-family:var(--mono)">{{ p.taches_terminees }}</td>
      <td>
        <div class="prog-wrap" style="width:80px;display:inline-block;margin-right:6px">
          <div class="prog-bar" style="width:{{ p.taux_completion_pct or 0 }}%;background:{% if (p.taux_completion_pct or 0)>=70 %}var(--acc){% elif (p.taux_completion_pct or 0)>=40 %}var(--amber){% else %}var(--red){% endif %}"></div>
        </div>
        <span style="font-family:var(--mono);font-size:12px">{{ p.taux_completion_pct or 0 }}%</span>
      </td>
    </tr>
    {% else %}<tr><td colspan="5" class="empty">Aucune donnée</td></tr>{% endfor %}
    </tbody>
  </table>
</div>
<div class="card">
  <h3>Écarts sur délais (tâches achevées)</h3>
  <table class="tbl">
    <thead><tr><th>Tâche</th><th>Activité</th><th>Écart (j)</th></tr></thead>
    <tbody>
    {% for e in ecarts %}
    <tr>
      <td>{{ e.libelle[:35] }}</td>
      <td style="color:var(--text2)">{{ e.activite[:25] }}</td>
      <td>
        {% if e.ecart_jours > 0 %}<span class="badge b-red">+{{ e.ecart_jours|int }}j</span>
        {% elif e.ecart_jours < 0 %}<span class="badge b-green">{{ e.ecart_jours|int }}j</span>
        {% else %}<span class="badge b-gray">0j</span>{% endif %}
      </td>
    </tr>
    {% else %}<tr><td colspan="3" class="empty">Aucune tâche terminée encore</td></tr>{% endfor %}
    </tbody>
  </table>
</div>
</div>
{% endblock %}'''
    return render_template_string(IND_TPL, prod=prod, ecarts=ecarts)

# ─────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────
@app.route('/notifications')
@login_required
def notifications():
    notifs = query("SELECT * FROM notification WHERE destinataire_id=? ORDER BY date_envoi DESC", [session['user_id']])
    mutate("UPDATE notification SET lu=1 WHERE destinataire_id=?", [session['user_id']])
    NOTIF_TPL = BASE + '''
{% block page_title %}Notifications{% endblock %}
{% block content %}
<div class="card">
{% for n in notifs %}
<div style="padding:14px 0;border-bottom:1px solid var(--border);display:flex;gap:14px;align-items:flex-start">
  <div style="width:8px;height:8px;border-radius:50%;background:{% if n.type=='alerte' %}var(--red){% elif n.type=='affectation' %}var(--blue){% else %}var(--acc){% endif %};margin-top:6px;flex-shrink:0"></div>
  <div style="flex:1">
    <div style="font-weight:600;font-size:14px">{{ n.titre or 'Notification' }}</div>
    <div style="color:var(--text2);font-size:13px;margin-top:4px">{{ n.message }}</div>
    <div style="color:var(--text3);font-size:11px;font-family:var(--mono);margin-top:6px">{{ n.date_envoi }}</div>
  </div>
</div>
{% else %}<div class="empty">Aucune notification</div>{% endfor %}
</div>
{% endblock %}'''
    return render_template_string(NOTIF_TPL, notifs=notifs)

# ─────────────────────────────────────────────
# BOÎTE À IDÉES
# ─────────────────────────────────────────────
@app.route('/idees', methods=['GET','POST'])
@login_required
def boite_idees():
    if request.method == 'POST':
        f = request.form
        mutate("INSERT INTO idee(proposant_id,titre,description) VALUES(?,?,?)",
               [session['user_id'], f['titre'], f['description']])
        session['flash_msg'] = 'Idée soumise avec succès !'
        session['flash_type'] = 'ok'
        return redirect(url_for('boite_idees'))
    idees = query("""SELECT i.*,u.nom||' '||u.prenom as proposant
                     FROM idee i JOIN utilisateur u ON u.id=i.proposant_id
                     ORDER BY i.votes DESC, i.date_proposition DESC""")
    IDEE_TPL = BASE + '''
{% block page_title %}Boîte à idées{% endblock %}
{% block content %}
{% if flash_msg %}<div class="flash flash-{{ flash_type }}">{{ flash_msg }}</div>{% endif %}
<div class="grid g2" style="align-items:start">
<div class="card">
  <h3>Soumettre une idée</h3>
  <form method="post">
    <div class="form-group"><label>Titre</label><input name="titre" required placeholder="Votre idée en quelques mots"></div>
    <div class="form-group"><label>Description détaillée</label><textarea name="description" required placeholder="Décrivez votre idée..."></textarea></div>
    <button class="btn btn-primary" type="submit">Soumettre →</button>
  </form>
</div>
<div>
{% for i in idees %}
<div class="card card-sm" style="margin-bottom:12px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <div style="font-weight:700;font-size:14px">{{ i.titre }}</div>
      <div style="color:var(--text2);font-size:12px;margin-top:2px">{{ i.proposant }} · {{ i.date_proposition[:10] }}</div>
    </div>
    <div style="display:flex;align-items:center;gap:8px">
      <span style="font-family:var(--mono);font-size:16px;font-weight:700;color:var(--acc)">▲ {{ i.votes }}</span>
      <form method="post" action="{{ url_for('voter_idee', id=i.id) }}"><button class="btn btn-secondary btn-sm" type="submit">+1</button></form>
    </div>
  </div>
  <div style="margin-top:10px;font-size:13px;color:var(--text2)">{{ i.description[:200] }}</div>
  <div style="margin-top:8px">
    {% if i.statut=='soumise' %}<span class="badge b-blue">soumise</span>
    {% elif i.statut=='retenue' %}<span class="badge b-green">retenue</span>
    {% elif i.statut=='en_etude' %}<span class="badge b-amber">en étude</span>
    {% else %}<span class="badge b-gray">{{ i.statut }}</span>{% endif %}
  </div>
</div>
{% else %}<div class="empty">Aucune idée soumise</div>{% endfor %}
</div>
</div>
{% endblock %}'''
    return render_template_string(IDEE_TPL, idees=idees,
        flash_msg=session.pop('flash_msg',None), flash_type=session.pop('flash_type','ok'))

@app.route('/idees/<int:id>/voter', methods=['POST'])
@login_required
def voter_idee(id):
    mutate("UPDATE idee SET votes=votes+1 WHERE id=?", [id])
    return redirect(url_for('boite_idees'))

# ─────────────────────────────────────────────
# SIGNALEMENTS
# ─────────────────────────────────────────────
@app.route('/signalements', methods=['GET','POST'])
@login_required
def signalements():
    if request.method == 'POST':
        f = request.form
        mutate("INSERT INTO signalement(emetteur_id,type,description) VALUES(?,?,?)",
               [session['user_id'], f['type'], f['description']])
        session['flash_msg'] = 'Signalement enregistré.'
        session['flash_type'] = 'ok'
        return redirect(url_for('signalements'))
    rows = query("""SELECT s.*,u.nom||' '||u.prenom as emetteur
                    FROM signalement s JOIN utilisateur u ON u.id=s.emetteur_id
                    ORDER BY s.date_emission DESC""")
    SIG_TPL = BASE + '''
{% block page_title %}Signalements{% endblock %}
{% block content %}
{% if flash_msg %}<div class="flash flash-{{ flash_type }}">{{ flash_msg }}</div>{% endif %}
<div class="grid g2" style="align-items:start">
<div class="card">
  <h3>Nouveau signalement</h3>
  <form method="post">
    <div class="form-group"><label>Type</label>
      <select name="type" required>
        <option value="securite">Sécurité</option>
        <option value="anomalie">Anomalie</option>
        <option value="acces_non_autorise">Accès non autorisé</option>
        <option value="autre">Autre</option>
      </select></div>
    <div class="form-group"><label>Description</label><textarea name="description" required></textarea></div>
    <button class="btn btn-primary" type="submit">Émettre le signalement</button>
  </form>
</div>
<div class="card">
  <h3>Historique</h3>
  <table class="tbl">
    <thead><tr><th>Type</th><th>Émetteur</th><th>Date</th><th>Statut</th></tr></thead>
    <tbody>
    {% for s in rows %}
    <tr>
      <td><span class="chip">{{ s.type }}</span></td>
      <td>{{ s.emetteur }}</td>
      <td style="font-family:var(--mono);font-size:11px">{{ s.date_emission[:10] }}</td>
      <td>{% if s.statut=='ouvert' %}<span class="badge b-amber">ouvert</span>
          {% elif s.statut=='resolu' %}<span class="badge b-green">résolu</span>
          {% else %}<span class="badge b-gray">{{ s.statut }}</span>{% endif %}</td>
    </tr>
    {% else %}<tr><td colspan="4" class="empty">Aucun signalement</td></tr>{% endfor %}
    </tbody>
  </table>
</div>
</div>
{% endblock %}'''
    return render_template_string(SIG_TPL, rows=rows,
        flash_msg=session.pop('flash_msg',None), flash_type=session.pop('flash_type','ok'))

# ─────────────────────────────────────────────
# UTILISATEURS (admin)
# ─────────────────────────────────────────────
@app.route('/utilisateurs')
@login_required
def utilisateurs():
    if session.get('niveau', 0) < 3:
        return redirect(url_for('dashboard'))
    rows = query("""SELECT u.*,s.nom as service_nom FROM utilisateur u
                    LEFT JOIN service s ON s.id=u.service_id ORDER BY u.nom""")
    USR_TPL = BASE + '''{% block page_title %}Gestion des utilisateurs{% endblock %}
{% block content %}
<div class="card">
<table class="tbl">
<thead><tr><th>Nom</th><th>Email</th><th>Service</th><th>Rôle</th><th>Niveau</th><th>Actif</th></tr></thead>
<tbody>
{% for u in rows %}
<tr>
  <td style="font-weight:600">{{ u.prenom }} {{ u.nom }}</td>
  <td style="font-family:var(--mono);font-size:12px;color:var(--text2)">{{ u.email }}</td>
  <td>{{ u.service_nom or '—' }}</td>
  <td><span class="chip">{{ u.role }}</span></td>
  <td style="font-family:var(--mono)">N{{ u.niveau_hierarchique }}</td>
  <td>{% if u.actif %}<span class="badge b-green">✓</span>{% else %}<span class="badge b-red">✗</span>{% endif %}</td>
</tr>
{% endfor %}
</tbody>
</table>
</div>{% endblock %}'''
    return render_template_string(USR_TPL, rows=rows)

# ─────────────────────────────────────────────
# LANCEMENT
# ─────────────────────────────────────────────
if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True, port=5000)
