# ============================================================
#  RAMA — Vue Responsable (N+1)
#  Application Flask complète — Google Colab ready
#  Auteur : Projet L2 Informatique | Prof. Papa DIOP 2025-2026
# ============================================================
#
#  INSTRUCTIONS COLAB :
#  1. Uploader ce fichier + rama_agent.py dans Colab
#  2. !pip install flask werkzeug pyngrok -q
#  3. Dans une cellule :
#       from pyngrok import ngrok
#       import threading
#       exec(open("rama_responsable.py").read())
#       init_db()
#       t = threading.Thread(target=lambda: app.run(port=5000))
#       t.daemon = True; t.start()
#       print(ngrok.connect(5000))
#
#  Compte démo responsable : resp@rama.sn / admin
# ============================================================

from flask import (Flask, render_template_string, request,
                   redirect, url_for, session, flash, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import sqlite3, functools

app = Flask(__name__)
app.secret_key = "rama_secret_key_2026"
DB = "rama.db"

# ─────────────────────────────────────────
# DB HELPERS
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
        role           TEXT NOT NULL,
        id_superieur   INTEGER REFERENCES utilisateur(id_utilisateur),
        id_service     INTEGER REFERENCES service(id_service),
        actif          INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS activite (
        id_activite     INTEGER PRIMARY KEY AUTOINCREMENT,
        titre           TEXT NOT NULL,
        type            TEXT NOT NULL,
        description     TEXT,
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
        date_validation   TEXT,
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
    CREATE TABLE IF NOT EXISTS notification (
        id_notification INTEGER PRIMARY KEY AUTOINCREMENT,
        id_destinataire INTEGER REFERENCES utilisateur(id_utilisateur),
        type            TEXT NOT NULL,
        message         TEXT NOT NULL,
        lue             INTEGER DEFAULT 0,
        date_envoi      TEXT DEFAULT (datetime('now')),
        id_tache        INTEGER REFERENCES tache(id_tache)
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

    existing = db.execute("SELECT COUNT(*) FROM utilisateur").fetchone()[0]
    if existing == 0:
        db.execute("INSERT INTO service (libelle) VALUES ('Direction administrative')")
        db.execute("INSERT INTO service (libelle) VALUES ('Direction technique')")
        db.executemany(
            "INSERT INTO utilisateur (nom,prenom,email,mot_de_passe,role,id_superieur,id_service) VALUES (?,?,?,?,?,?,?)",
            [
                ("DIOP",  "Amadou",  "dg@rama.sn",      generate_password_hash("admin"), "DG",          None, None),
                ("SARR",  "Fatou",   "dir@rama.sn",      generate_password_hash("admin"), "DIRECTEUR",   1,    1),
                ("FALL",  "Khady",   "chef@rama.sn",     generate_password_hash("admin"), "CHEF_SERVICE",2,    1),
                ("BA",    "Ibou",    "resp@rama.sn",     generate_password_hash("admin"), "RESPONSABLE", 3,    1),
                ("KANE",  "Aissa",   "agent@rama.sn",    generate_password_hash("admin"), "AGENT",       4,    1),
                ("NDIAYE","Moussa",  "agent2@rama.sn",   generate_password_hash("admin"), "AGENT",       4,    1),
                ("SOW",   "Mariama", "agent3@rama.sn",   generate_password_hash("admin"), "AGENT",       4,    2),
            ]
        )
        db.executemany(
            "INSERT INTO activite (titre,type,description,date_debut,date_fin_prevue,statut,id_service,id_createur) VALUES (?,?,?,?,?,?,?,?)",
            [
                ("Atelier national RAMA 2026","ATELIER","Atelier de restitution annuel","2026-04-01","2026-04-30","EN_COURS",1,2),
                ("Séminaire de coordination", "SEMINAIRE","Séminaire inter-directions","2026-04-15","2026-05-15","PLANIFIEE",1,2),
                ("Mission terrain nord",      "MISSION",  "Mission d'évaluation régionale","2026-03-20","2026-04-20","EN_COURS",2,3),
            ]
        )
        db.executemany(
            "INSERT INTO tache (libelle,type_livrable,description,echeance_prevue,statut,id_activite,id_assigne_par,id_assigne_a) VALUES (?,?,?,?,?,?,?,?)",
            [
                ("Rédiger les termes de référence","TERMES_REFERENCE","Document cadre","2026-04-10","VALIDE",   1,4,5),
                ("Préparer la convocation",        "CONVOCATION",     "Invitations","2026-04-12",  "LIVRE",    1,4,5),
                ("Produire le rapport final",      "RAPPORT",         "Restitution","2026-04-28",  "EN_COURS", 1,4,6),
                ("Rédiger la fiche technique",     "FICHE_TECHNIQUE", "Fiche",      "2026-04-20",  "EN_RETARD",2,4,5),
                ("Préparer le compte-rendu",       "COMPTE_RENDU",    "CR mission", "2026-04-18",  "EN_ATTENTE",3,4,7),
            ]
        )
        db.execute("""INSERT INTO livrable (id_tache,fichier_nom,commentaire,statut_validation)
                      VALUES (1,'termes_ref_v1.pdf','Version finale','VALIDE')""")
        db.execute("""INSERT INTO livrable (id_tache,fichier_nom,commentaire,statut_validation)
                      VALUES (2,'convocation_atelier.pdf','Prêt pour validation','EN_ATTENTE')""")
        db.execute("""INSERT INTO historique_tache (id_tache,type_action,statut_avant,statut_apres,effectue_par)
                      VALUES (1,'ASSIGNATION_INITIALE',NULL,'EN_ATTENTE',4)""")
        db.execute("""INSERT INTO historique_tache (id_tache,type_action,statut_avant,statut_apres,effectue_par)
                      VALUES (1,'CHANGEMENT_STATUT','EN_ATTENTE','VALIDE',4)""")
        db.execute("""INSERT INTO notification (id_destinataire,type,message,id_tache)
                      VALUES (4,'VALIDATION','Le livrable TDR a été soumis par Aissa KANE',1)""")
        db.execute("""INSERT INTO notification (id_destinataire,type,message,id_tache)
                      VALUES (4,'RETARD','La tâche fiche technique est en retard de 2 jours',4)""")
        db.execute("INSERT INTO idee (id_auteur,titre,contenu,nb_votes) VALUES (5,'Vue calendrier mensuel','Ajouter un calendrier par service',8)")
        db.execute("INSERT INTO idee (id_auteur,titre,contenu,nb_votes) VALUES (6,'Export PDF Gantt','Exporter le Gantt directement',6)")
    db.commit()
    db.close()

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def login_required(f):
    @functools.wraps(f)
    def d(*a, **kw):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*a, **kw)
    return d

def responsable_required(f):
    @functools.wraps(f)
    def d(*a, **kw):
        if session.get("role") not in ("RESPONSABLE","CHEF_SERVICE","DIRECTEUR","DG"):
            flash("Accès réservé aux responsables.", "danger")
            return redirect(url_for("dashboard"))
        return f(*a, **kw)
    return d

def ecart(prevue, reelle=None):
    try:
        dp = datetime.strptime(prevue, "%Y-%m-%d").date()
        dr = datetime.strptime(reelle, "%Y-%m-%d").date() if reelle else date.today()
        return (dr - dp).days
    except:
        return None

def badge(statut):
    m = {
        "EN_ATTENTE": ("bwait",  "En attente"),
        "EN_COURS":   ("bprog",  "En cours"),
        "LIVRE":      ("bdel",   "Livré"),
        "VALIDE":     ("bdone",  "Validé"),
        "REJETE":     ("brej",   "Rejeté"),
        "EN_RETARD":  ("blate",  "En retard"),
        "PLANIFIEE":  ("bwait",  "Planifiée"),
        "ACHEVEE":    ("bdone",  "Achevée"),
        "ANNULEE":    ("brej",   "Annulée"),
    }
    return m.get(statut, ("bwait", statut))

def notifier(db, destinataire, type_notif, message, id_tache=None):
    db.execute(
        "INSERT INTO notification (id_destinataire,type,message,id_tache) VALUES (?,?,?,?)",
        (destinataire, type_notif, message, id_tache)
    )

# ─────────────────────────────────────────
# DESIGN SYSTEM  (Sénégal gov / admin)
# ─────────────────────────────────────────
CSS = """
:root{
  --brand:#1B3A6B;--accent:#E8A020;--accent2:#2E7D5E;
  --bg:#F0F4F9;--surface:#FFF;--border:#DDE3EE;
  --text:#18243A;--muted:#637089;
  --ok:#16A34A;--warn:#D97706;--err:#DC2626;--info:#2563EB;
  --r:10px;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
a{color:inherit;text-decoration:none}
.shell{display:flex;min-height:100vh}
.sidebar{width:248px;flex-shrink:0;background:var(--brand);display:flex;flex-direction:column;padding-bottom:24px}
.s-logo{padding:26px 22px 18px;border-bottom:1px solid rgba(255,255,255,.1);margin-bottom:12px}
.s-logo .app{font-family:'Syne',sans-serif;font-size:22px;color:#fff;letter-spacing:.02em}
.s-logo .sub{font-size:11px;color:rgba(255,255,255,.45);margin-top:2px;letter-spacing:.05em}
.s-sect{padding:0 10px;margin-bottom:2px}
.s-lbl{font-size:10px;color:rgba(255,255,255,.35);letter-spacing:.1em;padding:8px 12px 4px;text-transform:uppercase}
.nav{display:flex;align-items:center;gap:9px;padding:9px 12px;border-radius:8px;font-size:14px;color:rgba(255,255,255,.7);cursor:pointer;transition:all .15s;margin-bottom:2px}
.nav:hover{background:rgba(255,255,255,.1);color:#fff}
.nav.on{background:var(--accent);color:#fff;font-weight:500}
.nav .ic{width:18px;text-align:center;font-size:14px;flex-shrink:0}
.s-badge{background:var(--err);color:#fff;font-size:10px;font-weight:600;padding:1px 6px;border-radius:10px;margin-left:auto}
.s-user{margin-top:auto;padding:14px 20px;border-top:1px solid rgba(255,255,255,.1)}
.avatar{width:34px;height:34px;border-radius:50%;background:var(--accent);display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;color:#fff;flex-shrink:0}
.u-name{font-size:13px;font-weight:500;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.u-role{font-size:11px;color:rgba(255,255,255,.45)}
.main{flex:1;display:flex;flex-direction:column;min-width:0}
.topbar{background:var(--surface);border-bottom:1px solid var(--border);padding:0 28px;height:58px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.page-h{font-family:'Syne',sans-serif;font-size:17px;font-weight:700}
.content{padding:24px 28px;flex:1}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:18px 22px;margin-bottom:18px}
.card-h{font-family:'Syne',sans-serif;font-size:14px;font-weight:700;margin-bottom:14px}
.kgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:14px 18px}
.kl{font-size:12px;color:var(--muted);margin-bottom:5px}
.kv{font-size:25px;font-weight:600}
.ks{font-size:11px;color:var(--muted);margin-top:3px}
.bwait{background:#F1F5F9;color:#475569}
.bprog{background:#EFF6FF;color:#1D4ED8}
.bdel{background:#FEF9C3;color:#854D0E}
.bdone{background:#F0FDF4;color:#15803D}
.brej{background:#FEF2F2;color:#B91C1C}
.blate{background:#FFF7ED;color:#C2410C}
.badge{display:inline-flex;align-items:center;gap:4px;font-size:12px;font-weight:500;padding:3px 10px;border-radius:20px}
.badge::before{content:'';width:5px;height:5px;border-radius:50%;background:currentColor;opacity:.6}
.tbl{width:100%;border-collapse:collapse;font-size:13px}
.tbl th{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:500;padding:9px 10px;border-bottom:2px solid var(--border);text-align:left}
.tbl td{padding:11px 10px;border-bottom:1px solid var(--border);vertical-align:middle}
.tbl tr:last-child td{border-bottom:none}
.tbl tr:hover td{background:#F8FAFD}
.form-g{margin-bottom:14px}
.lbl{display:block;font-size:13px;font-weight:500;margin-bottom:4px}
.inp{width:100%;padding:8px 11px;border:1px solid var(--border);border-radius:8px;font-size:14px;font-family:inherit;background:var(--surface);color:var(--text);transition:border-color .15s}
.inp:focus{outline:none;border-color:var(--brand);box-shadow:0 0 0 3px rgba(27,58,107,.08)}
textarea.inp{resize:vertical;min-height:72px}
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:8px;border:none;font-size:13px;font-weight:500;font-family:inherit;cursor:pointer;transition:all .15s}
.btn-p{background:var(--brand);color:#fff}.btn-p:hover{background:#152E56}
.btn-a{background:var(--accent);color:#fff}.btn-a:hover{background:#C9871A}
.btn-g{background:transparent;border:1px solid var(--border);color:var(--text)}.btn-g:hover{background:var(--bg)}
.btn-ok{background:#F0FDF4;color:#166534;border:1px solid #BBF7D0}
.btn-err{background:#FEF2F2;color:#B91C1C;border:1px solid #FECACA}
.btn-sm{padding:5px 11px;font-size:12px}
.alert{padding:10px 14px;border-radius:8px;font-size:14px;margin-bottom:14px;display:flex;align-items:center;gap:8px}
.al-ok{background:#F0FDF4;color:#166534;border:1px solid #BBF7D0}
.al-err{background:#FEF2F2;color:#991B1B;border:1px solid #FECACA}
.al-info{background:#EFF6FF;color:#1E40AF;border:1px solid #BFDBFE}
.al-warn{background:#FFFBEB;color:#92400E;border:1px solid #FDE68A}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}
.flex{display:flex}.gap2{gap:8px}.gap3{gap:12px}.ic{align-items:center}.jb{justify-content:space-between}
.muted{color:var(--muted);font-size:13px}.sm{font-size:13px}.fw5{font-weight:500}
.pill{display:inline-block;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:500}
.bar-w{height:7px;background:#EEF2F7;border-radius:4px;overflow:hidden}
.bar-f{height:100%;border-radius:4px}
.tl{position:relative;padding-left:18px}
.tl::before{content:'';position:absolute;left:5px;top:0;bottom:0;width:1px;background:var(--border)}
.tl-i{position:relative;padding:0 0 14px 18px}
.tl-dot{position:absolute;left:-7px;top:4px;width:11px;height:11px;border-radius:50%;border:2px solid var(--surface)}
.tl-d{font-size:11px;color:var(--muted);margin-bottom:2px}
.tl-t{font-size:13px}
.gantt-row{display:flex;align-items:center;gap:8px;padding:5px 0;border-top:1px solid var(--border)}
.gantt-lbl{font-size:12px;color:var(--muted);width:140px;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gantt-track{flex:1;height:12px;background:#EEF2F7;border-radius:3px;overflow:hidden;position:relative}
.gantt-bar{height:100%;border-radius:3px;position:absolute;top:0}
.gantt-pct{font-size:11px;color:var(--muted);width:36px;text-align:right;flex-shrink:0}
.notif-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.modal-bg{background:rgba(15,25,50,.45);display:flex;align-items:center;justify-content:center;min-height:500px;border-radius:var(--r)}
.modal{background:var(--surface);border-radius:var(--r);padding:28px;width:440px;border:1px solid var(--border)}
.modal-h{font-family:'Syne',sans-serif;font-size:16px;font-weight:700;margin-bottom:18px}
.sep{border:none;border-top:1px solid var(--border);margin:14px 0}
"""

BASE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RAMA — {title}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=Syne:wght@600;700&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>
{flashes}
{body}
</body>
</html>"""

def render(title, body, **ctx):
    db = get_db()
    nb_notif = 0
    nb_livrables = 0
    if "user_id" in session:
        nb_notif = db.execute(
            "SELECT COUNT(*) FROM notification WHERE id_destinataire=? AND lue=0",
            (session["user_id"],)
        ).fetchone()[0]
        nb_livrables = db.execute("""
            SELECT COUNT(*) FROM livrable l
            JOIN tache t ON t.id_tache=l.id_tache
            WHERE t.id_assigne_par=? AND l.statut_validation='EN_ATTENTE'
        """, (session["user_id"],)).fetchone()[0]
    db.close()

    flashes_html = ""
    from flask import get_flashed_messages
    msgs = get_flashed_messages(with_categories=True)
    if msgs:
        flashes_html = '<div style="position:fixed;top:16px;right:16px;z-index:999;max-width:340px">'
        for cat, msg in msgs:
            cls = {"success":"al-ok","danger":"al-err","warning":"al-warn","info":"al-info"}.get(cat,"al-info")
            flashes_html += f'<div class="alert {cls}" style="margin-bottom:8px;box-shadow:0 4px 12px rgba(0,0,0,.12)">{msg}</div>'
        flashes_html += '</div>'

    sidebar = f"""
    <div class="shell">
    <aside class="sidebar">
      <div class="s-logo">
        <div class="app">RAMA</div>
        <div class="sub">Reporting &amp; Monitoring</div>
      </div>
      <div class="s-sect">
        <div class="s-lbl">Navigation</div>
        <a href="{url_for('dashboard')}" class="nav {'on' if ctx.get('active')=='dashboard' else ''}">
          <span class="ic">&#9632;</span> Tableau de bord
        </a>
        <a href="{url_for('mes_activites')}" class="nav {'on' if ctx.get('active')=='activites' else ''}">
          <span class="ic">&#9670;</span> Mes activités
        </a>
        <a href="{url_for('assigner_tache')}" class="nav {'on' if ctx.get('active')=='assigner' else ''}">
          <span class="ic">&#43;</span> Assigner une tâche
        </a>
        <a href="{url_for('mes_taches_resp')}" class="nav {'on' if ctx.get('active')=='taches' else ''}">
          <span class="ic">&#9776;</span> Suivi tâches
        </a>
        <a href="{url_for('livrables_a_valider')}" class="nav {'on' if ctx.get('active')=='livrables' else ''}">
          <span class="ic">&#9744;</span> Livrables
          {'<span class="s-badge">'+str(nb_livrables)+'</span>' if nb_livrables > 0 else ''}
        </a>
        <a href="{url_for('gantt_view')}" class="nav {'on' if ctx.get('active')=='gantt' else ''}">
          <span class="ic">&#9641;</span> Gantt
        </a>
      </div>
      <div class="s-sect">
        <div class="s-lbl">Équipe</div>
        <a href="{url_for('productivite_equipe')}" class="nav {'on' if ctx.get('active')=='perf' else ''}">
          <span class="ic">&#9650;</span> Productivité équipe
        </a>
        <a href="{url_for('notifications_view')}" class="nav {'on' if ctx.get('active')=='notifs' else ''}">
          <span class="ic">&#9993;</span> Notifications
          {'<span class="s-badge">'+str(nb_notif)+'</span>' if nb_notif > 0 else ''}
        </a>
      </div>
      <div class="s-user">
        <div class="flex ic gap2">
          <div class="avatar">{session.get('prenom','?')[0]}{session.get('nom','?')[0]}</div>
          <div style="flex:1;min-width:0">
            <div class="u-name">{session.get('prenom','')} {session.get('nom','')}</div>
            <div class="u-role">Responsable · {session.get('service','')}</div>
          </div>
          <a href="{url_for('logout')}" style="color:rgba(255,255,255,.35);font-size:15px">&#10005;</a>
        </div>
      </div>
    </aside>
    <main class="main">
    """
    full_body = sidebar + body + "</main></div>"
    return BASE.format(title=title, css=CSS, flashes=flashes_html, body=full_body)

# ─────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────
LOGIN_HTML = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500&family=Syne:wght@700&display=swap" rel="stylesheet">
<style>{css}
.login-wrap{{min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--brand)}}
.login-card{{background:var(--surface);border-radius:16px;padding:38px 34px;width:370px}}
.login-logo{{font-family:'Syne',sans-serif;font-size:30px;font-weight:700;color:var(--brand);text-align:center;margin-bottom:4px}}
.login-sub{{font-size:13px;color:var(--muted);text-align:center;margin-bottom:26px}}
</style></head><body>
{flashes}
<div class="login-wrap"><div class="login-card">
  <div class="login-logo">RAMA</div>
  <div class="login-sub">Espace Responsable (N+1)</div>
  <form method="POST" action="/login">
    <div class="form-g"><label class="lbl">Email</label>
      <input type="email" name="email" class="inp" placeholder="resp@rama.sn" required></div>
    <div class="form-g"><label class="lbl">Mot de passe</label>
      <input type="password" name="password" class="inp" required></div>
    <button type="submit" class="btn btn-p" style="width:100%;justify-content:center;margin-top:6px">Connexion</button>
  </form>
  <p class="muted" style="text-align:center;margin-top:18px;font-size:12px">Démo : resp@rama.sn / admin</p>
</div></div></body></html>"""

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email, pwd = request.form["email"], request.form["password"]
        db = get_db()
        u = db.execute(
            "SELECT u.*,s.libelle svc FROM utilisateur u LEFT JOIN service s ON s.id_service=u.id_service WHERE u.email=? AND u.actif=1",
            (email,)
        ).fetchone()
        db.close()
        if u and check_password_hash(u["mot_de_passe"], pwd):
            session.clear()
            for k in ("id_utilisateur","nom","prenom","role","id_service","id_superieur"):
                session[k] = u[k]
            session["service"] = u["svc"] or "—"
            session["user_id"] = u["id_utilisateur"]
            return redirect(url_for("dashboard"))
        flash("Identifiants incorrects.", "danger")

    from flask import get_flashed_messages
    msgs = get_flashed_messages(with_categories=True)
    fhtml = "".join(f'<div class="alert al-err" style="max-width:370px;margin:16px auto">{m}</div>' for _, m in msgs)
    return LOGIN_HTML.format(css=CSS, flashes=fhtml)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ─────────────────────────────────────────
# TABLEAU DE BORD
# ─────────────────────────────────────────
@app.route("/")
@login_required
def dashboard():
    uid = session["user_id"]
    db  = get_db()

    taches_all = db.execute(
        "SELECT * FROM tache WHERE id_assigne_par=?", (uid,)
    ).fetchall()
    total    = len(taches_all)
    en_cours = sum(1 for t in taches_all if t["statut"] in ("EN_COURS","EN_ATTENTE"))
    valides  = sum(1 for t in taches_all if t["statut"] == "VALIDE")
    retards  = sum(1 for t in taches_all if t["statut"] == "EN_RETARD" or
                   (t["statut"] not in ("VALIDE","ANNULEE") and t["echeance_prevue"] < str(date.today())))
    a_valider = db.execute("""
        SELECT COUNT(*) FROM livrable l JOIN tache t ON t.id_tache=l.id_tache
        WHERE t.id_assigne_par=? AND l.statut_validation='EN_ATTENTE'
    """, (uid,)).fetchone()[0]

    agents = db.execute("""
        SELECT u.id_utilisateur,u.nom,u.prenom,
               COUNT(t.id_tache) total,
               SUM(t.statut='VALIDE') valides,
               SUM(t.statut='EN_RETARD') retards
        FROM utilisateur u
        LEFT JOIN tache t ON t.id_assigne_a=u.id_utilisateur AND t.id_assigne_par=?
        WHERE u.id_superieur=?
        GROUP BY u.id_utilisateur
    """, (uid, uid)).fetchall()

    taches_urgentes = db.execute("""
        SELECT t.*, u.nom a_nom, u.prenom a_prenom, a.titre act_titre
        FROM tache t
        JOIN utilisateur u ON u.id_utilisateur=t.id_assigne_a
        JOIN activite a ON a.id_activite=t.id_activite
        WHERE t.id_assigne_par=? AND t.statut NOT IN ('VALIDE','ANNULEE')
        ORDER BY t.echeance_prevue ASC LIMIT 5
    """, (uid,)).fetchall()

    nb_notif = db.execute(
        "SELECT COUNT(*) FROM notification WHERE id_destinataire=? AND lue=0", (uid,)
    ).fetchone()[0]
    db.close()

    score = round(100 * valides / total) if total else 0
    body = f"""
    <div class="topbar">
      <div class="page-h">Tableau de bord</div>
      <div class="flex ic gap2">
        <span class="muted sm">{session['prenom']} {session['nom']}</span>
        <span class="pill" style="background:#EFF6FF;color:#1E40AF">Responsable</span>
        {'<a href="/notifications" class="pill" style="background:#FEF2F2;color:#B91C1C">'+str(nb_notif)+' notifications</a>' if nb_notif else ''}
      </div>
    </div>
    <div class="content">
      <div class="kgrid">
        <div class="kpi"><div class="kl">Tâches assignées</div>
          <div class="kv" style="color:var(--brand)">{total}</div>
          <div class="ks">à mon équipe</div></div>
        <div class="kpi"><div class="kl">En cours / attente</div>
          <div class="kv" style="color:var(--info)">{en_cours}</div>
          <div class="ks">actives</div></div>
        <div class="kpi"><div class="kl">En retard</div>
          <div class="kv" style="color:var(--err)">{retards}</div>
          <div class="ks">à traiter en priorité</div></div>
        <div class="kpi"><div class="kl">Livrables à valider</div>
          <div class="kv" style="color:var(--warn)">{a_valider}</div>
          <div class="ks">en attente de décision</div></div>
      </div>

      <div class="g2" style="gap:18px">
        <div class="card">
          <div class="card-h">Mon équipe — productivité</div>
          {''.join(f"""
          <div class="gantt-row" style="border-top:{'1px solid var(--border)' if i>0 else 'none'}">
            <div class="gantt-lbl fw5">{ag['prenom']} {ag['nom']}</div>
            <div class="gantt-track">
              <div class="gantt-bar" style="width:{round(100*(ag['valides'] or 0)/max(ag['total'],1))}%;background:var(--brand);left:0"></div>
            </div>
            <div class="gantt-pct">{ag['valides'] or 0}/{ag['total'] or 0}</div>
          </div>""" for i,ag in enumerate(agents)) if agents else '<div class="muted sm">Aucun agent sous votre supervision.</div>'}
          <a href="/productivite" class="btn btn-g btn-sm" style="margin-top:12px">Détail complet</a>
        </div>

        <div class="card">
          <div class="card-h flex ic jb" style="margin-bottom:14px">
            <span>Tâches urgentes</span>
            <a href="/taches" class="btn btn-g btn-sm">Toutes</a>
          </div>
          {''.join(f"""
          <div style="padding:9px 0;border-top:{'1px solid var(--border)' if i>0 else 'none'}">
            <div class="flex ic jb">
              <div class="fw5 sm">{t['libelle']}</div>
              <span class="badge {badge(t['statut'])[0]}">{badge(t['statut'])[1]}</span>
            </div>
            <div class="muted" style="font-size:11px;margin-top:2px">{t['a_prenom']} {t['a_nom']} · {t['act_titre']} · {t['echeance_prevue']}</div>
          </div>""" for i,t in enumerate(taches_urgentes)) if taches_urgentes else '<div class="muted sm">Aucune tâche urgente.</div>'}
        </div>
      </div>

      <div class="card">
        <div class="card-h flex ic jb" style="margin-bottom:14px">
          <span>Raccourcis</span>
        </div>
        <div class="flex gap2" style="flex-wrap:wrap">
          <a href="/assigner" class="btn btn-a">&#43; Assigner une tâche</a>
          <a href="/livrables" class="btn btn-p">&#9744; Valider des livrables</a>
          <a href="/gantt" class="btn btn-g">&#9641; Voir le Gantt</a>
          <a href="/taches?statut=EN_RETARD" class="btn btn-err">Voir les retards</a>
        </div>
      </div>
    </div>
    """
    return render("Tableau de bord", body, active="dashboard")


# ─────────────────────────────────────────
# MES ACTIVITÉS
# ─────────────────────────────────────────
@app.route("/activites")
@login_required
def mes_activites():
    uid = session["user_id"]
    db  = get_db()
    sid = session.get("id_service")
    activites = db.execute("""
        SELECT a.*,
               COUNT(t.id_tache) nb_taches,
               SUM(t.statut='VALIDE') nb_valides,
               SUM(t.statut='EN_RETARD') nb_retards
        FROM activite a
        LEFT JOIN tache t ON t.id_activite=a.id_activite
        WHERE a.id_service=? OR a.id_createur=?
        GROUP BY a.id_activite
        ORDER BY a.date_debut DESC
    """, (sid, uid)).fetchall()
    db.close()

    rows = ""
    for a in activites:
        b = badge(a["statut"])
        pct = round(100 * (a["nb_valides"] or 0) / max(a["nb_taches"] or 1, 1))
        rows += f"""
        <tr>
          <td class="fw5">{a['titre']}</td>
          <td><span class="pill" style="background:#EFF6FF;color:#1E40AF">{a['type']}</span></td>
          <td>{a['date_debut']}</td>
          <td>{a['date_fin_prevue']}</td>
          <td>
            <div class="flex ic gap2">
              <div class="bar-w" style="width:80px"><div class="bar-f" style="width:{pct}%;background:var(--brand)"></div></div>
              <span class="muted" style="font-size:11px">{pct}%</span>
            </div>
          </td>
          <td>{a['nb_taches'] or 0} tâches · <span style="color:var(--err)">{a['nb_retards'] or 0} retards</span></td>
          <td><span class="badge {b[0]}">{b[1]}</span></td>
          <td><a href="/activites/{a['id_activite']}" class="btn btn-g btn-sm">Voir</a></td>
        </tr>"""

    body = f"""
    <div class="topbar"><div class="page-h">Mes activités</div>
      <a href="/assigner" class="btn btn-a btn-sm">&#43; Nouvelle tâche</a>
    </div>
    <div class="content">
      <div class="card">
        <table class="tbl">
          <thead><tr><th>Activité</th><th>Type</th><th>Début</th><th>Échéance</th>
            <th>Avancement</th><th>Tâches</th><th>Statut</th><th></th></tr></thead>
          <tbody>{rows if rows else '<tr><td colspan="8" style="text-align:center;color:var(--muted);padding:22px">Aucune activité.</td></tr>'}</tbody>
        </table>
      </div>
    </div>"""
    return render("Mes activités", body, active="activites")


@app.route("/activites/<int:aid>")
@login_required
def activite_detail(aid):
    uid = session["user_id"]
    db  = get_db()
    a = db.execute("SELECT * FROM activite WHERE id_activite=?", (aid,)).fetchone()
    if not a:
        db.close(); flash("Activité introuvable.", "danger")
        return redirect(url_for("mes_activites"))

    taches = db.execute("""
        SELECT t.*, u.nom a_nom, u.prenom a_prenom
        FROM tache t JOIN utilisateur u ON u.id_utilisateur=t.id_assigne_a
        WHERE t.id_activite=? AND t.id_assigne_par=?
        ORDER BY t.echeance_prevue
    """, (aid, uid)).fetchall()
    db.close()

    rows = ""
    for t in taches:
        b = badge(t["statut"])
        e = ecart(t["echeance_prevue"], t["echeance_reelle"])
        ecart_html = ""
        if e is not None:
            col = "var(--err)" if e > 0 else "var(--ok)"
            ecart_html = f'<span style="font-size:11px;color:{col}">{"+" if e>0 else ""}{e}j</span>'
        rows += f"""<tr>
          <td class="fw5">{t['libelle']}</td>
          <td class="muted sm">{t['type_livrable'].replace('_',' ')}</td>
          <td>{t['a_prenom']} {t['a_nom']}</td>
          <td>{t['echeance_prevue']} {ecart_html}</td>
          <td><span class="badge {b[0]}">{b[1]}</span></td>
          <td><a href="/taches/{t['id_tache']}" class="btn btn-g btn-sm">Détail</a></td>
        </tr>"""

    nb_total  = len(taches)
    nb_valide = sum(1 for t in taches if t["statut"] == "VALIDE")
    pct = round(100 * nb_valide / max(nb_total, 1))

    body = f"""
    <div class="topbar">
      <div class="flex ic gap2">
        <a href="/activites" class="btn btn-g btn-sm">&larr;</a>
        <div class="page-h">{a['titre']}</div>
        <span class="pill" style="background:#EFF6FF;color:#1E40AF">{a['type']}</span>
      </div>
      <span class="badge {badge(a['statut'])[0]}">{badge(a['statut'])[1]}</span>
    </div>
    <div class="content">
      <div class="card">
        <div class="g3">
          <div class="kpi"><div class="kl">Total tâches</div><div class="kv">{nb_total}</div></div>
          <div class="kpi"><div class="kl">Validées</div><div class="kv" style="color:var(--ok)">{nb_valide}</div></div>
          <div class="kpi"><div class="kl">Avancement</div>
            <div class="kv" style="color:var(--brand)">{pct}%</div>
            <div class="bar-w" style="margin-top:6px"><div class="bar-f" style="width:{pct}%;background:var(--brand)"></div></div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-h flex ic jb" style="margin-bottom:14px">
          <span>Tâches de cette activité</span>
          <a href="/assigner?activite={aid}" class="btn btn-a btn-sm">&#43; Nouvelle tâche</a>
        </div>
        <table class="tbl">
          <thead><tr><th>Libellé</th><th>Livrable</th><th>Assignée à</th><th>Échéance</th><th>Statut</th><th></th></tr></thead>
          <tbody>{rows if rows else '<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:20px">Aucune tâche.</td></tr>'}</tbody>
        </table>
      </div>
    </div>"""
    return render(f"Activité — {a['titre']}", body, active="activites")


# ─────────────────────────────────────────
# ASSIGNER UNE TÂCHE  (N+1 → N)
# ─────────────────────────────────────────
@app.route("/assigner", methods=["GET","POST"])
@login_required
def assigner_tache():
    uid = session["user_id"]
    db  = get_db()

    if request.method == "POST":
        libelle      = request.form["libelle"].strip()
        type_livr    = request.form["type_livrable"]
        description  = request.form.get("description","").strip()
        echeance     = request.form["echeance_prevue"]
        id_activite  = int(request.form["id_activite"])
        id_assigne_a = int(request.form["id_assigne_a"])

        # Vérifier que l'agent est bien un subordonné
        agent = db.execute(
            "SELECT * FROM utilisateur WHERE id_utilisateur=? AND id_superieur=?",
            (id_assigne_a, uid)
        ).fetchone()
        if not agent:
            flash("Vous ne pouvez assigner une tâche qu'à vos agents directs (N).", "danger")
            db.close()
            return redirect(url_for("assigner_tache"))

        db.execute("""
            INSERT INTO tache (libelle,type_livrable,description,echeance_prevue,
                               statut,id_activite,id_assigne_par,id_assigne_a)
            VALUES (?,?,?,?,'EN_ATTENTE',?,?,?)
        """, (libelle, type_livr, description, echeance, id_activite, uid, id_assigne_a))
        new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        db.execute("""INSERT INTO historique_tache
            (id_tache,type_action,id_utilisateur_apres,statut_apres,effectue_par)
            VALUES (?,'ASSIGNATION_INITIALE',?,?,?)""",
            (new_id, id_assigne_a, "EN_ATTENTE", uid))

        notifier(db, id_assigne_a, "ASSIGNATION",
                 f"Nouvelle tâche assignée : « {libelle} » — échéance {echeance}", new_id)
        db.commit()
        flash(f"Tâche « {libelle} » assignée à {agent['prenom']} {agent['nom']}.", "success")
        db.close()
        return redirect(url_for("mes_taches_resp"))

    sid = session.get("id_service")
    pre_activite = request.args.get("activite", "")
    activites = db.execute(
        "SELECT * FROM activite WHERE id_service=? AND statut IN ('PLANIFIEE','EN_COURS') ORDER BY date_debut DESC",
        (sid,)
    ).fetchall()
    agents = db.execute(
        "SELECT * FROM utilisateur WHERE id_superieur=? AND role='AGENT' AND actif=1 ORDER BY nom",
        (uid,)
    ).fetchall()
    db.close()

    opts_act = "".join(
        f'<option value="{a["id_activite"]}" {"selected" if str(a["id_activite"])==pre_activite else ""}>{a["titre"]} ({a["type"]})</option>'
        for a in activites
    ) or '<option disabled>Aucune activité disponible</option>'
    opts_agent = "".join(
        f'<option value="{ag["id_utilisateur"]}">{ag["prenom"]} {ag["nom"]}</option>'
        for ag in agents
    ) or '<option disabled>Aucun agent sous votre supervision</option>'
    type_opts = "".join(
        f'<option value="{v}">{v.replace("_"," ")}</option>'
        for v in ["CONVOCATION","TERMES_REFERENCE","RAPPORT","COMPTE_RENDU","PV",
                  "FICHE_TECHNIQUE","DOSSIER_MARCHE","APPEL_CANDIDATURES","AUTRE"]
    )

    body = f"""
    <div class="topbar"><div class="page-h">Assigner une tâche</div></div>
    <div class="content">
      <div style="max-width:560px">
        <div class="card">
          <div class="card-h">Nouvelle tâche — règle N+1 → N</div>
          <div class="alert al-info" style="margin-bottom:16px;font-size:13px">
            Conformément à la matrice RAMA, seul un N+1 peut assigner une tâche à un N.
            Seuls vos agents directs apparaissent ci-dessous.
          </div>
          <form method="POST">
            <div class="form-g">
              <label class="lbl">Activité concernée *</label>
              <select name="id_activite" class="inp" required>{opts_act}</select>
            </div>
            <div class="form-g">
              <label class="lbl">Libellé de la tâche *</label>
              <input type="text" name="libelle" class="inp" placeholder="Ex : Rédiger les termes de référence" required>
            </div>
            <div class="form-g">
              <label class="lbl">Type de livrable *</label>
              <select name="type_livrable" class="inp" required>{type_opts}</select>
            </div>
            <div class="form-g">
              <label class="lbl">Description / consignes</label>
              <textarea name="description" class="inp" rows="3" placeholder="Détails, sources à consulter, format attendu..."></textarea>
            </div>
            <div class="g2">
              <div class="form-g">
                <label class="lbl">Échéance prévue *</label>
                <input type="date" name="echeance_prevue" class="inp" required>
              </div>
              <div class="form-g">
                <label class="lbl">Assigner à (agent N) *</label>
                <select name="id_assigne_a" class="inp" required>{opts_agent}</select>
              </div>
            </div>
            <button type="submit" class="btn btn-a">Assigner la tâche</button>
            <a href="/taches" class="btn btn-g" style="margin-left:8px">Annuler</a>
          </form>
        </div>
      </div>
    </div>"""
    return render("Assigner une tâche", body, active="assigner")


# ─────────────────────────────────────────
# SUIVI DES TÂCHES
# ─────────────────────────────────────────
@app.route("/taches")
@login_required
def mes_taches_resp():
    uid    = session["user_id"]
    filtre = request.args.get("statut","")
    db     = get_db()
    q = """
        SELECT t.*, u.nom a_nom, u.prenom a_prenom, a.titre act_titre, a.type act_type
        FROM tache t
        JOIN utilisateur u ON u.id_utilisateur=t.id_assigne_a
        JOIN activite a ON a.id_activite=t.id_activite
        WHERE t.id_assigne_par=?
    """
    params = [uid]
    if filtre:
        q += " AND t.statut=?"
        params.append(filtre)
    q += " ORDER BY t.echeance_prevue ASC"
    taches = db.execute(q, params).fetchall()
    db.close()

    rows = ""
    for t in taches:
        b = badge(t["statut"])
        e = ecart(t["echeance_prevue"], t["echeance_reelle"])
        ecart_html = ""
        if e is not None:
            col = "var(--err)" if e > 0 else "var(--ok)"
            ecart_html = f'<span style="color:{col};font-size:11px">{"+" if e>0 else ""}{e}j</span>'
        rows += f"""<tr>
          <td class="fw5">{t['libelle']}</td>
          <td><span class="pill" style="background:#F1F5F9;color:#475569;font-size:11px">{t['type_livrable'].replace('_',' ')}</span></td>
          <td>{t['act_titre']}</td>
          <td>{t['a_prenom']} {t['a_nom']}</td>
          <td>{t['echeance_prevue']} {ecart_html}</td>
          <td><span class="badge {b[0]}">{b[1]}</span></td>
          <td>
            <a href="/taches/{t['id_tache']}" class="btn btn-g btn-sm">Détail</a>
            <a href="/taches/{t['id_tache']}/reassigner" class="btn btn-g btn-sm">Réassigner</a>
          </td>
        </tr>"""

    filtres_html = "".join(
        f'<a href="/taches?statut={s}" class="btn btn-sm {"btn-p" if filtre==s else "btn-g"}">{l}</a>'
        for s, l in [("","Toutes"),("EN_ATTENTE","En attente"),("EN_COURS","En cours"),
                     ("EN_RETARD","En retard"),("LIVRE","Livrés"),("VALIDE","Validés")]
    )

    body = f"""
    <div class="topbar"><div class="page-h">Suivi des tâches</div>
      <div class="flex gap2">{filtres_html}</div>
    </div>
    <div class="content">
      <div class="card">
        <table class="tbl">
          <thead><tr><th>Tâche</th><th>Livrable</th><th>Activité</th>
            <th>Agent</th><th>Échéance</th><th>Statut</th><th>Actions</th></tr></thead>
          <tbody>{rows if rows else '<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:22px">Aucune tâche.</td></tr>'}</tbody>
        </table>
      </div>
    </div>"""
    return render("Suivi des tâches", body, active="taches")


# ─────────────────────────────────────────
# DÉTAIL TÂCHE (vue responsable)
# ─────────────────────────────────────────
@app.route("/taches/<int:tid>")
@login_required
def tache_detail(tid):
    uid = session["user_id"]
    db  = get_db()
    t = db.execute("""
        SELECT t.*, u.nom a_nom, u.prenom a_prenom, a.titre act_titre
        FROM tache t JOIN utilisateur u ON u.id_utilisateur=t.id_assigne_a
        JOIN activite a ON a.id_activite=t.id_activite
        WHERE t.id_tache=? AND t.id_assigne_par=?
    """, (tid, uid)).fetchone()
    if not t:
        db.close(); flash("Tâche introuvable.", "danger")
        return redirect(url_for("mes_taches_resp"))

    livrables = db.execute(
        "SELECT * FROM livrable WHERE id_tache=? ORDER BY date_soumission DESC", (tid,)
    ).fetchall()
    histo = db.execute("""
        SELECT h.*, ua.nom av_nom, ua.prenom av_prenom,
               ub.nom ap_nom, ub.prenom ap_prenom,
               uc.nom ef_nom, uc.prenom ef_prenom
        FROM historique_tache h
        LEFT JOIN utilisateur ua ON ua.id_utilisateur=h.id_utilisateur_avant
        LEFT JOIN utilisateur ub ON ub.id_utilisateur=h.id_utilisateur_apres
        LEFT JOIN utilisateur uc ON uc.id_utilisateur=h.effectue_par
        WHERE h.id_tache=? ORDER BY h.date_action DESC
    """, (tid,)).fetchall()
    db.close()

    e = ecart(t["echeance_prevue"], t["echeance_reelle"])
    b = badge(t["statut"])
    ecart_html = ""
    if e is not None:
        col = "var(--err)" if e > 0 else ("var(--warn)" if e == 0 else "var(--ok)")
        lab = f"+{e}j retard" if e > 0 else (f"{abs(e)}j avant l'échéance" if e < 0 else "Dans les temps")
        ecart_html = f'<span style="color:{col}">{lab}</span>'

    livr_rows = ""
    for l in livrables:
        bl = badge(l["statut_validation"])
        livr_rows += f"""
        <div style="padding:10px 0;border-top:1px solid var(--border)">
          <div class="flex ic jb">
            <div class="fw5 sm">{l['fichier_nom']}</div>
            <span class="badge {bl[0]}">{bl[1]}</span>
          </div>
          <div class="muted" style="font-size:11px;margin-top:2px">{l['date_soumission'][:16]}</div>
          {f'<div style="font-size:12px;color:var(--err);margin-top:3px">{l["motif_rejet"]}</div>' if l['motif_rejet'] else ''}
        </div>"""

    tl = ""
    for h in histo:
        tl += f"""<div class="tl-i">
          <div class="tl-dot" style="background:var(--brand)"></div>
          <div class="tl-d">{h['date_action'][:16]} — {h['ef_prenom'] or ''} {h['ef_nom'] or ''}</div>
          <div class="tl-t fw5">{h['type_action'].replace('_',' ')}</div>
          {f'<div class="tl-t muted">{h["statut_avant"]} → {h["statut_apres"]}</div>' if h['statut_avant'] else ''}
          {f'<div style="font-size:12px;color:var(--muted)">{h["motif"]}</div>' if h['motif'] else ''}
        </div>"""

    body = f"""
    <div class="topbar">
      <div class="flex ic gap2">
        <a href="/taches" class="btn btn-g btn-sm">&larr;</a>
        <div class="page-h">{t['libelle']}</div>
      </div>
      <div class="flex ic gap2">
        <span class="badge {b[0]}">{b[1]}</span>
        <a href="/taches/{tid}/reassigner" class="btn btn-g btn-sm">Réassigner</a>
      </div>
    </div>
    <div class="content">
      <div class="g2" style="gap:18px">
        <div>
          <div class="card">
            <div class="card-h">Informations</div>
            <table style="width:100%;font-size:13px">
              <tr><td class="muted" style="padding:5px 0">Activité</td><td class="fw5">{t['act_titre']}</td></tr>
              <tr><td class="muted" style="padding:5px 0">Agent assigné</td><td>{t['a_prenom']} {t['a_nom']}</td></tr>
              <tr><td class="muted" style="padding:5px 0">Livrable attendu</td><td>{t['type_livrable'].replace('_',' ')}</td></tr>
              <tr><td class="muted" style="padding:5px 0">Échéance prévue</td><td>{t['echeance_prevue']}</td></tr>
              <tr><td class="muted" style="padding:5px 0">Livré le</td><td>{t['echeance_reelle'] or '—'}</td></tr>
              <tr><td class="muted" style="padding:5px 0">Écart</td><td>{ecart_html or '—'}</td></tr>
            </table>
            {f'<hr class="sep"><div class="muted sm" style="margin-bottom:4px">Description</div><div class="sm">{t["description"]}</div>' if t['description'] else ''}
          </div>
          <div class="card">
            <div class="card-h">Livrables soumis</div>
            {livr_rows or '<div class="muted sm">Aucun livrable.</div>'}
          </div>
        </div>
        <div>
          <div class="card">
            <div class="card-h">Historique des actions</div>
            <div class="tl">{tl or '<div class="muted sm">Aucune action.</div>'}</div>
          </div>
        </div>
      </div>
    </div>"""
    return render(f"Tâche — {t['libelle']}", body, active="taches")


# ─────────────────────────────────────────
# RÉASSIGNATION
# ─────────────────────────────────────────
@app.route("/taches/<int:tid>/reassigner", methods=["GET","POST"])
@login_required
def reassigner_tache(tid):
    uid = session["user_id"]
    db  = get_db()
    t = db.execute(
        "SELECT t.*, u.nom a_nom, u.prenom a_prenom FROM tache t JOIN utilisateur u ON u.id_utilisateur=t.id_assigne_a WHERE t.id_tache=? AND t.id_assigne_par=?",
        (tid, uid)
    ).fetchone()
    if not t:
        db.close(); flash("Tâche introuvable.", "danger")
        return redirect(url_for("mes_taches_resp"))

    if request.method == "POST":
        new_agent = int(request.form["id_assigne_a"])
        motif     = request.form.get("motif","").strip()
        old_agent = t["id_assigne_a"]

        agent = db.execute(
            "SELECT * FROM utilisateur WHERE id_utilisateur=? AND id_superieur=?",
            (new_agent, uid)
        ).fetchone()
        if not agent:
            flash("Agent non autorisé.", "danger")
            db.close()
            return redirect(url_for("reassigner_tache", tid=tid))

        db.execute("UPDATE tache SET id_assigne_a=? WHERE id_tache=?", (new_agent, tid))
        db.execute("""INSERT INTO historique_tache
            (id_tache,type_action,id_utilisateur_avant,id_utilisateur_apres,motif,effectue_par)
            VALUES (?,'REASSIGNATION',?,?,?,?)""",
            (tid, old_agent, new_agent, motif, uid))

        notifier(db, new_agent, "ASSIGNATION",
                 f"Tâche réassignée vers vous : « {t['libelle']} »", tid)
        notifier(db, old_agent, "INFO",
                 f"Tâche « {t['libelle']} » retirée et réassignée.", tid)
        db.commit()
        flash("Tâche réassignée avec succès. Historique mis à jour.", "success")
        db.close()
        return redirect(url_for("tache_detail", tid=tid))

    agents = db.execute(
        "SELECT * FROM utilisateur WHERE id_superieur=? AND role='AGENT' AND actif=1 AND id_utilisateur!=? ORDER BY nom",
        (uid, t["id_assigne_a"])
    ).fetchall()
    db.close()

    opts = "".join(f'<option value="{ag["id_utilisateur"]}">{ag["prenom"]} {ag["nom"]}</option>' for ag in agents)

    body = f"""
    <div class="topbar">
      <div class="flex ic gap2">
        <a href="/taches/{tid}" class="btn btn-g btn-sm">&larr;</a>
        <div class="page-h">Réassigner — {t['libelle']}</div>
      </div>
    </div>
    <div class="content"><div style="max-width:500px">
      <div class="card">
        <div class="card-h">Réassignation de tâche</div>
        <div class="alert al-warn" style="margin-bottom:16px;font-size:13px">
          Actuellement assignée à <strong>{t['a_prenom']} {t['a_nom']}</strong>.
          Cette action sera tracée dans l'historique.
        </div>
        <form method="POST">
          <div class="form-g">
            <label class="lbl">Nouvel agent *</label>
            <select name="id_assigne_a" class="inp" required>
              {opts or '<option disabled>Aucun autre agent disponible</option>'}
            </select>
          </div>
          <div class="form-g">
            <label class="lbl">Motif de la réassignation *</label>
            <textarea name="motif" class="inp" rows="3" placeholder="Indisponibilité, surcharge, réorientation..." required></textarea>
          </div>
          <button type="submit" class="btn btn-a">Confirmer la réassignation</button>
          <a href="/taches/{tid}" class="btn btn-g" style="margin-left:8px">Annuler</a>
        </form>
      </div>
    </div></div>"""
    return render("Réassignation", body, active="taches")


# ─────────────────────────────────────────
# VALIDATION DES LIVRABLES
# ─────────────────────────────────────────
@app.route("/livrables")
@login_required
def livrables_a_valider():
    uid = session["user_id"]
    filtre = request.args.get("f","en_attente")
    db  = get_db()
    cond = "AND l.statut_validation='EN_ATTENTE'" if filtre == "en_attente" else ""
    livs = db.execute(f"""
        SELECT l.*, t.libelle t_libelle, t.id_tache,
               u.nom a_nom, u.prenom a_prenom,
               a.titre act_titre
        FROM livrable l
        JOIN tache t ON t.id_tache=l.id_tache
        JOIN utilisateur u ON u.id_utilisateur=t.id_assigne_a
        JOIN activite a ON a.id_activite=t.id_activite
        WHERE t.id_assigne_par=? {cond}
        ORDER BY l.date_soumission DESC
    """, (uid,)).fetchall()
    db.close()

    rows = ""
    for l in livs:
        bl = badge(l["statut_validation"])
        rows += f"""<tr>
          <td class="fw5">{l['fichier_nom']}</td>
          <td>{l['t_libelle']}</td>
          <td>{l['act_titre']}</td>
          <td>{l['a_prenom']} {l['a_nom']}</td>
          <td class="muted sm">{l['date_soumission'][:16]}</td>
          <td><span class="badge {bl[0]}">{bl[1]}</span></td>
          <td>
            {"" if l['statut_validation'] != 'EN_ATTENTE' else f'''
            <form method="POST" action="/livrables/{l['id_livrable']}/valider" style="display:inline">
              <input type="hidden" name="decision" value="VALIDE">
              <button class="btn btn-ok btn-sm">&#10003; Valider</button>
            </form>
            <a href="/livrables/{l['id_livrable']}/rejeter" class="btn btn-err btn-sm" style="margin-left:4px">&#10007; Rejeter</a>'''}
          </td>
        </tr>"""

    f_tabs = "".join(
        f'<a href="/livrables?f={k}" class="btn btn-sm {"btn-p" if filtre==k else "btn-g"}">{l}</a>'
        for k, l in [("en_attente","À valider"),("tous","Tous")]
    )

    body = f"""
    <div class="topbar"><div class="page-h">Livrables à valider</div>
      <div class="flex gap2">{f_tabs}</div>
    </div>
    <div class="content">
      <div class="card">
        <table class="tbl">
          <thead><tr><th>Fichier</th><th>Tâche</th><th>Activité</th>
            <th>Agent</th><th>Soumis le</th><th>Statut</th><th>Actions</th></tr></thead>
          <tbody>{rows if rows else '<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:22px">Aucun livrable en attente.</td></tr>'}</tbody>
        </table>
      </div>
    </div>"""
    return render("Livrables à valider", body, active="livrables")


@app.route("/livrables/<int:lid>/valider", methods=["POST"])
@login_required
def valider_livrable(lid):
    uid = session["user_id"]
    db  = get_db()
    l = db.execute(
        "SELECT l.*,t.id_assigne_par,t.id_assigne_a,t.id_tache,t.libelle FROM livrable l JOIN tache t ON t.id_tache=l.id_tache WHERE l.id_livrable=?",
        (lid,)
    ).fetchone()
    if l and l["id_assigne_par"] == uid:
        decision = request.form.get("decision","VALIDE")
        db.execute(
            "UPDATE livrable SET statut_validation=?,id_validateur=?,date_validation=? WHERE id_livrable=?",
            (decision, uid, str(date.today()), lid)
        )
        db.execute(
            "UPDATE tache SET statut=? WHERE id_tache=?",
            (decision, l["id_tache"])
        )
        db.execute("""INSERT INTO historique_tache
            (id_tache,type_action,statut_avant,statut_apres,effectue_par)
            VALUES (?,'CHANGEMENT_STATUT','LIVRE',?,'?')""".replace("'?'", "?"),
            (l["id_tache"], decision, uid))
        notifier(db, l["id_assigne_a"], "VALIDATION",
                 f"Votre livrable « {l['libelle']} » a été {decision.lower()}.", l["id_tache"])
        db.commit()
        flash(f"Livrable {'validé' if decision=='VALIDE' else 'rejeté'}.", "success")
    db.close()
    return redirect(url_for("livrables_a_valider"))


@app.route("/livrables/<int:lid>/rejeter", methods=["GET","POST"])
@login_required
def rejeter_livrable(lid):
    uid = session["user_id"]
    db  = get_db()
    l = db.execute(
        "SELECT l.*,t.id_assigne_par,t.id_assigne_a,t.id_tache,t.libelle FROM livrable l JOIN tache t ON t.id_tache=l.id_tache WHERE l.id_livrable=?",
        (lid,)
    ).fetchone()
    if not l or l["id_assigne_par"] != uid:
        db.close(); flash("Non autorisé.", "danger")
        return redirect(url_for("livrables_a_valider"))

    if request.method == "POST":
        motif = request.form.get("motif","").strip()
        db.execute(
            "UPDATE livrable SET statut_validation='REJETE',motif_rejet=?,id_validateur=?,date_validation=? WHERE id_livrable=?",
            (motif, uid, str(date.today()), lid)
        )
        db.execute("UPDATE tache SET statut='REJETE' WHERE id_tache=?", (l["id_tache"],))
        db.execute("""INSERT INTO historique_tache
            (id_tache,type_action,statut_avant,statut_apres,motif,effectue_par)
            VALUES (?,'CHANGEMENT_STATUT','LIVRE','REJETE',?,?)""",
            (l["id_tache"], motif, uid))
        notifier(db, l["id_assigne_a"], "REJET",
                 f"Livrable rejeté : « {l['libelle']} » — {motif}", l["id_tache"])
        db.commit()
        flash("Livrable rejeté. L'agent a été notifié.", "success")
        db.close()
        return redirect(url_for("livrables_a_valider"))
    db.close()

    body = f"""
    <div class="topbar">
      <div class="flex ic gap2">
        <a href="/livrables" class="btn btn-g btn-sm">&larr;</a>
        <div class="page-h">Rejeter — {l['fichier_nom']}</div>
      </div>
    </div>
    <div class="content"><div style="max-width:480px">
      <div class="modal-bg"><div class="modal">
        <div class="modal-h">Motif du rejet</div>
        <div class="alert al-warn" style="margin-bottom:16px;font-size:13px">
          Ce motif sera visible par l'agent et consigné dans l'historique.
        </div>
        <form method="POST">
          <div class="form-g">
            <label class="lbl">Motif détaillé *</label>
            <textarea name="motif" class="inp" rows="4" placeholder="Ex : Le rapport est incomplet, il manque la section 3..." required></textarea>
          </div>
          <div class="flex gap2" style="margin-top:6px">
            <button type="submit" class="btn btn-err">Confirmer le rejet</button>
            <a href="/livrables" class="btn btn-g">Annuler</a>
          </div>
        </form>
      </div></div>
    </div></div>"""
    return render("Rejeter un livrable", body, active="livrables")


# ─────────────────────────────────────────
# GANTT
# ─────────────────────────────────────────
@app.route("/gantt")
@login_required
def gantt_view():
    uid = session["user_id"]
    sid = session.get("id_service")
    db  = get_db()
    activites = db.execute(
        "SELECT * FROM activite WHERE id_service=? ORDER BY date_debut", (sid,)
    ).fetchall()
    taches_par_act = {}
    for a in activites:
        taches_par_act[a["id_activite"]] = db.execute("""
            SELECT t.*, u.nom a_nom, u.prenom a_prenom
            FROM tache t JOIN utilisateur u ON u.id_utilisateur=t.id_assigne_a
            WHERE t.id_activite=? AND t.id_assigne_par=?
            ORDER BY t.echeance_prevue
        """, (a["id_activite"], uid)).fetchall()
    db.close()

    gantt_html = ""
    today = str(date.today())
    month_start = today[:8] + "01"

    for a in activites:
        taches = taches_par_act.get(a["id_activite"], [])
        if not taches:
            continue
        gantt_html += f"""
        <div style="margin-bottom:20px">
          <div class="flex ic jb" style="margin-bottom:8px">
            <div class="fw5 sm">{a['titre']} <span class="pill" style="background:#EFF6FF;color:#1E40AF;margin-left:4px">{a['type']}</span></div>
            <span class="badge {badge(a['statut'])[0]}">{badge(a['statut'])[1]}</span>
          </div>"""
        for t in taches:
            try:
                d_start = datetime.strptime(a["date_debut"], "%Y-%m-%d").date()
                d_end   = datetime.strptime(a["date_fin_prevue"], "%Y-%m-%d").date()
                d_task  = datetime.strptime(t["echeance_prevue"], "%Y-%m-%d").date()
                total_days = max((d_end - d_start).days, 1)
                task_off   = max((d_task - d_start).days, 0)
                left_pct   = round(100 * task_off / total_days)
                width_pct  = max(round(100 / total_days * 3), 6)
                left_pct   = min(left_pct, 94)
                bar_color  = "#DC2626" if t["statut"] == "EN_RETARD" else ("#16A34A" if t["statut"] == "VALIDE" else "#1B3A6B")
            except:
                left_pct, width_pct, bar_color = 0, 20, "#1B3A6B"

            b_label = badge(t["statut"])[1]
            gantt_html += f"""
            <div class="gantt-row">
              <div class="gantt-lbl" title="{t['libelle']}">{t['libelle'][:22]}{'…' if len(t['libelle'])>22 else ''}</div>
              <div class="gantt-track" style="height:16px">
                <div class="gantt-bar" style="left:{left_pct}%;width:{width_pct}%;background:{bar_color}"></div>
                <div style="position:absolute;top:0;left:50%;transform:translateX(-50%);font-size:10px;color:var(--muted);white-space:nowrap;line-height:16px">{t['echeance_prevue']}</div>
              </div>
              <div style="width:80px;flex-shrink:0;text-align:right"><span class="badge {badge(t['statut'])[0]}" style="font-size:10px">{b_label}</span></div>
            </div>"""
        gantt_html += "</div><hr class='sep'>"

    body = f"""
    <div class="topbar"><div class="page-h">Diagramme de Gantt</div>
      <span class="muted sm">Vue de vos activités · {today}</span>
    </div>
    <div class="content">
      <div class="card">
        <div class="flex ic jb" style="margin-bottom:16px">
          <div class="card-h" style="margin:0">Tâches par activité</div>
          <div class="flex gap2">
            <span class="flex ic gap2" style="font-size:12px"><span style="width:12px;height:8px;background:#1B3A6B;border-radius:2px;display:inline-block"></span>En cours</span>
            <span class="flex ic gap2" style="font-size:12px"><span style="width:12px;height:8px;background:#16A34A;border-radius:2px;display:inline-block"></span>Validé</span>
            <span class="flex ic gap2" style="font-size:12px"><span style="width:12px;height:8px;background:#DC2626;border-radius:2px;display:inline-block"></span>En retard</span>
          </div>
        </div>
        {gantt_html or '<div class="muted sm">Aucune activité à afficher.</div>'}
      </div>
    </div>"""
    return render("Gantt", body, active="gantt")


# ─────────────────────────────────────────
# PRODUCTIVITÉ ÉQUIPE
# ─────────────────────────────────────────
@app.route("/productivite")
@login_required
def productivite_equipe():
    uid = session["user_id"]
    db  = get_db()
    agents = db.execute(
        "SELECT * FROM utilisateur WHERE id_superieur=? AND actif=1 ORDER BY nom", (uid,)
    ).fetchall()

    stats = []
    for ag in agents:
        taches = db.execute(
            "SELECT * FROM tache WHERE id_assigne_a=? AND id_assigne_par=?",
            (ag["id_utilisateur"], uid)
        ).fetchall()
        total    = len(taches)
        valides  = sum(1 for t in taches if t["statut"] == "VALIDE")
        en_cours = sum(1 for t in taches if t["statut"] in ("EN_COURS","EN_ATTENTE"))
        retards  = sum(1 for t in taches if t["statut"] == "EN_RETARD" or
                       (t["statut"] not in ("VALIDE",) and t["echeance_prevue"] < str(date.today())))
        dans_delais = sum(1 for t in taches if t["statut"] == "VALIDE" and
                          t["echeance_reelle"] and t["echeance_reelle"] <= t["echeance_prevue"])
        score = round(100 * dans_delais / max(valides, 1)) if valides else 0
        stats.append({
            "ag": ag, "total": total, "valides": valides,
            "en_cours": en_cours, "retards": retards, "score": score
        })

    cards = ""
    for s in stats:
        ag = s["ag"]
        pct = round(100 * s["valides"] / max(s["total"], 1))
        score_col = "var(--ok)" if s["score"] >= 80 else ("var(--warn)" if s["score"] >= 50 else "var(--err)")
        cards += f"""
        <div class="card" style="margin-bottom:14px">
          <div class="flex ic jb" style="margin-bottom:12px">
            <div class="flex ic gap2">
              <div class="avatar" style="width:36px;height:36px;font-size:12px">{ag['prenom'][0]}{ag['nom'][0]}</div>
              <div>
                <div class="fw5 sm">{ag['prenom']} {ag['nom']}</div>
                <div class="muted" style="font-size:11px">{ag['role']} · Service {session.get('service','')}</div>
              </div>
            </div>
            <div style="font-size:20px;font-weight:600;color:{score_col}">{s['score']}%</div>
          </div>
          <div class="g3">
            <div style="text-align:center">
              <div class="muted" style="font-size:11px;margin-bottom:2px">Total</div>
              <div style="font-size:18px;font-weight:600">{s['total']}</div>
            </div>
            <div style="text-align:center">
              <div class="muted" style="font-size:11px;margin-bottom:2px">Validées</div>
              <div style="font-size:18px;font-weight:600;color:var(--ok)">{s['valides']}</div>
            </div>
            <div style="text-align:center">
              <div class="muted" style="font-size:11px;margin-bottom:2px">En retard</div>
              <div style="font-size:18px;font-weight:600;color:var(--err)">{s['retards']}</div>
            </div>
          </div>
          <div style="margin-top:12px">
            <div class="flex ic jb" style="margin-bottom:4px">
              <span class="muted" style="font-size:11px">Tâches complétées</span>
              <span style="font-size:11px;font-weight:500">{pct}%</span>
            </div>
            <div class="bar-w"><div class="bar-f" style="width:{pct}%;background:var(--brand)"></div></div>
          </div>
          <div style="margin-top:10px">
            <a href="/taches?agent={ag['id_utilisateur']}" class="btn btn-g btn-sm">Voir ses tâches</a>
          </div>
        </div>"""

    body = f"""
    <div class="topbar"><div class="page-h">Productivité de l'équipe</div></div>
    <div class="content">
      <div style="max-width:680px">
        {cards or '<div class="card muted sm">Aucun agent sous votre supervision.</div>'}
      </div>
    </div>"""
    return render("Productivité équipe", body, active="perf")


# ─────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────
@app.route("/notifications")
@login_required
def notifications_view():
    uid = session["user_id"]
    db  = get_db()
    notifs = db.execute(
        "SELECT * FROM notification WHERE id_destinataire=? ORDER BY date_envoi DESC LIMIT 50",
        (uid,)
    ).fetchall()
    db.execute("UPDATE notification SET lue=1 WHERE id_destinataire=?", (uid,))
    db.commit()
    db.close()

    type_color = {
        "ASSIGNATION": "#EFF6FF:#1E40AF",
        "VALIDATION":  "#F0FDF4:#166534",
        "REJET":       "#FEF2F2:#991B1B",
        "RETARD":      "#FFF7ED:#92400E",
        "INFO":        "#F8FAFC:#475569",
        "SIGNALEMENT": "#FEF2F2:#991B1B",
    }
    rows = ""
    for n in notifs:
        colors = type_color.get(n["type"], "#F8FAFC:#475569").split(":")
        rows += f"""
        <div style="padding:12px 0;border-top:1px solid var(--border);display:flex;gap:12px;align-items:flex-start">
          <span class="pill" style="background:{colors[0]};color:{colors[1]};flex-shrink:0">{n['type']}</span>
          <div style="flex:1">
            <div class="sm">{n['message']}</div>
            <div class="muted" style="font-size:11px;margin-top:3px">{n['date_envoi'][:16]}</div>
          </div>
          {'<span style="width:7px;height:7px;border-radius:50%;background:var(--info);flex-shrink:0;margin-top:5px"></span>' if not n['lue'] else ''}
        </div>"""

    body = f"""
    <div class="topbar"><div class="page-h">Notifications</div></div>
    <div class="content"><div class="card">
      {rows or '<div class="muted sm">Aucune notification.</div>'}
    </div></div>"""
    return render("Notifications", body, active="notifs")


# ─────────────────────────────────────────
# LANCEMENT
# ─────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("=" * 55)
    print("  RAMA — Vue Responsable (N+1)")
    print("  URL locale : http://127.0.0.1:5000")
    print("  Compte démo : resp@rama.sn / admin")
    print("=" * 55)
    app.run(debug=True, port=5000)
