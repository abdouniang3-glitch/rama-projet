# ============================================================
#  RAMA — Vue Agent (N)
#  Application Flask complète — Google Colab ready
#  Auteur : Projet L2 Informatique | Prof. Papa DIOP 2025-2026
# ============================================================
#
#  INSTRUCTIONS COLAB :
#  1. Coller ce fichier dans une cellule
#  2. Exécuter : !pip install flask flask-login werkzeug
#  3. Lancer dans une 2e cellule :
#       from pyngrok import ngrok
#       !ngrok authtoken VOTRE_TOKEN
#       public_url = ngrok.connect(5000)
#       print(public_url)
#       app.run()
#
# ============================================================

from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import sqlite3, os, functools

app = Flask(__name__)
app.secret_key = "rama_secret_key_2026"
DB = "rama.db"

# ─────────────────────────────────────────
# INITIALISATION BASE DE DONNÉES (SQLite)
# ─────────────────────────────────────────
def get_db():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS service (
        id_service   INTEGER PRIMARY KEY AUTOINCREMENT,
        libelle      TEXT NOT NULL,
        description  TEXT
    );
    CREATE TABLE IF NOT EXISTS utilisateur (
        id_utilisateur INTEGER PRIMARY KEY AUTOINCREMENT,
        nom            TEXT NOT NULL,
        prenom         TEXT NOT NULL,
        email          TEXT NOT NULL UNIQUE,
        mot_de_passe   TEXT NOT NULL,
        role           TEXT NOT NULL CHECK(role IN ('DG','DIRECTEUR','CHEF_SERVICE','RESPONSABLE','AGENT')),
        id_superieur   INTEGER REFERENCES utilisateur(id_utilisateur),
        id_service     INTEGER REFERENCES service(id_service),
        actif          INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS activite (
        id_activite     INTEGER PRIMARY KEY AUTOINCREMENT,
        titre           TEXT NOT NULL,
        type            TEXT NOT NULL,
        date_debut      TEXT NOT NULL,
        date_fin_prevue TEXT NOT NULL,
        date_fin_reelle TEXT,
        statut          TEXT DEFAULT 'PLANIFIEE',
        id_service      INTEGER REFERENCES service(id_service),
        id_createur     INTEGER REFERENCES utilisateur(id_utilisateur)
    );
    CREATE TABLE IF NOT EXISTS tache (
        id_tache         INTEGER PRIMARY KEY AUTOINCREMENT,
        libelle          TEXT NOT NULL,
        type_livrable    TEXT NOT NULL,
        description      TEXT,
        echeance_prevue  TEXT NOT NULL,
        echeance_reelle  TEXT,
        statut           TEXT DEFAULT 'EN_ATTENTE',
        id_activite      INTEGER REFERENCES activite(id_activite),
        id_assigne_par   INTEGER REFERENCES utilisateur(id_utilisateur),
        id_assigne_a     INTEGER REFERENCES utilisateur(id_utilisateur),
        date_assignation TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS livrable (
        id_livrable       INTEGER PRIMARY KEY AUTOINCREMENT,
        id_tache          INTEGER REFERENCES tache(id_tache),
        fichier_nom       TEXT NOT NULL,
        commentaire       TEXT,
        date_soumission   TEXT DEFAULT (datetime('now')),
        statut_validation TEXT DEFAULT 'EN_ATTENTE',
        id_validateur     INTEGER REFERENCES utilisateur(id_utilisateur),
        motif_rejet       TEXT
    );
    CREATE TABLE IF NOT EXISTS historique_tache (
        id_historique        INTEGER PRIMARY KEY AUTOINCREMENT,
        id_tache             INTEGER REFERENCES tache(id_tache),
        type_action          TEXT NOT NULL,
        id_utilisateur_avant INTEGER,
        id_utilisateur_apres INTEGER,
        statut_avant         TEXT,
        statut_apres         TEXT,
        motif                TEXT,
        effectue_par         INTEGER REFERENCES utilisateur(id_utilisateur),
        date_action          TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS idee (
        id_idee         INTEGER PRIMARY KEY AUTOINCREMENT,
        id_auteur       INTEGER REFERENCES utilisateur(id_utilisateur),
        titre           TEXT NOT NULL,
        contenu         TEXT NOT NULL,
        nb_votes        INTEGER DEFAULT 0,
        statut          TEXT DEFAULT 'SOUMISE',
        date_soumission TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS avis (
        id_avis         INTEGER PRIMARY KEY AUTOINCREMENT,
        id_auteur       INTEGER REFERENCES utilisateur(id_utilisateur),
        type            TEXT NOT NULL,
        cible           TEXT,
        contenu         TEXT NOT NULL,
        statut          TEXT DEFAULT 'SOUMIS',
        date_soumission TEXT DEFAULT (datetime('now'))
    );
    """)

    # Données de démonstration
    existing = db.execute("SELECT COUNT(*) FROM utilisateur").fetchone()[0]
    if existing == 0:
        db.execute("INSERT INTO service (libelle) VALUES ('Direction administrative')")
        db.execute("INSERT INTO service (libelle) VALUES ('Direction technique')")
        db.executemany(
            "INSERT INTO utilisateur (nom,prenom,email,mot_de_passe,role,id_superieur,id_service) VALUES (?,?,?,?,?,?,?)",
            [
                ("DIOP","Amadou","dg@rama.sn",       generate_password_hash("admin"), "DG",          None, None),
                ("SARR","Fatou", "dir@rama.sn",       generate_password_hash("admin"), "DIRECTEUR",   1,    1),
                ("FALL","Khady", "chef@rama.sn",      generate_password_hash("admin"), "CHEF_SERVICE",2,    1),
                ("BA",  "Ibou",  "resp@rama.sn",      generate_password_hash("admin"), "RESPONSABLE", 3,    1),
                ("KANE","Aissa", "agent@rama.sn",     generate_password_hash("admin"), "AGENT",       4,    1),
                ("NDIAYE","Moussa","agent2@rama.sn",  generate_password_hash("admin"), "AGENT",       4,    1),
            ]
        )
        db.execute("""INSERT INTO activite (titre,type,date_debut,date_fin_prevue,statut,id_service,id_createur)
                      VALUES ('Atelier national RAMA 2026','ATELIER','2026-04-01','2026-04-30','EN_COURS',1,2)""")
        db.execute("""INSERT INTO activite (titre,type,date_debut,date_fin_prevue,statut,id_service,id_createur)
                      VALUES ('Séminaire de coordination','SEMINAIRE','2026-04-15','2026-05-15','PLANIFIEE',1,2)""")
        db.executemany(
            "INSERT INTO tache (libelle,type_livrable,description,echeance_prevue,statut,id_activite,id_assigne_par,id_assigne_a) VALUES (?,?,?,?,?,?,?,?)",
            [
                ("Rédiger les termes de référence","TERMES_REFERENCE","Document cadre de l'atelier","2026-04-10","VALIDE",1,4,5),
                ("Préparer la convocation","CONVOCATION","Envoyer aux participants","2026-04-12","EN_COURS",1,4,5),
                ("Produire le rapport final","RAPPORT","Rapport de restitution","2026-04-28","EN_ATTENTE",1,4,5),
                ("Rédiger la fiche technique","FICHE_TECHNIQUE","Fiche de présentation","2026-04-20","EN_RETARD",2,4,5),
            ]
        )
        db.execute("""INSERT INTO livrable (id_tache,fichier_nom,commentaire,statut_validation)
                      VALUES (1,'termes_ref_v1.pdf','Version finale validée','VALIDE')""")
    db.commit()
    db.close()

# ─────────────────────────────────────────
# DECORATEUR AUTH
# ─────────────────────────────────────────
def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def agent_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "AGENT":
            flash("Accès réservé aux agents.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def ecart_jours(prevue, reelle=None):
    try:
        dp = datetime.strptime(prevue, "%Y-%m-%d").date()
        dr = datetime.strptime(reelle, "%Y-%m-%d").date() if reelle else date.today()
        return (dr - dp).days
    except:
        return None

def statut_badge(statut):
    m = {
        "EN_ATTENTE":  ("badge-waiting",  "En attente"),
        "EN_COURS":    ("badge-progress", "En cours"),
        "LIVRE":       ("badge-delivered","Livré"),
        "VALIDE":      ("badge-done",     "Validé"),
        "REJETE":      ("badge-reject",   "Rejeté"),
        "EN_RETARD":   ("badge-late",     "En retard"),
    }
    return m.get(statut, ("badge-waiting", statut))

# ─────────────────────────────────────────
# HTML TEMPLATE (design Sénégal / admin gov)
# ─────────────────────────────────────────
BASE_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RAMA — {% block title %}{% endblock %}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=Syne:wght@600;700&display=swap" rel="stylesheet">
<style>
:root {
  --brand:   #1B3A6B;
  --accent:  #E8A020;
  --bg:      #F4F6FA;
  --surface: #FFFFFF;
  --border:  #E2E8F0;
  --text:    #1A2332;
  --muted:   #64748B;
  --success: #16A34A;
  --warning: #D97706;
  --danger:  #DC2626;
  --info:    #2563EB;
  --radius:  10px;
}
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family:'DM Sans',sans-serif; background:var(--bg); color:var(--text); min-height:100vh; }
a { color:inherit; text-decoration:none; }

/* LAYOUT */
.shell { display:flex; min-height:100vh; }
.sidebar {
  width:240px; flex-shrink:0; background:var(--brand);
  display:flex; flex-direction:column;
  padding:0 0 24px;
}
.sidebar-logo {
  padding:28px 24px 20px;
  border-bottom:1px solid rgba(255,255,255,.12);
  margin-bottom:16px;
}
.sidebar-logo .app-name {
  font-family:'Syne',sans-serif; font-size:22px;
  color:#fff; letter-spacing:.02em;
}
.sidebar-logo .app-sub {
  font-size:11px; color:rgba(255,255,255,.5);
  margin-top:2px; letter-spacing:.04em;
}
.nav-section { padding:0 12px; margin-bottom:4px; }
.nav-label { font-size:10px; color:rgba(255,255,255,.4); letter-spacing:.1em; padding:8px 12px 4px; text-transform:uppercase; }
.nav-item {
  display:flex; align-items:center; gap:10px;
  padding:9px 12px; border-radius:8px;
  font-size:14px; color:rgba(255,255,255,.75);
  cursor:pointer; transition:all .15s;
  margin-bottom:2px;
}
.nav-item:hover { background:rgba(255,255,255,.1); color:#fff; }
.nav-item.active { background:var(--accent); color:#fff; font-weight:500; }
.nav-item .icon { width:18px; text-align:center; font-size:15px; flex-shrink:0; }
.sidebar-user {
  margin-top:auto; padding:16px 24px;
  border-top:1px solid rgba(255,255,255,.12);
}
.user-avatar {
  width:36px; height:36px; border-radius:50%;
  background:var(--accent); display:flex;
  align-items:center; justify-content:center;
  font-size:13px; font-weight:600; color:#fff; flex-shrink:0;
}
.user-info { flex:1; min-width:0; }
.user-name { font-size:13px; font-weight:500; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.user-role { font-size:11px; color:rgba(255,255,255,.5); }

.main { flex:1; display:flex; flex-direction:column; min-width:0; }
.topbar {
  background:var(--surface); border-bottom:1px solid var(--border);
  padding:0 32px; height:60px; display:flex; align-items:center;
  justify-content:space-between; flex-shrink:0;
}
.page-title { font-family:'Syne',sans-serif; font-size:18px; font-weight:700; }
.content { padding:28px 32px; flex:1; }

/* CARDS */
.card {
  background:var(--surface); border:1px solid var(--border);
  border-radius:var(--radius); padding:20px 24px; margin-bottom:20px;
}
.card-title { font-family:'Syne',sans-serif; font-size:15px; font-weight:700; margin-bottom:16px; }
.kpi-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:24px; }
.kpi {
  background:var(--surface); border:1px solid var(--border);
  border-radius:var(--radius); padding:16px 20px;
}
.kpi-label { font-size:12px; color:var(--muted); margin-bottom:6px; }
.kpi-val { font-size:26px; font-weight:600; }
.kpi-sub { font-size:11px; color:var(--muted); margin-top:3px; }

/* BADGES */
.badge { display:inline-flex; align-items:center; gap:5px; font-size:12px; font-weight:500; padding:3px 10px; border-radius:20px; }
.badge::before { content:''; width:6px; height:6px; border-radius:50%; background:currentColor; opacity:.7; }
.badge-waiting  { background:#F1F5F9; color:#475569; }
.badge-progress { background:#EFF6FF; color:#1D4ED8; }
.badge-delivered{ background:#FEF9C3; color:#854D0E; }
.badge-done     { background:#F0FDF4; color:#15803D; }
.badge-reject   { background:#FEF2F2; color:#B91C1C; }
.badge-late     { background:#FFF7ED; color:#C2410C; }

/* TABLE */
.tbl { width:100%; border-collapse:collapse; font-size:14px; }
.tbl th { font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); font-weight:500; padding:10px 12px; border-bottom:2px solid var(--border); text-align:left; }
.tbl td { padding:12px 12px; border-bottom:1px solid var(--border); vertical-align:middle; }
.tbl tr:last-child td { border-bottom:none; }
.tbl tr:hover td { background:#F8FAFC; }

/* FORMS */
.form-group { margin-bottom:16px; }
.form-label { display:block; font-size:13px; font-weight:500; margin-bottom:5px; }
.form-control {
  width:100%; padding:9px 12px; border:1px solid var(--border);
  border-radius:8px; font-size:14px; font-family:inherit;
  background:var(--surface); color:var(--text);
  transition:border-color .15s;
}
.form-control:focus { outline:none; border-color:var(--brand); box-shadow:0 0 0 3px rgba(27,58,107,.1); }
textarea.form-control { resize:vertical; min-height:80px; }
.btn {
  display:inline-flex; align-items:center; gap:7px;
  padding:9px 18px; border-radius:8px; border:none;
  font-size:14px; font-weight:500; font-family:inherit;
  cursor:pointer; transition:all .15s;
}
.btn-primary { background:var(--brand); color:#fff; }
.btn-primary:hover { background:#152E56; }
.btn-accent  { background:var(--accent); color:#fff; }
.btn-accent:hover { background:#C9871A; }
.btn-ghost   { background:transparent; border:1px solid var(--border); color:var(--text); }
.btn-ghost:hover { background:var(--bg); }
.btn-sm { padding:5px 12px; font-size:13px; }
.btn-danger { background:#FEF2F2; color:var(--danger); border:1px solid #FECACA; }

/* ALERTS */
.alert { padding:12px 16px; border-radius:8px; font-size:14px; margin-bottom:16px; display:flex; align-items:center; gap:8px; }
.alert-success { background:#F0FDF4; color:#166534; border:1px solid #BBF7D0; }
.alert-danger  { background:#FEF2F2; color:#991B1B; border:1px solid #FECACA; }
.alert-info    { background:#EFF6FF; color:#1E40AF; border:1px solid #BFDBFE; }
.alert-warning { background:#FFFBEB; color:#92400E; border:1px solid #FDE68A; }

/* GANTT mini */
.gantt-bar-wrap { height:8px; background:#F1F5F9; border-radius:4px; overflow:hidden; }
.gantt-bar { height:100%; border-radius:4px; }

/* PROGRESS RING */
.score-ring { position:relative; display:inline-flex; }
.score-ring svg { transform:rotate(-90deg); }
.score-center { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; font-size:14px; font-weight:600; }

/* TIMELINE */
.timeline { position:relative; padding-left:20px; }
.timeline::before { content:''; position:absolute; left:6px; top:0; bottom:0; width:1px; background:var(--border); }
.tl-item { position:relative; padding:0 0 16px 20px; }
.tl-dot { position:absolute; left:-8px; top:4px; width:12px; height:12px; border-radius:50%; border:2px solid var(--surface); }
.tl-date { font-size:11px; color:var(--muted); margin-bottom:3px; }
.tl-text { font-size:13px; }

/* LOGIN */
.login-wrap { min-height:100vh; display:flex; align-items:center; justify-content:center; background:var(--brand); }
.login-card { background:var(--surface); border-radius:16px; padding:40px 36px; width:380px; }
.login-logo { font-family:'Syne',sans-serif; font-size:32px; font-weight:700; color:var(--brand); text-align:center; margin-bottom:4px; }
.login-sub  { font-size:13px; color:var(--muted); text-align:center; margin-bottom:28px; }

/* UTILS */
.flex { display:flex; }
.gap-2 { gap:8px; }
.gap-3 { gap:12px; }
.items-center { align-items:center; }
.justify-between { justify-content:space-between; }
.mt-1 { margin-top:4px; }
.mt-2 { margin-top:8px; }
.mb-4 { margin-bottom:16px; }
.text-muted { color:var(--muted); font-size:13px; }
.text-sm { font-size:13px; }
.fw-500 { font-weight:500; }
.w-full { width:100%; }
.grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
.pill { display:inline-block; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:500; }
</style>
</head>
<body>
{% with msgs = get_flashed_messages(with_categories=true) %}
  {% if msgs %}
    <div style="position:fixed;top:16px;right:16px;z-index:999;max-width:340px">
    {% for cat, msg in msgs %}
      <div class="alert alert-{{cat}}" style="margin-bottom:8px;box-shadow:0 4px 12px rgba(0,0,0,.1)">{{msg}}</div>
    {% endfor %}
    </div>
  {% endif %}
{% endwith %}
{% block body %}{% endblock %}
</body>
</html>"""

SIDEBAR_HTML = """
<div class="shell">
<aside class="sidebar">
  <div class="sidebar-logo">
    <div class="app-name">RAMA</div>
    <div class="app-sub">Reporting &amp; Monitoring</div>
  </div>
  <div class="nav-section">
    <div class="nav-label">Navigation</div>
    <a href="{{ url_for('dashboard') }}" class="nav-item {% if active=='dashboard' %}active{% endif %}">
      <span class="icon">&#9632;</span> Tableau de bord
    </a>
    <a href="{{ url_for('mes_taches') }}" class="nav-item {% if active=='taches' %}active{% endif %}">
      <span class="icon">&#10003;</span> Mes tâches
    </a>
    <a href="{{ url_for('mon_historique') }}" class="nav-item {% if active=='historique' %}active{% endif %}">
      <span class="icon">&#9677;</span> Mon historique
    </a>
  </div>
  <div class="nav-section">
    <div class="nav-label">Collaboration</div>
    <a href="{{ url_for('boite_idees') }}" class="nav-item {% if active=='idees' %}active{% endif %}">
      <span class="icon">&#9728;</span> Boîte à idées
    </a>
    <a href="{{ url_for('mes_avis') }}" class="nav-item {% if active=='avis' %}active{% endif %}">
      <span class="icon">&#9993;</span> Avis &amp; signalements
    </a>
  </div>
  <div class="sidebar-user">
    <div class="flex items-center gap-2">
      <div class="user-avatar">{{ session.prenom[0] }}{{ session.nom[0] }}</div>
      <div class="user-info">
        <div class="user-name">{{ session.prenom }} {{ session.nom }}</div>
        <div class="user-role">Agent · {{ session.service }}</div>
      </div>
      <a href="{{ url_for('logout') }}" title="Déconnexion" style="color:rgba(255,255,255,.4);font-size:16px;margin-left:4px">&#10005;</a>
    </div>
  </div>
</aside>
<main class="main">
"""

# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

# LOGIN
LOGIN_TPL = BASE_HTML.replace("{% block body %}{% endblock %}", """
{% block body %}
<div class="login-wrap">
  <div class="login-card">
    <div class="login-logo">RAMA</div>
    <div class="login-sub">Connexion à votre espace agent</div>
    {% with msgs = get_flashed_messages(with_categories=true) %}
      {% for cat, msg in msgs %}<div class="alert alert-{{cat}}">{{msg}}</div>{% endfor %}
    {% endwith %}
    <form method="POST" action="/login">
      <div class="form-group">
        <label class="form-label">Adresse e-mail</label>
        <input type="email" name="email" class="form-control" placeholder="prenom@rama.sn" required>
      </div>
      <div class="form-group">
        <label class="form-label">Mot de passe</label>
        <input type="password" name="password" class="form-control" required>
      </div>
      <button type="submit" class="btn btn-primary w-full" style="justify-content:center;margin-top:8px">
        Se connecter
      </button>
    </form>
    <p class="text-muted" style="text-align:center;margin-top:20px;font-size:12px">
      Démo : agent@rama.sn / admin
    </p>
  </div>
</div>
{% endblock %}
""")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        pwd   = request.form["password"]
        db = get_db()
        user = db.execute(
            "SELECT u.*,s.libelle as svc FROM utilisateur u LEFT JOIN service s ON s.id_service=u.id_service WHERE u.email=? AND u.actif=1",
            (email,)
        ).fetchone()
        db.close()
        if user and check_password_hash(user["mot_de_passe"], pwd):
            session.clear()
            session["user_id"] = user["id_utilisateur"]
            session["nom"]     = user["nom"]
            session["prenom"]  = user["prenom"]
            session["role"]    = user["role"]
            session["service"] = user["svc"] or "—"
            return redirect(url_for("dashboard"))
        flash("Email ou mot de passe incorrect.", "danger")
    return render_template_string(LOGIN_TPL)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    uid = session["user_id"]
    db  = get_db()
    taches = db.execute(
        "SELECT * FROM tache WHERE id_assigne_a=?", (uid,)
    ).fetchall()
    total    = len(taches)
    actives  = sum(1 for t in taches if t["statut"] in ("EN_ATTENTE","EN_COURS","EN_RETARD"))
    validees = sum(1 for t in taches if t["statut"] == "VALIDE")
    retard   = sum(1 for t in taches if t["statut"] == "EN_RETARD" or
                   (t["statut"] not in ("VALIDE","ANNULEE") and t["echeance_prevue"] < str(date.today())))
    score    = round(100 * validees / total) if total else 0

    taches_recentes = db.execute("""
        SELECT t.*, a.titre as act_titre, a.type as act_type,
               u.nom as sup_nom, u.prenom as sup_prenom
        FROM tache t
        JOIN activite a ON a.id_activite = t.id_activite
        JOIN utilisateur u ON u.id_utilisateur = t.id_assigne_par
        WHERE t.id_assigne_a=?
        ORDER BY t.date_assignation DESC LIMIT 5
    """, (uid,)).fetchall()

    idees_recentes = db.execute(
        "SELECT * FROM idee ORDER BY date_soumission DESC LIMIT 3"
    ).fetchall()
    db.close()

    tpl = BASE_HTML.replace("{% block title %}{% endblock %}", "Tableau de bord")
    tpl = tpl.replace("{% block body %}{% endblock %}", SIDEBAR_HTML + DASHBOARD_CONTENT + "</main></div>")
    return render_template_string(tpl,
        active="dashboard", total=total, actives=actives,
        validees=validees, retard=retard, score=score,
        taches=taches_recentes, idees=idees_recentes,
        ecart_jours=ecart_jours, statut_badge=statut_badge)

DASHBOARD_CONTENT = """
<div class="topbar">
  <div class="page-title">Tableau de bord</div>
  <div class="flex items-center gap-2">
    <span class="text-muted text-sm">{{ session.prenom }} {{ session.nom }}</span>
    <span class="pill" style="background:#EFF6FF;color:#1E40AF">Agent</span>
  </div>
</div>
<div class="content">
  <div class="kpi-grid">
    <div class="kpi">
      <div class="kpi-label">Tâches actives</div>
      <div class="kpi-val" style="color:#1B3A6B">{{ actives }}</div>
      <div class="kpi-sub">en cours ou en attente</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Validées ce mois</div>
      <div class="kpi-val" style="color:#16A34A">{{ validees }}</div>
      <div class="kpi-sub">sur {{ total }} assignées</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">En retard</div>
      <div class="kpi-val" style="color:#DC2626">{{ retard }}</div>
      <div class="kpi-sub">délai dépassé</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Mon score</div>
      <div class="kpi-val" style="color:#D97706">{{ score }}%</div>
      <div class="kpi-sub">respect des délais</div>
    </div>
  </div>

  <div class="card">
    <div class="flex items-center justify-between mb-4">
      <div class="card-title" style="margin:0">Tâches récentes</div>
      <a href="/taches" class="btn btn-ghost btn-sm">Voir tout</a>
    </div>
    <table class="tbl">
      <thead><tr>
        <th>Tâche</th><th>Activité</th><th>Assignée par</th>
        <th>Échéance</th><th>Statut</th><th>Action</th>
      </tr></thead>
      <tbody>
      {% for t in taches %}
        {% set badge = statut_badge(t.statut) %}
        {% set ecart = ecart_jours(t.echeance_prevue, t.echeance_reelle) %}
        <tr>
          <td class="fw-500">{{ t.libelle }}</td>
          <td class="text-muted">{{ t.act_titre }}</td>
          <td>{{ t.sup_prenom }} {{ t.sup_nom }}</td>
          <td>
            {{ t.echeance_prevue }}
            {% if ecart and ecart > 0 and t.statut not in ('VALIDE',) %}
              <span style="color:#DC2626;font-size:11px"> +{{ ecart }}j</span>
            {% endif %}
          </td>
          <td><span class="badge {{ badge[0] }}">{{ badge[1] }}</span></td>
          <td>
            <a href="/taches/{{ t.id_tache }}" class="btn btn-ghost btn-sm">Détail</a>
          </td>
        </tr>
      {% else %}
        <tr><td colspan="6" style="text-align:center;color:var(--muted);padding:24px">Aucune tâche assignée.</td></tr>
      {% endfor %}
      </tbody>
    </table>
  </div>

  <div class="card">
    <div class="card-title">Idées récentes de la structure</div>
    {% for idee in idees %}
    <div style="padding:10px 0;border-top:1px solid var(--border);display:flex;align-items:center;gap:12px">
      <div style="flex:1">
        <div class="fw-500 text-sm">{{ idee.titre }}</div>
        <div class="text-muted" style="font-size:12px;margin-top:2px">{{ idee.date_soumission[:10] }}</div>
      </div>
      <span class="pill" style="background:#F0FDF4;color:#166534">{{ idee.nb_votes }} votes</span>
    </div>
    {% endfor %}
    <a href="/idees" class="btn btn-ghost btn-sm" style="margin-top:12px">Voir la boîte à idées</a>
  </div>
</div>
"""

# MES TÂCHES
@app.route("/taches")
@login_required
def mes_taches():
    uid  = session["user_id"]
    filtre = request.args.get("statut", "")
    db   = get_db()
    q = """SELECT t.*, a.titre as act_titre, a.type as act_type,
                  u.nom as sup_nom, u.prenom as sup_prenom
           FROM tache t
           JOIN activite a ON a.id_activite = t.id_activite
           JOIN utilisateur u ON u.id_utilisateur = t.id_assigne_par
           WHERE t.id_assigne_a=?"""
    params = [uid]
    if filtre:
        q += " AND t.statut=?"
        params.append(filtre)
    q += " ORDER BY t.echeance_prevue ASC"
    taches = db.execute(q, params).fetchall()
    db.close()

    tpl = BASE_HTML.replace("{% block title %}{% endblock %}", "Mes tâches")
    tpl = tpl.replace("{% block body %}{% endblock %}", SIDEBAR_HTML + TACHES_CONTENT + "</main></div>")
    return render_template_string(tpl, active="taches", taches=taches,
        filtre=filtre, ecart_jours=ecart_jours, statut_badge=statut_badge)

TACHES_CONTENT = """
<div class="topbar">
  <div class="page-title">Mes tâches</div>
  <div class="flex gap-2">
    {% for s, label in [('','Toutes'),('EN_ATTENTE','En attente'),('EN_COURS','En cours'),('EN_RETARD','En retard'),('VALIDE','Validées')] %}
      <a href="/taches?statut={{ s }}" class="btn btn-ghost btn-sm {% if filtre==s %}btn-primary{% endif %}">{{ label }}</a>
    {% endfor %}
  </div>
</div>
<div class="content">
  <div class="card">
    <table class="tbl">
      <thead><tr>
        <th>Libellé</th><th>Type livrable</th><th>Activité</th>
        <th>Assignée par</th><th>Échéance</th><th>Écart</th>
        <th>Statut</th><th>Actions</th>
      </tr></thead>
      <tbody>
      {% for t in taches %}
        {% set badge = statut_badge(t.statut) %}
        {% set ecart = ecart_jours(t.echeance_prevue, t.echeance_reelle) %}
        <tr>
          <td class="fw-500">{{ t.libelle }}</td>
          <td class="text-muted text-sm">{{ t.type_livrable.replace('_',' ') }}</td>
          <td>{{ t.act_titre }}</td>
          <td>{{ t.sup_prenom }} {{ t.sup_nom }}</td>
          <td>{{ t.echeance_prevue }}</td>
          <td>
            {% if ecart is not none %}
              {% if ecart > 0 %}
                <span style="color:#DC2626;font-size:12px">+{{ ecart }}j</span>
              {% elif ecart == 0 %}
                <span style="color:#D97706;font-size:12px">Auj.</span>
              {% else %}
                <span style="color:#16A34A;font-size:12px">{{ ecart|abs }}j restants</span>
              {% endif %}
            {% endif %}
          </td>
          <td><span class="badge {{ badge[0] }}">{{ badge[1] }}</span></td>
          <td>
            <a href="/taches/{{ t.id_tache }}" class="btn btn-ghost btn-sm">Détail</a>
          </td>
        </tr>
      {% else %}
        <tr><td colspan="8" style="text-align:center;color:var(--muted);padding:24px">Aucune tâche.</td></tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</div>
"""

# DÉTAIL + MISE À JOUR TÂCHE
@app.route("/taches/<int:tid>", methods=["GET","POST"])
@login_required
def tache_detail(tid):
    uid = session["user_id"]
    db  = get_db()
    t = db.execute("""
        SELECT t.*, a.titre as act_titre, a.type as act_type,
               u.nom as sup_nom, u.prenom as sup_prenom
        FROM tache t
        JOIN activite a ON a.id_activite=t.id_activite
        JOIN utilisateur u ON u.id_utilisateur=t.id_assigne_par
        WHERE t.id_tache=? AND t.id_assigne_a=?
    """, (tid, uid)).fetchone()
    if not t:
        db.close()
        flash("Tâche introuvable.", "danger")
        return redirect(url_for("mes_taches"))

    if request.method == "POST":
        action = request.form.get("action")
        if action == "update_statut":
            new_statut = request.form["statut"]
            old_statut = t["statut"]
            reelle = str(date.today()) if new_statut == "LIVRE" else t["echeance_reelle"]
            db.execute("UPDATE tache SET statut=?, echeance_reelle=? WHERE id_tache=?",
                       (new_statut, reelle, tid))
            db.execute("""INSERT INTO historique_tache
                (id_tache,type_action,statut_avant,statut_apres,effectue_par)
                VALUES (?,?,?,?,?)""",
                (tid, "CHANGEMENT_STATUT", old_statut, new_statut, uid))
            db.commit()
            flash("Statut mis à jour.", "success")

        elif action == "soumettre_livrable":
            fichier = request.form.get("fichier_nom","").strip()
            commentaire = request.form.get("commentaire","").strip()
            if fichier:
                db.execute("""INSERT INTO livrable (id_tache,fichier_nom,commentaire)
                              VALUES (?,?,?)""", (tid, fichier, commentaire))
                db.execute("UPDATE tache SET statut='LIVRE', echeance_reelle=? WHERE id_tache=?",
                           (str(date.today()), tid))
                db.execute("""INSERT INTO historique_tache
                    (id_tache,type_action,statut_avant,statut_apres,effectue_par)
                    VALUES (?,?,?,?,?)""",
                    (tid, "CHANGEMENT_STATUT", t["statut"], "LIVRE", uid))
                db.commit()
                flash("Livrable soumis avec succès.", "success")
            else:
                flash("Nom du fichier requis.", "warning")
        db.close()
        return redirect(url_for("tache_detail", tid=tid))

    livrables = db.execute("SELECT * FROM livrable WHERE id_tache=? ORDER BY date_soumission DESC", (tid,)).fetchall()
    histo = db.execute("""
        SELECT h.*, u.nom, u.prenom FROM historique_tache h
        LEFT JOIN utilisateur u ON u.id_utilisateur=h.effectue_par
        WHERE h.id_tache=? ORDER BY h.date_action DESC
    """, (tid,)).fetchall()
    db.close()

    ecart = ecart_jours(t["echeance_prevue"], t["echeance_reelle"])
    badge = statut_badge(t["statut"])

    tpl = BASE_HTML.replace("{% block title %}{% endblock %}", "Détail tâche")
    tpl = tpl.replace("{% block body %}{% endblock %}", SIDEBAR_HTML + DETAIL_CONTENT + "</main></div>")
    return render_template_string(tpl, active="taches", t=t, livrables=livrables,
        histo=histo, ecart=ecart, badge=badge, statut_badge=statut_badge)

DETAIL_CONTENT = """
<div class="topbar">
  <div class="flex items-center gap-2">
    <a href="/taches" class="btn btn-ghost btn-sm">&larr; Retour</a>
    <div class="page-title">{{ t.libelle }}</div>
  </div>
  <span class="badge {{ badge[0] }}">{{ badge[1] }}</span>
</div>
<div class="content">
  <div class="grid-2" style="gap:20px">
    <div>
      <div class="card">
        <div class="card-title">Informations</div>
        <table style="width:100%;font-size:14px">
          <tr><td style="color:var(--muted);padding:5px 0">Activité</td><td class="fw-500">{{ t.act_titre }}</td></tr>
          <tr><td style="color:var(--muted);padding:5px 0">Type</td><td>{{ t.act_type }}</td></tr>
          <tr><td style="color:var(--muted);padding:5px 0">Livrable</td><td>{{ t.type_livrable.replace('_',' ') }}</td></tr>
          <tr><td style="color:var(--muted);padding:5px 0">Assignée par</td><td>{{ t.sup_prenom }} {{ t.sup_nom }}</td></tr>
          <tr><td style="color:var(--muted);padding:5px 0">Échéance prévue</td><td>{{ t.echeance_prevue }}</td></tr>
          <tr><td style="color:var(--muted);padding:5px 0">Date réelle</td><td>{{ t.echeance_reelle or '—' }}</td></tr>
          <tr><td style="color:var(--muted);padding:5px 0">Écart</td>
            <td>{% if ecart is not none %}
              <span style="color:{% if ecart>0 %}#DC2626{% elif ecart<0 %}#16A34A{% else %}#D97706{% endif %}">
                {% if ecart>0 %}+{{ ecart }}j retard{% elif ecart<0 %}{{ ecart|abs }}j avant{% else %}Dans les temps{% endif %}
              </span>
            {% else %}—{% endif %}</td>
          </tr>
        </table>
        {% if t.description %}
          <div style="margin-top:14px;padding-top:14px;border-top:1px solid var(--border)">
            <div class="text-muted text-sm" style="margin-bottom:4px">Description</div>
            <div style="font-size:14px">{{ t.description }}</div>
          </div>
        {% endif %}
      </div>

      {% if t.statut not in ('VALIDE',) %}
      <div class="card">
        <div class="card-title">Mettre à jour le statut</div>
        <form method="POST">
          <input type="hidden" name="action" value="update_statut">
          <div class="form-group">
            <label class="form-label">Nouveau statut</label>
            <select name="statut" class="form-control">
              {% for s,l in [('EN_ATTENTE','En attente'),('EN_COURS','En cours'),('LIVRE','Livré')] %}
                <option value="{{ s }}" {% if t.statut==s %}selected{% endif %}>{{ l }}</option>
              {% endfor %}
            </select>
          </div>
          <button type="submit" class="btn btn-primary">Mettre à jour</button>
        </form>
      </div>

      <div class="card">
        <div class="card-title">Soumettre un livrable</div>
        <form method="POST">
          <input type="hidden" name="action" value="soumettre_livrable">
          <div class="form-group">
            <label class="form-label">Nom du fichier</label>
            <input type="text" name="fichier_nom" class="form-control" placeholder="rapport_final_v2.pdf">
          </div>
          <div class="form-group">
            <label class="form-label">Commentaire (facultatif)</label>
            <textarea name="commentaire" class="form-control" rows="2"></textarea>
          </div>
          <button type="submit" class="btn btn-accent">Soumettre le livrable</button>
        </form>
      </div>
      {% endif %}
    </div>

    <div>
      <div class="card">
        <div class="card-title">Livrables soumis</div>
        {% for l in livrables %}
          <div style="padding:10px 0;border-top:1px solid var(--border)">
            <div class="flex items-center justify-between">
              <div class="fw-500 text-sm">{{ l.fichier_nom }}</div>
              {% set bv = statut_badge(l.statut_validation) %}
              <span class="badge {{ bv[0] }}">{{ bv[1] }}</span>
            </div>
            <div class="text-muted" style="font-size:12px;margin-top:2px">{{ l.date_soumission[:16] }}</div>
            {% if l.motif_rejet %}<div style="font-size:12px;color:#DC2626;margin-top:3px">{{ l.motif_rejet }}</div>{% endif %}
          </div>
        {% else %}
          <div class="text-muted text-sm">Aucun livrable soumis.</div>
        {% endfor %}
      </div>

      <div class="card">
        <div class="card-title">Historique</div>
        <div class="timeline">
          {% for h in histo %}
          <div class="tl-item">
            <div class="tl-dot" style="background:var(--brand)"></div>
            <div class="tl-date">{{ h.date_action[:16] }} — {{ h.prenom or '' }} {{ h.nom or '' }}</div>
            <div class="tl-text">
              {{ h.type_action.replace('_',' ') }}
              {% if h.statut_avant and h.statut_apres %}
                : <span style="color:var(--muted)">{{ h.statut_avant }}</span>
                → <span style="color:var(--brand)">{{ h.statut_apres }}</span>
              {% endif %}
              {% if h.motif %}<div style="font-size:12px;color:var(--muted)">{{ h.motif }}</div>{% endif %}
            </div>
          </div>
          {% else %}
          <div class="text-muted text-sm">Aucun historique.</div>
          {% endfor %}
        </div>
      </div>
    </div>
  </div>
</div>
"""

# MON HISTORIQUE
@app.route("/historique")
@login_required
def mon_historique():
    uid = session["user_id"]
    db  = get_db()
    histo = db.execute("""
        SELECT h.*, t.libelle as tache_libelle,
               u.nom as acteur_nom, u.prenom as acteur_prenom
        FROM historique_tache h
        JOIN tache t ON t.id_tache=h.id_tache
        LEFT JOIN utilisateur u ON u.id_utilisateur=h.effectue_par
        WHERE t.id_assigne_a=? OR t.id_assigne_par=?
        ORDER BY h.date_action DESC LIMIT 50
    """, (uid, uid)).fetchall()
    db.close()

    tpl = BASE_HTML.replace("{% block title %}{% endblock %}", "Mon historique")
    tpl = tpl.replace("{% block body %}{% endblock %}", SIDEBAR_HTML + HISTO_CONTENT + "</main></div>")
    return render_template_string(tpl, active="historique", histo=histo)

HISTO_CONTENT = """
<div class="topbar"><div class="page-title">Mon historique de tâches</div></div>
<div class="content">
  <div class="card">
    <div class="timeline">
      {% for h in histo %}
      <div class="tl-item">
        <div class="tl-dot" style="background:var(--brand)"></div>
        <div class="tl-date">{{ h.date_action[:16] }} — {{ h.acteur_prenom or '' }} {{ h.acteur_nom or '' }}</div>
        <div class="tl-text fw-500">{{ h.tache_libelle }}</div>
        <div class="tl-text" style="margin-top:2px">
          {{ h.type_action.replace('_',' ') }}
          {% if h.statut_avant and h.statut_apres %}
            : {{ h.statut_avant }} → {{ h.statut_apres }}
          {% endif %}
        </div>
        {% if h.motif %}<div class="text-muted" style="font-size:12px">{{ h.motif }}</div>{% endif %}
      </div>
      {% else %}
      <div class="text-muted text-sm">Aucune action enregistrée.</div>
      {% endfor %}
    </div>
  </div>
</div>
"""

# BOÎTE À IDÉES
@app.route("/idees", methods=["GET","POST"])
@login_required
def boite_idees():
    uid = session["user_id"]
    db  = get_db()
    if request.method == "POST":
        titre   = request.form["titre"].strip()
        contenu = request.form["contenu"].strip()
        if titre and contenu:
            db.execute("INSERT INTO idee (id_auteur,titre,contenu) VALUES (?,?,?)",
                       (uid, titre, contenu))
            db.commit()
            flash("Idée soumise avec succès !", "success")
        else:
            flash("Titre et contenu requis.", "warning")
        db.close()
        return redirect(url_for("boite_idees"))

    idees = db.execute("""
        SELECT i.*, u.nom, u.prenom FROM idee i
        JOIN utilisateur u ON u.id_utilisateur=i.id_auteur
        ORDER BY i.nb_votes DESC, i.date_soumission DESC
    """).fetchall()
    db.close()

    tpl = BASE_HTML.replace("{% block title %}{% endblock %}", "Boîte à idées")
    tpl = tpl.replace("{% block body %}{% endblock %}", SIDEBAR_HTML + IDEES_CONTENT + "</main></div>")
    return render_template_string(tpl, active="idees", idees=idees)

IDEES_CONTENT = """
<div class="topbar">
  <div class="page-title">Boîte à idées institutionnelle</div>
  <span class="text-muted text-sm">Partagez vos idées avec la direction</span>
</div>
<div class="content">
  <div class="grid-2" style="gap:20px;align-items:start">
    <div>
      <div class="card">
        <div class="card-title">Proposer une idée</div>
        <form method="POST">
          <div class="form-group">
            <label class="form-label">Titre</label>
            <input type="text" name="titre" class="form-control" placeholder="Ex : Ajouter une vue calendrier..." required>
          </div>
          <div class="form-group">
            <label class="form-label">Description détaillée</label>
            <textarea name="contenu" class="form-control" rows="5" placeholder="Décrivez votre idée, son utilité, les bénéfices attendus..." required></textarea>
          </div>
          <button type="submit" class="btn btn-accent">Soumettre l'idée</button>
        </form>
      </div>
    </div>
    <div>
      {% for idee in idees %}
      <div class="card" style="margin-bottom:14px">
        <div class="flex justify-between items-center">
          <div class="fw-500" style="font-size:15px">{{ idee.titre }}</div>
          <div style="display:flex;flex-direction:column;align-items:center">
            <form method="POST" action="/idees/{{ idee.id_idee }}/vote" style="display:inline">
              <button class="btn btn-ghost btn-sm" style="font-size:18px;padding:4px 10px">&#9650;</button>
            </form>
            <span style="font-size:13px;font-weight:600;color:var(--brand)">{{ idee.nb_votes }}</span>
          </div>
        </div>
        <div class="text-muted text-sm" style="margin:6px 0">{{ idee.contenu[:120] }}{% if idee.contenu|length > 120 %}…{% endif %}</div>
        <div style="font-size:11px;color:var(--muted)">{{ idee.prenom }} {{ idee.nom }} · {{ idee.date_soumission[:10] }}</div>
      </div>
      {% else %}
      <div class="text-muted text-sm">Aucune idée soumise pour l'instant.</div>
      {% endfor %}
    </div>
  </div>
</div>
"""

@app.route("/idees/<int:iid>/vote", methods=["POST"])
@login_required
def voter_idee(iid):
    db = get_db()
    db.execute("UPDATE idee SET nb_votes=nb_votes+1 WHERE id_idee=?", (iid,))
    db.commit()
    db.close()
    return redirect(url_for("boite_idees"))

# AVIS & SIGNALEMENTS
@app.route("/avis", methods=["GET","POST"])
@login_required
def mes_avis():
    uid = session["user_id"]
    db  = get_db()
    if request.method == "POST":
        type_avis = request.form["type"]
        cible     = request.form.get("cible","").strip()
        contenu   = request.form["contenu"].strip()
        if contenu:
            db.execute("INSERT INTO avis (id_auteur,type,cible,contenu) VALUES (?,?,?,?)",
                       (uid, type_avis, cible, contenu))
            db.commit()
            flash("Avis soumis avec succès.", "success")
        db.close()
        return redirect(url_for("mes_avis"))

    avis = db.execute("SELECT * FROM avis WHERE id_auteur=? ORDER BY date_soumission DESC", (uid,)).fetchall()
    db.close()

    tpl = BASE_HTML.replace("{% block title %}{% endblock %}", "Avis & signalements")
    tpl = tpl.replace("{% block body %}{% endblock %}", SIDEBAR_HTML + AVIS_CONTENT + "</main></div>")
    return render_template_string(tpl, active="avis", avis=avis)

AVIS_CONTENT = """
<div class="topbar">
  <div class="page-title">Avis &amp; signalements</div>
</div>
<div class="content">
  <div class="grid-2" style="gap:20px;align-items:start">
    <div class="card">
      <div class="card-title">Émettre un avis</div>
      <form method="POST">
        <div class="form-group">
          <label class="form-label">Type</label>
          <select name="type" class="form-control">
            <option value="FONCTIONNALITE">Avis sur une fonctionnalité</option>
            <option value="SIGNALEMENT">Signalement de compromission</option>
            <option value="SUGGESTION">Suggestion</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Module concerné (facultatif)</label>
          <input type="text" name="cible" class="form-control" placeholder="Ex : module_taches, accès, interface...">
        </div>
        <div class="form-group">
          <label class="form-label">Description</label>
          <textarea name="contenu" class="form-control" rows="5" required placeholder="Décrivez précisément..."></textarea>
        </div>
        <button type="submit" class="btn btn-primary">Soumettre</button>
      </form>
    </div>
    <div>
      <div class="card">
        <div class="card-title">Mes avis soumis</div>
        {% for a in avis %}
        <div style="padding:10px 0;border-top:1px solid var(--border)">
          <div class="flex justify-between">
            <span class="pill" style="background:#EFF6FF;color:#1E40AF;font-size:11px">{{ a.type.replace('_',' ') }}</span>
            <span class="text-muted" style="font-size:11px">{{ a.date_soumission[:10] }}</span>
          </div>
          {% if a.cible %}<div class="text-muted text-sm" style="margin-top:4px">{{ a.cible }}</div>{% endif %}
          <div style="font-size:13px;margin-top:4px">{{ a.contenu[:100] }}{% if a.contenu|length>100 %}…{% endif %}</div>
          <div style="font-size:11px;margin-top:4px">
            <span class="pill" style="background:{% if a.statut=='TRAITE' %}#F0FDF4;color:#166534{% else %}#F8FAFC;color:#475569{% endif %}">{{ a.statut }}</span>
          </div>
        </div>
        {% else %}
        <div class="text-muted text-sm">Aucun avis soumis.</div>
        {% endfor %}
      </div>
    </div>
  </div>
</div>
"""

# PROPOSITION À SON N+1 (API JSON simple)
@app.route("/api/proposition", methods=["POST"])
@login_required
def soumettre_proposition():
    uid  = session["user_id"]
    data = request.get_json()
    db   = get_db()
    sup  = db.execute("SELECT id_superieur FROM utilisateur WHERE id_utilisateur=?", (uid,)).fetchone()
    if not sup or not sup["id_superieur"]:
        db.close()
        return jsonify({"ok": False, "msg": "Aucun supérieur hiérarchique trouvé."})
    db.execute("INSERT INTO avis (id_auteur,type,cible,contenu) VALUES (?,?,?,?)",
               (uid, "SUGGESTION", data.get("cible",""), data.get("contenu","")))
    db.commit()
    db.close()
    return jsonify({"ok": True, "msg": "Proposition transmise à votre N+1."})


