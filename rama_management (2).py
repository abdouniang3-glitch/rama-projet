# ============================================================
#  RAMA — Vues Management (Chef de service, Directeur, DG)
#  Application Flask complète — Google Colab ready
#  Prof. Papa DIOP | L2 Informatique 2025-2026
# ============================================================
#  Comptes démo :
#    Chef de service : chef@rama.sn  / admin
#    Directeur       : dir@rama.sn   / admin
#    DG              : dg@rama.sn    / admin
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
# DB
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
        libelle      TEXT NOT NULL, description TEXT);
    CREATE TABLE IF NOT EXISTS utilisateur (
        id_utilisateur INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL, prenom TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE, mot_de_passe TEXT NOT NULL,
        role TEXT NOT NULL, id_superieur INTEGER REFERENCES utilisateur(id_utilisateur),
        id_service INTEGER REFERENCES service(id_service), actif INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS activite (
        id_activite INTEGER PRIMARY KEY AUTOINCREMENT,
        titre TEXT NOT NULL, type TEXT NOT NULL, description TEXT,
        date_debut TEXT NOT NULL, date_fin_prevue TEXT NOT NULL,
        date_fin_reelle TEXT, statut TEXT DEFAULT 'PLANIFIEE',
        id_service INTEGER REFERENCES service(id_service),
        id_createur INTEGER REFERENCES utilisateur(id_utilisateur));
    CREATE TABLE IF NOT EXISTS tache (
        id_tache INTEGER PRIMARY KEY AUTOINCREMENT,
        libelle TEXT NOT NULL, type_livrable TEXT NOT NULL, description TEXT,
        echeance_prevue TEXT NOT NULL, echeance_reelle TEXT,
        statut TEXT DEFAULT 'EN_ATTENTE',
        id_activite INTEGER REFERENCES activite(id_activite),
        id_assigne_par INTEGER REFERENCES utilisateur(id_utilisateur),
        id_assigne_a INTEGER REFERENCES utilisateur(id_utilisateur),
        date_assignation TEXT DEFAULT (datetime('now')));
    CREATE TABLE IF NOT EXISTS livrable (
        id_livrable INTEGER PRIMARY KEY AUTOINCREMENT,
        id_tache INTEGER REFERENCES tache(id_tache),
        fichier_nom TEXT NOT NULL, commentaire TEXT,
        date_soumission TEXT DEFAULT (datetime('now')),
        statut_validation TEXT DEFAULT 'EN_ATTENTE',
        id_validateur INTEGER REFERENCES utilisateur(id_utilisateur),
        date_validation TEXT, motif_rejet TEXT);
    CREATE TABLE IF NOT EXISTS historique_tache (
        id_historique INTEGER PRIMARY KEY AUTOINCREMENT,
        id_tache INTEGER REFERENCES tache(id_tache),
        type_action TEXT NOT NULL,
        id_utilisateur_avant INTEGER, id_utilisateur_apres INTEGER,
        statut_avant TEXT, statut_apres TEXT, motif TEXT,
        effectue_par INTEGER REFERENCES utilisateur(id_utilisateur),
        date_action TEXT DEFAULT (datetime('now')));
    CREATE TABLE IF NOT EXISTS notification (
        id_notification INTEGER PRIMARY KEY AUTOINCREMENT,
        id_destinataire INTEGER REFERENCES utilisateur(id_utilisateur),
        type TEXT NOT NULL, message TEXT NOT NULL,
        lue INTEGER DEFAULT 0, date_envoi TEXT DEFAULT (datetime('now')),
        id_tache INTEGER REFERENCES tache(id_tache));
    CREATE TABLE IF NOT EXISTS idee (
        id_idee INTEGER PRIMARY KEY AUTOINCREMENT,
        id_auteur INTEGER REFERENCES utilisateur(id_utilisateur),
        titre TEXT NOT NULL, contenu TEXT NOT NULL,
        nb_votes INTEGER DEFAULT 0, statut TEXT DEFAULT 'SOUMISE',
        date_soumission TEXT DEFAULT (datetime('now')));
    CREATE TABLE IF NOT EXISTS avis (
        id_avis INTEGER PRIMARY KEY AUTOINCREMENT,
        id_auteur INTEGER REFERENCES utilisateur(id_utilisateur),
        type TEXT NOT NULL, cible TEXT, contenu TEXT NOT NULL,
        statut TEXT DEFAULT 'SOUMIS',
        date_soumission TEXT DEFAULT (datetime('now')));
    """)
    if db.execute("SELECT COUNT(*) FROM utilisateur").fetchone()[0] == 0:
        db.execute("INSERT INTO service (libelle) VALUES ('Direction administrative')")
        db.execute("INSERT INTO service (libelle) VALUES ('Direction technique')")
        db.execute("INSERT INTO service (libelle) VALUES ('Direction financière')")
        db.executemany(
            "INSERT INTO utilisateur (nom,prenom,email,mot_de_passe,role,id_superieur,id_service) VALUES (?,?,?,?,?,?,?)",
            [
                ("DIOP",  "Amadou",  "dg@rama.sn",     generate_password_hash("admin"),"DG",          None,1),
                ("SARR",  "Fatou",   "dir@rama.sn",     generate_password_hash("admin"),"DIRECTEUR",   1,   1),
                ("FALL",  "Khady",   "chef@rama.sn",    generate_password_hash("admin"),"CHEF_SERVICE",2,   1),
                ("BA",    "Ibou",    "resp@rama.sn",     generate_password_hash("admin"),"RESPONSABLE", 3,   1),
                ("KANE",  "Aissa",   "agent@rama.sn",   generate_password_hash("admin"),"AGENT",       4,   1),
                ("NDIAYE","Moussa",  "agent2@rama.sn",  generate_password_hash("admin"),"AGENT",       4,   1),
                ("SOW",   "Mariama", "agent3@rama.sn",  generate_password_hash("admin"),"AGENT",       4,   2),
                ("DIALLO","Abdou",   "dir2@rama.sn",    generate_password_hash("admin"),"DIRECTEUR",   1,   2),
                ("TOURE", "Aminata", "chef2@rama.sn",   generate_password_hash("admin"),"CHEF_SERVICE",8,   2),
            ]
        )
        db.executemany(
            "INSERT INTO activite (titre,type,description,date_debut,date_fin_prevue,statut,id_service,id_createur) VALUES (?,?,?,?,?,?,?,?)",
            [
                ("Atelier national RAMA 2026","ATELIER","Restitution annuelle","2026-04-01","2026-04-30","EN_COURS",1,2),
                ("Séminaire de coordination", "SEMINAIRE","Inter-directions","2026-04-15","2026-05-15","PLANIFIEE",1,2),
                ("Mission terrain nord",      "MISSION", "Évaluation régionale","2026-03-20","2026-04-20","EN_COURS",2,8),
                ("Forum des partenaires",     "FORUM",   "Forum annuel","2026-05-01","2026-05-20","PLANIFIEE",2,8),
                ("Colloque national",         "COLLOQUE","Colloque inter-agences","2026-06-01","2026-06-15","PLANIFIEE",3,2),
                ("Salon de l'innovation",     "SALON",   "Salon tech","2026-07-01","2026-07-10","PLANIFIEE",2,8),
            ]
        )
        db.executemany(
            "INSERT INTO tache (libelle,type_livrable,echeance_prevue,statut,id_activite,id_assigne_par,id_assigne_a) VALUES (?,?,?,?,?,?,?)",
            [
                ("Termes de référence",  "TERMES_REFERENCE","2026-04-10","VALIDE",   1,4,5),
                ("Convocation",          "CONVOCATION",     "2026-04-12","LIVRE",    1,4,5),
                ("Rapport final",        "RAPPORT",         "2026-04-28","EN_COURS", 1,4,6),
                ("Fiche technique",      "FICHE_TECHNIQUE", "2026-04-20","EN_RETARD",2,4,5),
                ("Compte-rendu mission", "COMPTE_RENDU",    "2026-04-18","EN_ATTENTE",3,4,7),
                ("Rapport évaluation",   "RAPPORT",         "2026-04-25","EN_COURS", 3,4,7),
                ("Dossier lancement",    "DOSSIER_MARCHE",  "2026-05-05","EN_ATTENTE",4,9,7),
            ]
        )
        db.execute("INSERT INTO livrable (id_tache,fichier_nom,statut_validation) VALUES (1,'tdr_v1.pdf','VALIDE')")
        db.execute("INSERT INTO livrable (id_tache,fichier_nom,statut_validation) VALUES (2,'convocation.pdf','EN_ATTENTE')")
        for i in range(3):
            db.execute("INSERT INTO idee (id_auteur,titre,contenu,nb_votes,statut) VALUES (?,?,?,?,?)",
                (5+i, f"Idée {i+1} des agents", f"Contenu de l'idée {i+1}", 3+i*2, "SOUMISE"))
        db.execute("INSERT INTO avis (id_auteur,type,cible,contenu,statut) VALUES (5,'SIGNALEMENT','module_taches','Accès non autorisé détecté','SOUMIS')")
        db.execute("INSERT INTO avis (id_auteur,type,cible,contenu,statut) VALUES (6,'FONCTIONNALITE','interface','Interface peu intuitive sur mobile','SOUMIS')")
    db.commit(); db.close()

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def login_required(f):
    @functools.wraps(f)
    def d(*a,**kw):
        if "user_id" not in session: return redirect(url_for("login"))
        return f(*a,**kw)
    return d

def require_roles(*roles):
    def decorator(f):
        @functools.wraps(f)
        def d(*a,**kw):
            if session.get("role") not in roles:
                flash("Accès non autorisé pour votre rôle.","danger")
                return redirect(url_for("dashboard"))
            return f(*a,**kw)
        return d
    return decorator

def ecart(prevue, reelle=None):
    try:
        dp = datetime.strptime(prevue,"%Y-%m-%d").date()
        dr = datetime.strptime(reelle,"%Y-%m-%d").date() if reelle else date.today()
        return (dr-dp).days
    except: return None

def badge(st):
    return {"EN_ATTENTE":("bw","En attente"),"EN_COURS":("bp","En cours"),
            "LIVRE":("bd","Livré"),"VALIDE":("bv","Validé"),"REJETE":("br","Rejeté"),
            "EN_RETARD":("bl","En retard"),"PLANIFIEE":("bw","Planifiée"),
            "ACHEVEE":("bv","Achevée"),"ANNULEE":("br","Annulée")}.get(st,("bw",st))

def notifier(db,dest,typ,msg,id_tache=None):
    db.execute("INSERT INTO notification (id_destinataire,type,message,id_tache) VALUES (?,?,?,?)",(dest,typ,msg,id_tache))

CSS = """
:root{--brand:#1B3A6B;--accent:#E8A020;--bg:#EEF2F8;--sf:#FFF;
  --bd:#DDE3EE;--tx:#18243A;--mu:#637089;
  --ok:#16A34A;--wn:#D97706;--er:#DC2626;--in:#2563EB;--r:10px;}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--tx);min-height:100vh}
a{color:inherit;text-decoration:none}
.shell{display:flex;min-height:100vh}
.sb{width:252px;flex-shrink:0;background:var(--brand);display:flex;flex-direction:column;padding-bottom:24px}
.sb-logo{padding:24px 20px 16px;border-bottom:1px solid rgba(255,255,255,.1);margin-bottom:10px}
.sb-logo .app{font-family:'Syne',sans-serif;font-size:21px;color:#fff;letter-spacing:.02em}
.sb-logo .sub{font-size:11px;color:rgba(255,255,255,.4);margin-top:2px}
.sb-lbl{font-size:10px;color:rgba(255,255,255,.3);letter-spacing:.1em;padding:8px 14px 4px;text-transform:uppercase}
.nav{display:flex;align-items:center;gap:8px;padding:9px 12px;border-radius:8px;margin:0 8px 2px;font-size:14px;color:rgba(255,255,255,.7);cursor:pointer;transition:all .15s}
.nav:hover{background:rgba(255,255,255,.1);color:#fff}
.nav.on{background:var(--accent);color:#fff;font-weight:500}
.ic{width:17px;text-align:center;font-size:13px;flex-shrink:0}
.sb-badge{background:var(--er);color:#fff;font-size:10px;font-weight:600;padding:1px 6px;border-radius:10px;margin-left:auto}
.sb-role{margin:8px 14px 4px;padding:6px 10px;background:rgba(255,255,255,.08);border-radius:6px;font-size:11px;color:rgba(255,255,255,.6)}
.sb-user{margin-top:auto;padding:12px 18px;border-top:1px solid rgba(255,255,255,.1)}
.av{width:32px;height:32px;border-radius:50%;background:var(--accent);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;color:#fff;flex-shrink:0}
.un{font-size:13px;font-weight:500;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ur{font-size:11px;color:rgba(255,255,255,.4)}
.main{flex:1;display:flex;flex-direction:column;min-width:0}
.top{background:var(--sf);border-bottom:1px solid var(--bd);padding:0 26px;height:56px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.ph{font-family:'Syne',sans-serif;font-size:17px;font-weight:700}
.ct{padding:22px 26px;flex:1}
.card{background:var(--sf);border:1px solid var(--bd);border-radius:var(--r);padding:16px 20px;margin-bottom:16px}
.ch{font-family:'Syne',sans-serif;font-size:14px;font-weight:700;margin-bottom:12px}
.kg{display:grid;grid-template-columns:repeat(4,1fr);gap:11px;margin-bottom:18px}
.kp{background:var(--sf);border:1px solid var(--bd);border-radius:var(--r);padding:14px 16px}
.kl{font-size:12px;color:var(--mu);margin-bottom:4px}
.kv{font-size:24px;font-weight:600}
.ks{font-size:11px;color:var(--mu);margin-top:3px}
.bw{background:#F1F5F9;color:#475569}
.bp{background:#EFF6FF;color:#1D4ED8}
.bd{background:#FEF9C3;color:#854D0E}
.bv{background:#F0FDF4;color:#15803D}
.br{background:#FEF2F2;color:#B91C1C}
.bl{background:#FFF7ED;color:#C2410C}
.bg-badge{display:inline-flex;align-items:center;gap:4px;font-size:12px;font-weight:500;padding:3px 9px;border-radius:20px}
.bg-badge::before{content:'';width:5px;height:5px;border-radius:50%;background:currentColor;opacity:.55}
.tbl{width:100%;border-collapse:collapse;font-size:13px}
.tbl th{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--mu);font-weight:500;padding:8px 10px;border-bottom:2px solid var(--bd);text-align:left}
.tbl td{padding:10px 10px;border-bottom:1px solid var(--bd);vertical-align:middle}
.tbl tr:last-child td{border-bottom:none}
.tbl tr:hover td{background:#F8FAFD}
.fg{margin-bottom:13px}
.lb{display:block;font-size:13px;font-weight:500;margin-bottom:4px}
.inp{width:100%;padding:8px 10px;border:1px solid var(--bd);border-radius:8px;font-size:14px;font-family:inherit;background:var(--sf);color:var(--tx);transition:border-color .15s}
.inp:focus{outline:none;border-color:var(--brand);box-shadow:0 0 0 3px rgba(27,58,107,.07)}
textarea.inp{resize:vertical;min-height:72px}
.btn{display:inline-flex;align-items:center;gap:6px;padding:7px 15px;border-radius:8px;border:none;font-size:13px;font-weight:500;font-family:inherit;cursor:pointer;transition:all .15s}
.bp-{background:var(--brand);color:#fff}.bp-:hover{background:#152E56}
.ba{background:var(--accent);color:#fff}.ba:hover{background:#C9871A}
.bg{background:transparent;border:1px solid var(--bd);color:var(--tx)}.bg:hover{background:var(--bg)}
.bok{background:#F0FDF4;color:#166534;border:1px solid #BBF7D0}
.ber{background:#FEF2F2;color:#B91C1C;border:1px solid #FECACA}
.bsm{padding:4px 10px;font-size:12px}
.al{padding:10px 14px;border-radius:8px;font-size:13px;margin-bottom:13px;display:flex;align-items:center;gap:8px}
.al-ok{background:#F0FDF4;color:#166534;border:1px solid #BBF7D0}
.al-er{background:#FEF2F2;color:#991B1B;border:1px solid #FECACA}
.al-in{background:#EFF6FF;color:#1E40AF;border:1px solid #BFDBFE}
.al-wn{background:#FFFBEB;color:#92400E;border:1px solid #FDE68A}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.fx{display:flex}.gp2{gap:8px}.gp3{gap:12px}.ai{align-items:center}.jb{justify-content:space-between}
.mu{color:var(--mu);font-size:13px}.sm{font-size:13px}.fw{font-weight:500}
.pill{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:500}
.bw2{height:7px;background:#EEF2F7;border-radius:4px;overflow:hidden}
.bf{height:100%;border-radius:4px}
.tl{position:relative;padding-left:16px}
.tl::before{content:'';position:absolute;left:4px;top:0;bottom:0;width:1px;background:var(--bd)}
.tl-i{position:relative;padding:0 0 12px 16px}
.tl-d{position:absolute;left:-6px;top:4px;width:10px;height:10px;border-radius:50%;border:2px solid var(--sf)}
.tl-t{font-size:11px;color:var(--mu);margin-bottom:2px}
.gr{display:flex;align-items:center;gap:8px;padding:4px 0;border-top:1px solid var(--bd)}
.gl{font-size:12px;color:var(--mu);width:130px;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gt{flex:1;height:10px;background:#EEF2F7;border-radius:3px;overflow:hidden;position:relative}
.gb{height:100%;border-radius:3px;position:absolute;top:0}
.gp{font-size:11px;color:var(--mu);width:32px;text-align:right;flex-shrink:0}
.sep{border:none;border-top:1px solid var(--bd);margin:12px 0}
"""

BASE = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RAMA — {title}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=Syne:wght@600;700&display=swap" rel="stylesheet">
<style>{css}</style></head>
<body>{flashes}{body}</body></html>"""

def render(title, body, active=""):
    from flask import get_flashed_messages
    msgs = get_flashed_messages(with_categories=True)
    fh = ""
    if msgs:
        fh = '<div style="position:fixed;top:14px;right:14px;z-index:999;max-width:320px">'
        for cat,msg in msgs:
            cls = {"success":"al-ok","danger":"al-er","warning":"al-wn","info":"al-in"}.get(cat,"al-in")
            fh += f'<div class="al {cls}" style="margin-bottom:7px;box-shadow:0 3px 10px rgba(0,0,0,.1)">{msg}</div>'
        fh += "</div>"

    db = get_db()
    nb_notif = 0
    nb_avis  = 0
    if "user_id" in session:
        nb_notif = db.execute("SELECT COUNT(*) FROM notification WHERE id_destinataire=? AND lue=0",(session["user_id"],)).fetchone()[0]
        if session.get("role") in ("CHEF_SERVICE","DIRECTEUR","DG"):
            nb_avis = db.execute("SELECT COUNT(*) FROM avis WHERE statut='SOUMIS'").fetchone()[0]
    db.close()

    role = session.get("role","")
    svc  = session.get("service","")

    # Navigation selon rôle
    nav_commun = f"""
    <a href="{url_for('dashboard')}" class="nav {'on' if active=='db' else ''}"><span class="ic">&#9632;</span>Tableau de bord</a>
    <a href="{url_for('activites_view')}" class="nav {'on' if active=='act' else ''}"><span class="ic">&#9670;</span>Activités</a>
    <a href="{url_for('taches_view')}" class="nav {'on' if active=='tch' else ''}"><span class="ic">&#9776;</span>Tâches</a>
    <a href="{url_for('gantt_view')}" class="nav {'on' if active=='gnt' else ''}"><span class="ic">&#9641;</span>Gantt</a>
    <a href="{url_for('perf_view')}" class="nav {'on' if active=='prf' else ''}"><span class="ic">&#9650;</span>Productivité</a>
    <a href="{url_for('ecarts_view')}" class="nav {'on' if active=='ec' else ''}"><span class="ic">&#9632;</span>Écarts délais</a>"""

    nav_chef_plus = ""
    if role in ("CHEF_SERVICE","DIRECTEUR","DG"):
        nav_chef_plus = f"""
        <a href="{url_for('assigner_view')}" class="nav {'on' if active=='asg' else ''}"><span class="ic">&#43;</span>Assigner tâche</a>"""

    nav_dg_plus = ""
    if role in ("DIRECTEUR","DG"):
        nav_dg_plus = f"""
        <a href="{url_for('kpi_global')}" class="nav {'on' if active=='kpi' else ''}"><span class="ic">&#9673;</span>KPIs globaux</a>
        <a href="{url_for('avis_view')}" class="nav {'on' if active=='av' else ''}"><span class="ic">&#9993;</span>Avis
        {'<span class="sb-badge">'+str(nb_avis)+'</span>' if nb_avis else ''}</a>
        <a href="{url_for('idees_view')}" class="nav {'on' if active=='id' else ''}"><span class="ic">&#9728;</span>Boîte à idées</a>"""

    nav_notif = f"""
    <a href="{url_for('notifs_view')}" class="nav {'on' if active=='nt' else ''}"><span class="ic">&#9993;</span>Notifications
    {'<span class="sb-badge">'+str(nb_notif)+'</span>' if nb_notif else ''}</a>"""

    role_labels = {"DG":"Directeur Général","DIRECTEUR":"Directeur","CHEF_SERVICE":"Chef de service"}
    role_badge_color = {"DG":"#7F77DD","DIRECTEUR":"#185FA5","CHEF_SERVICE":"#0F6E56"}.get(role,"#637089")

    sb = f"""
    <div class="shell">
    <aside class="sb">
      <div class="sb-logo"><div class="app">RAMA</div><div class="sub">Reporting &amp; Monitoring</div></div>
      <div class="sb-role" style="color:rgba(255,255,255,.75);background:rgba(255,255,255,.1)">
        {role_labels.get(role,role)} — {svc or 'Structure'}
      </div>
      <div style="padding:0 0 4px">
        <div class="sb-lbl">Navigation</div>
        {nav_commun}
        {nav_chef_plus}
        {nav_dg_plus}
        <div class="sb-lbl" style="margin-top:6px">Alertes</div>
        {nav_notif}
      </div>
      <div class="sb-user">
        <div class="fx ai gp2">
          <div class="av" style="background:{role_badge_color}">{session.get('prenom','?')[0]}{session.get('nom','?')[0]}</div>
          <div style="flex:1;min-width:0">
            <div class="un">{session.get('prenom','')} {session.get('nom','')}</div>
            <div class="ur">{role_labels.get(role,role)}</div>
          </div>
          <a href="{url_for('logout')}" style="color:rgba(255,255,255,.3);font-size:14px">&#10005;</a>
        </div>
      </div>
    </aside>
    <main class="main">"""

    full = sb + body + "</main></div>"
    return BASE.format(title=title, css=CSS, flashes=fh, body=full)

# ─────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────
LOGIN_TPL = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500&family=Syne:wght@700&display=swap" rel="stylesheet">
<style>{css}.lw{{min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--brand)}}
.lc{{background:var(--sf);border-radius:14px;padding:36px 32px;width:360px}}
.ll{{font-family:'Syne',sans-serif;font-size:28px;font-weight:700;color:var(--brand);text-align:center;margin-bottom:4px}}
.ls{{font-size:13px;color:var(--mu);text-align:center;margin-bottom:24px}}</style></head><body>
{f}<div class="lw"><div class="lc">
<div class="ll">RAMA</div><div class="ls">Espace Management</div>
<form method="POST" action="/login">
<div class="fg"><label class="lb">Email</label><input type="email" name="email" class="inp" placeholder="chef@rama.sn" required></div>
<div class="fg"><label class="lb">Mot de passe</label><input type="password" name="password" class="inp" required></div>
<button type="submit" class="btn bp-" style="width:100%;justify-content:center;margin-top:5px">Connexion</button>
</form>
<div class="mu" style="text-align:center;margin-top:14px;font-size:12px">
chef@rama.sn · dir@rama.sn · dg@rama.sn (mdp: admin)</div>
</div></div></body></html>"""

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email,pwd=request.form["email"],request.form["password"]
        db=get_db()
        u=db.execute("SELECT u.*,s.libelle svc FROM utilisateur u LEFT JOIN service s ON s.id_service=u.id_service WHERE u.email=? AND u.actif=1",(email,)).fetchone()
        db.close()
        if u and check_password_hash(u["mot_de_passe"],pwd):
            session.clear()
            for k in ("id_utilisateur","nom","prenom","role","id_service","id_superieur"):
                session[k]=u[k]
            session["service"]=u["svc"] or "—"
            session["user_id"]=u["id_utilisateur"]
            return redirect(url_for("dashboard"))
        flash("Identifiants incorrects.","danger")
    from flask import get_flashed_messages
    msgs=get_flashed_messages(with_categories=True)
    fh="".join(f'<div class="al al-er" style="max-width:360px;margin:12px auto">{m}</div>' for _,m in msgs)
    return LOGIN_TPL.format(css=CSS,f=fh)

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("login"))

# ─────────────────────────────────────────
# UTILITAIRES DONNÉES COMMUNES
# ─────────────────────────────────────────
def get_perimetre(db, uid, role, sid):
    """Retourne les activités et tâches dans le périmètre du rôle."""
    if role=="CHEF_SERVICE":
        acts=db.execute("SELECT * FROM activite WHERE id_service=? ORDER BY date_debut DESC",(sid,)).fetchall()
    elif role=="DIRECTEUR":
        # Toutes les activités des services dont il supervise les chefs
        acts=db.execute("""
            SELECT DISTINCT a.* FROM activite a
            JOIN utilisateur u ON u.id_service=a.id_service
            WHERE u.id_superieur=? OR a.id_service=?
            ORDER BY a.date_debut DESC
        """,(uid,sid)).fetchall()
    else:  # DG
        acts=db.execute("SELECT * FROM activite ORDER BY date_debut DESC").fetchall()
    return acts

def kpi_from_acts(db, acts):
    ids = [a["id_activite"] for a in acts]
    if not ids: return 0,0,0,0,0
    ph = ",".join("?"*len(ids))
    taches=db.execute(f"SELECT * FROM tache WHERE id_activite IN ({ph})",ids).fetchall()
    total    = len(taches)
    valides  = sum(1 for t in taches if t["statut"]=="VALIDE")
    en_cours = sum(1 for t in taches if t["statut"] in ("EN_COURS","EN_ATTENTE"))
    retards  = sum(1 for t in taches if t["statut"]=="EN_RETARD" or
                   (t["statut"] not in ("VALIDE","ANNULEE") and t["echeance_prevue"]<str(date.today())))
    pct = round(100*valides/max(total,1))
    return total, valides, en_cours, retards, pct

# ─────────────────────────────────────────
# TABLEAU DE BORD — ADAPTATIF SELON RÔLE
# ─────────────────────────────────────────
@app.route("/")
@login_required
def dashboard():
    uid  = session["user_id"]
    role = session["role"]
    sid  = session.get("id_service")
    db   = get_db()

    acts = get_perimetre(db, uid, role, sid)
    total, valides, en_cours, retards, pct = kpi_from_acts(db, acts)
    nb_act = len(acts)

    # Stats types d'activités
    type_counts = {}
    for a in acts:
        type_counts[a["type"]] = type_counts.get(a["type"],0)+1
    type_dominant = max(type_counts, key=type_counts.get) if type_counts else "—"

    # Retards critiques
    taches_retard = []
    if acts:
        ids = [a["id_activite"] for a in acts]
        ph  = ",".join("?"*len(ids))
        taches_retard = db.execute(f"""
            SELECT t.*,u.nom a_nom,u.prenom a_prenom,a.titre act_titre,s.libelle svc
            FROM tache t
            JOIN utilisateur u ON u.id_utilisateur=t.id_assigne_a
            JOIN activite a ON a.id_activite=t.id_activite
            JOIN service s ON s.id_service=a.id_service
            WHERE t.id_activite IN ({ph})
            AND (t.statut='EN_RETARD' OR (t.statut NOT IN ('VALIDE','ANNULEE') AND t.echeance_prevue<?))
            ORDER BY t.echeance_prevue LIMIT 6
        """, ids+[str(date.today())]).fetchall()

    # Productivité top agents
    top_agents = db.execute("""
        SELECT u.nom,u.prenom,
               COUNT(t.id_tache) total,
               SUM(t.statut='VALIDE') valides
        FROM utilisateur u
        JOIN tache t ON t.id_assigne_a=u.id_utilisateur
        GROUP BY u.id_utilisateur
        ORDER BY valides DESC LIMIT 4
    """).fetchall()

    nb_notif = db.execute("SELECT COUNT(*) FROM notification WHERE id_destinataire=? AND lue=0",(uid,)).fetchone()[0]
    nb_idees = db.execute("SELECT COUNT(*) FROM idee WHERE statut='SOUMISE'").fetchone()[0]
    nb_avis  = db.execute("SELECT COUNT(*) FROM avis WHERE statut='SOUMIS'").fetchone()[0]
    db.close()

    role_labels={"DG":"Directeur Général","DIRECTEUR":"Directeur","CHEF_SERVICE":"Chef de service"}
    role_color ={"DG":"#7F77DD","DIRECTEUR":"#185FA5","CHEF_SERVICE":"#0F6E56"}.get(role,"#637089")

    retard_rows="".join(f"""
    <tr>
      <td class="fw sm">{t['libelle']}</td>
      <td class="mu sm">{t['act_titre']}</td>
      <td class="mu sm">{t['svc']}</td>
      <td>{t['a_prenom']} {t['a_nom']}</td>
      <td style="color:var(--er);font-size:12px">+{ecart(t['echeance_prevue'])}j</td>
      <td><span class="bg-badge {badge(t['statut'])[0]}">{badge(t['statut'])[1]}</span></td>
    </tr>""" for t in taches_retard)

    agent_rows="".join(f"""
    <div class="gr" style="border-top:{'1px solid var(--bd)' if i>0 else 'none'}">
      <div class="gl fw">{ag['prenom']} {ag['nom']}</div>
      <div class="gt"><div class="gb" style="width:{round(100*(ag['valides'] or 0)/max(ag['total'],1))}%;background:var(--brand);left:0"></div></div>
      <div class="gp">{ag['valides'] or 0}/{ag['total'] or 0}</div>
    </div>""" for i,ag in enumerate(top_agents))

    act_type_html="".join(f"""
    <div class="fx ai jb" style="padding:5px 0;border-top:1px solid var(--bd)">
      <span class="sm">{tp}</span>
      <div class="fx ai gp2">
        <div style="width:80px;height:6px;background:#EEF2F7;border-radius:3px;overflow:hidden">
          <div style="width:{round(100*cnt/max(nb_act,1))}%;height:100%;background:var(--brand);border-radius:3px"></div>
        </div>
        <span class="mu" style="font-size:12px;min-width:16px">{cnt}</span>
      </div>
    </div>""" for tp,cnt in sorted(type_counts.items(),key=lambda x:-x[1]))

    perim_label = {"DG":"toute la structure","DIRECTEUR":"votre direction","CHEF_SERVICE":"votre service"}.get(role,"votre périmètre")

    body = f"""
    <div class="top">
      <div class="fx ai gp2">
        <div class="ph">Tableau de bord</div>
        <span class="pill" style="background:{role_color}22;color:{role_color}">{role_labels.get(role,role)}</span>
        <span class="mu sm">— {perim_label}</span>
      </div>
      <div class="fx ai gp2">
        {'<a href="/notifications" class="pill" style="background:#FEF2F2;color:#B91C1C">'+str(nb_notif)+' notif.</a>' if nb_notif else ''}
        {'<a href="/avis" class="pill" style="background:#FFF7ED;color:#92400E">'+str(nb_avis)+' avis</a>' if nb_avis and role in ("CHEF_SERVICE","DIRECTEUR","DG") else ''}
      </div>
    </div>
    <div class="ct">
      <div class="kg">
        <div class="kp"><div class="kl">Activités</div>
          <div class="kv" style="color:var(--brand)">{nb_act}</div>
          <div class="ks">{perim_label}</div></div>
        <div class="kp"><div class="kl">Taux complétion</div>
          <div class="kv" style="color:var(--ok)">{pct}%</div>
          <div class="bw2" style="margin-top:6px"><div class="bf" style="width:{pct}%;background:var(--ok)"></div></div></div>
        <div class="kp"><div class="kl">Tâches en retard</div>
          <div class="kv" style="color:var(--er)">{retards}</div>
          <div class="ks">à traiter en priorité</div></div>
        <div class="kp"><div class="kl">Idées / Avis</div>
          <div class="kv" style="color:var(--wn)">{nb_idees}</div>
          <div class="ks">{nb_avis} signalements</div></div>
      </div>

      <div class="g2" style="gap:16px">
        <div class="card">
          <div class="ch fx ai jb" style="margin-bottom:12px">
            <span>Retards actifs</span>
            <a href="/taches?statut=EN_RETARD" class="btn bg bsm">Tous</a>
          </div>
          <table class="tbl">
            <thead><tr><th>Tâche</th><th>Activité</th><th>Service</th><th>Agent</th><th>Retard</th><th>Statut</th></tr></thead>
            <tbody>{retard_rows or '<tr><td colspan="6" style="text-align:center;color:var(--mu);padding:18px">Aucun retard.</td></tr>'}</tbody>
          </table>
        </div>
        <div>
          <div class="card">
            <div class="ch">Types d'activités</div>
            {act_type_html or '<div class="mu sm">Aucune activité.</div>'}
          </div>
          <div class="card">
            <div class="ch fx ai jb" style="margin-bottom:12px">
              <span>Top productivité</span>
              <a href="/productivite" class="btn bg bsm">Détail</a>
            </div>
            {agent_rows or '<div class="mu sm">Aucune donnée.</div>'}
          </div>
        </div>
      </div>

      <div class="card">
        <div class="ch" style="margin-bottom:10px">Actions rapides</div>
        <div class="fx gp2" style="flex-wrap:wrap">
          {'<a href="/assigner" class="btn ba">&#43; Assigner une tâche</a>' if role in ("CHEF_SERVICE","DIRECTEUR","DG") else ''}
          <a href="/gantt" class="btn bg">&#9641; Voir le Gantt</a>
          <a href="/ecarts" class="btn bg">&#9632; Écarts délais</a>
          {'<a href="/kpi" class="btn bg">&#9673; KPIs globaux</a>' if role in ("DIRECTEUR","DG") else ''}
          {'<a href="/avis" class="btn bg">&#9993; Traiter les avis</a>' if role in ("CHEF_SERVICE","DIRECTEUR","DG") else ''}
          <a href="/idees" class="btn bg">&#9728; Boîte à idées</a>
        </div>
      </div>
    </div>"""
    return render("Tableau de bord", body, active="db")


# ─────────────────────────────────────────
# ACTIVITÉS
# ─────────────────────────────────────────
@app.route("/activites")
@login_required
def activites_view():
    uid=session["user_id"]; role=session["role"]; sid=session.get("id_service")
    db=get_db()
    acts=get_perimetre(db,uid,role,sid)
    rows=""
    for a in acts:
        ids=[a["id_activite"]]
        _,val,_,ret,pct=kpi_from_acts(db,[a])
        nb=db.execute("SELECT COUNT(*) FROM tache WHERE id_activite=?",(a["id_activite"],)).fetchone()[0]
        b=badge(a["statut"])
        rows+=f"""<tr>
          <td class="fw sm">{a['titre']}</td>
          <td><span class="pill" style="background:#EFF6FF;color:#1E40AF;font-size:11px">{a['type']}</span></td>
          <td class="mu sm">{a['date_debut']}</td>
          <td class="mu sm">{a['date_fin_prevue']}</td>
          <td>
            <div class="fx ai gp2">
              <div class="bw2" style="width:70px"><div class="bf" style="width:{pct}%;background:var(--brand)"></div></div>
              <span class="mu" style="font-size:11px">{pct}%</span>
            </div>
          </td>
          <td>{nb} tâches <span style="color:var(--er);font-size:11px">· {ret} retard(s)</span></td>
          <td><span class="bg-badge {b[0]}">{b[1]}</span></td>
          <td><a href="/activites/{a['id_activite']}" class="btn bg bsm">Voir</a></td>
        </tr>"""
    db.close()
    body=f"""
    <div class="top"><div class="ph">Activités</div>
      {'<a href="/assigner" class="btn ba bsm">&#43; Nouvelle tâche</a>' if session["role"] in ("CHEF_SERVICE","DIRECTEUR","DG") else ''}
    </div>
    <div class="ct"><div class="card">
      <table class="tbl">
        <thead><tr><th>Titre</th><th>Type</th><th>Début</th><th>Échéance</th><th>Avancement</th><th>Tâches</th><th>Statut</th><th></th></tr></thead>
        <tbody>{rows or '<tr><td colspan="8" style="text-align:center;color:var(--mu);padding:20px">Aucune activité.</td></tr>'}</tbody>
      </table>
    </div></div>"""
    return render("Activités",body,active="act")

@app.route("/activites/<int:aid>")
@login_required
def activite_detail(aid):
    db=get_db()
    a=db.execute("SELECT a.*,s.libelle svc FROM activite a JOIN service s ON s.id_service=a.id_service WHERE a.id_activite=?",(aid,)).fetchone()
    if not a: db.close(); flash("Introuvable.","danger"); return redirect(url_for("activites_view"))
    taches=db.execute("""
        SELECT t.*,u.nom an,u.prenom ap,up.nom pn,up.prenom pp
        FROM tache t
        JOIN utilisateur u ON u.id_utilisateur=t.id_assigne_a
        JOIN utilisateur up ON up.id_utilisateur=t.id_assigne_par
        WHERE t.id_activite=? ORDER BY t.echeance_prevue
    """,(aid,)).fetchall()
    db.close()
    nb=len(taches); val=sum(1 for t in taches if t["statut"]=="VALIDE")
    pct=round(100*val/max(nb,1))
    b=badge(a["statut"])
    rows="".join(f"""<tr>
      <td class="fw sm">{t['libelle']}</td>
      <td class="mu sm">{t['type_livrable'].replace('_',' ')}</td>
      <td>{t['ap']} {t['an']}</td>
      <td>{t['pp']} {t['pn']}</td>
      <td>{t['echeance_prevue']}</td>
      <td><span class="bg-badge {badge(t['statut'])[0]}">{badge(t['statut'])[1]}</span></td>
      <td><a href="/taches/{t['id_tache']}" class="btn bg bsm">Détail</a></td>
    </tr>""" for t in taches)
    body=f"""
    <div class="top">
      <div class="fx ai gp2">
        <a href="/activites" class="btn bg bsm">&larr;</a>
        <div class="ph">{a['titre']}</div>
        <span class="pill" style="background:#EFF6FF;color:#1E40AF">{a['type']}</span>
      </div>
      <span class="bg-badge {b[0]}">{b[1]}</span>
    </div>
    <div class="ct">
      <div class="g3" style="margin-bottom:16px">
        <div class="kp"><div class="kl">Tâches</div><div class="kv">{nb}</div></div>
        <div class="kp"><div class="kl">Validées</div><div class="kv" style="color:var(--ok)">{val}</div></div>
        <div class="kp"><div class="kl">Avancement</div>
          <div class="kv" style="color:var(--brand)">{pct}%</div>
          <div class="bw2" style="margin-top:6px"><div class="bf" style="width:{pct}%;background:var(--brand)"></div></div>
        </div>
      </div>
      <div class="card">
        <div class="ch fx ai jb" style="margin-bottom:12px">
          <span>Tâches</span>
          <a href="/assigner?activite={aid}" class="btn ba bsm">&#43; Assigner</a>
        </div>
        <table class="tbl">
          <thead><tr><th>Libellé</th><th>Livrable</th><th>Agent</th><th>Assignée par</th><th>Échéance</th><th>Statut</th><th></th></tr></thead>
          <tbody>{rows or '<tr><td colspan="7" style="text-align:center;color:var(--mu);padding:18px">Aucune tâche.</td></tr>'}</tbody>
        </table>
      </div>
    </div>"""
    return render(f"Activité",body,active="act")


# ─────────────────────────────────────────
# ASSIGNER UNE TÂCHE (Chef de service + Directeur)
# ─────────────────────────────────────────
@app.route("/assigner", methods=["GET","POST"])
@login_required
@require_roles("CHEF_SERVICE","DIRECTEUR","DG")
def assigner_view():
    uid=session["user_id"]; sid=session.get("id_service"); role=session["role"]
    db=get_db()
    if request.method=="POST":
        libelle   =request.form["libelle"].strip()
        type_l    =request.form["type_livrable"]
        desc      =request.form.get("description","").strip()
        ech       =request.form["echeance_prevue"]
        id_act    =int(request.form["id_activite"])
        id_agent  =int(request.form["id_assigne_a"])
       # Vérifier relation hiérarchique
        agent = db.execute("""
            SELECT u.* FROM utilisateur u
            JOIN utilisateur sup ON sup.id_utilisateur=?
            WHERE u.id_utilisateur=? AND u.niveau_hierarchique < sup.niveau_hierarchique
        """, (uid, id_agent)).fetchone()
        if not agent:
            flash("Vous ne pouvez assigner qu'à vos agents directs (N).","danger")
            db.close()
            return redirect(url_for("assigner_view"))
        db.execute("""INSERT INTO tache 
            (libelle, type_livrable, description, date_fin_prevue, statut, activite_id)
            VALUES (?,?,?,?,'non_demarree',?)""",
            (libelle, type_l, desc, ech, id_act))
        nid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute("""INSERT INTO affectation_tache 
            (tache_id, utilisateur_id, assigne_par_id, statut)
            VALUES (?,?,?,'active')""",
            (nid, id_agent, uid))
        aid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute("""INSERT INTO historique_affectation 
            (affectation_id, nouvel_utilisateur_id, type_changement, effectue_par_id)
            VALUES (?,?,'attribution',?)""",
            (aid, id_agent, uid))
        notifier(db, id_agent, "ASSIGNATION", f"Nouvelle tâche assignée : «{libelle}» — échéance {ech}", nid)
        db.commit()
        db.close()
        flash("Tâche assignée avec succès !","success")
        return redirect(url_for("assigner_view"))
    VALUES (?,?,'attribution',?)""",
    (aid, id_agent, uid))
notifier(db, id_agent, "ASSIGNATION", f"Nouvelle tâche assignée : «{libelle}» — échéance {ech}", nid)
db.commit()
db.close()
        flash(f"Tâche «{libelle}» assignée à {agent['prenom']} {agent['nom']}.","success")
        return redirect(url_for("taches_view"))

    acts=db.execute("SELECT * FROM activite WHERE id_service=? AND statut IN ('PLANIFIEE','EN_COURS') ORDER BY date_debut DESC",(sid,)).fetchall()
    agents=db.execute("SELECT * FROM utilisateur WHERE id_superieur=? AND actif=1 ORDER BY nom",(uid,)).fetchall()
    db.close()
    pre=request.args.get("activite","")
    opts_a="".join(f'<option value="{a["id_activite"]}" {"selected" if str(a["id_activite"])==pre else ""}>{a["titre"]} ({a["type"]})</option>' for a in acts) or '<option disabled>Aucune activité</option>'
    opts_u="".join(f'<option value="{u["id_utilisateur"]}">{u["prenom"]} {u["nom"]} ({u["role"]})</option>' for u in agents) or '<option disabled>Aucun agent direct</option>'
    livr_opts="".join(f'<option value="{v}">{v.replace("_"," ")}</option>' for v in ["CONVOCATION","TERMES_REFERENCE","RAPPORT","COMPTE_RENDU","PV","FICHE_TECHNIQUE","DOSSIER_MARCHE","APPEL_CANDIDATURES","AUTRE"])
    body=f"""
    <div class="top"><div class="ph">Assigner une tâche</div></div>
    <div class="ct"><div style="max-width:540px"><div class="card">
      <div class="ch">Nouvelle tâche — règle N+1 → N</div>
      <div class="al al-in" style="margin-bottom:14px;font-size:13px">Seuls vos agents directs apparaissent. La règle hiérarchique est vérifiée automatiquement.</div>
      <form method="POST">
        <div class="fg"><label class="lb">Activité *</label><select name="id_activite" class="inp" required>{opts_a}</select></div>
        <div class="fg"><label class="lb">Libellé *</label><input type="text" name="libelle" class="inp" placeholder="Ex : Rédiger les termes de référence" required></div>
        <div class="fg"><label class="lb">Type de livrable *</label><select name="type_livrable" class="inp" required>{livr_opts}</select></div>
        <div class="fg"><label class="lb">Description / consignes</label><textarea name="description" class="inp" rows="3"></textarea></div>
        <div class="g2">
          <div class="fg"><label class="lb">Échéance *</label><input type="date" name="echeance_prevue" class="inp" required></div>
          <div class="fg"><label class="lb">Assigner à *</label><select name="id_assigne_a" class="inp" required>{opts_u}</select></div>
        </div>
        <button type="submit" class="btn ba">Assigner</button>
        <a href="/taches" class="btn bg" style="margin-left:8px">Annuler</a>
      </form>
    </div></div></div>"""
    return render("Assigner",body,active="asg")


# ─────────────────────────────────────────
# SUIVI TÂCHES
# ─────────────────────────────────────────
@app.route("/taches")
@login_required
def taches_view():
    uid=session["user_id"]; role=session["role"]; sid=session.get("id_service")
    filtre=request.args.get("statut","")
    db=get_db()
    acts=get_perimetre(db,uid,role,sid)
    ids=[a["id_activite"] for a in acts]
    rows_html=""
    if ids:
        ph=",".join("?"*len(ids))
        q=f"""SELECT t.*,u.nom an,u.prenom ap,up.nom pn,up.prenom pp,a.titre at_,s.libelle svc
              FROM tache t
              JOIN utilisateur u ON u.id_utilisateur=t.id_assigne_a
              JOIN utilisateur up ON up.id_utilisateur=t.id_assigne_par
              JOIN activite a ON a.id_activite=t.id_activite
              JOIN service s ON s.id_service=a.id_service
              WHERE t.id_activite IN ({ph})"""
        params=list(ids)
        if filtre: q+=" AND t.statut=?"; params.append(filtre)
        q+=" ORDER BY t.echeance_prevue ASC"
        taches=db.execute(q,params).fetchall()
        rows_html="".join(f"""<tr>
          <td class="fw sm">{t['libelle']}</td>
          <td class="mu sm">{t['at_']}</td>
          <td class="mu sm">{t['svc']}</td>
          <td>{t['ap']} {t['an']}</td>
          <td>{t['pp']} {t['pn']}</td>
          <td>{t['echeance_prevue']}
            {f'<span style="color:var(--er);font-size:11px"> +{ecart(t["echeance_prevue"])}j</span>' if ecart(t["echeance_prevue"]) and ecart(t["echeance_prevue"])>0 and t["statut"] not in ("VALIDE",) else ''}
          </td>
          <td><span class="bg-badge {badge(t['statut'])[0]}">{badge(t['statut'])[1]}</span></td>
          <td><a href="/taches/{t['id_tache']}" class="btn bg bsm">Détail</a></td>
        </tr>""" for t in taches)
    db.close()
    f_tabs="".join(f'<a href="/taches?statut={s}" class="btn bsm {"bp-" if filtre==s else "bg"}">{l}</a>'
        for s,l in [("","Toutes"),("EN_ATTENTE","Attente"),("EN_COURS","En cours"),("EN_RETARD","Retard"),("LIVRE","Livrés"),("VALIDE","Validés")])
    body=f"""
    <div class="top"><div class="ph">Suivi des tâches</div>
      <div class="fx gp2">{f_tabs}</div>
    </div>
    <div class="ct"><div class="card">
      <table class="tbl">
        <thead><tr><th>Tâche</th><th>Activité</th><th>Service</th><th>Agent</th><th>Assignée par</th><th>Échéance</th><th>Statut</th><th></th></tr></thead>
        <tbody>{rows_html or '<tr><td colspan="8" style="text-align:center;color:var(--mu);padding:20px">Aucune tâche.</td></tr>'}</tbody>
      </table>
    </div></div>"""
    return render("Tâches",body,active="tch")

@app.route("/taches/<int:tid>")
@login_required
def tache_detail(tid):
    db=get_db()
    t=db.execute("""SELECT t.*,u.nom an,u.prenom ap,up.nom pn,up.prenom pp,a.titre at_
        FROM tache t JOIN utilisateur u ON u.id_utilisateur=t.id_assigne_a
        JOIN utilisateur up ON up.id_utilisateur=t.id_assigne_par
        JOIN activite a ON a.id_activite=t.id_activite
        WHERE t.id_tache=?""",(tid,)).fetchone()
    if not t: db.close(); flash("Introuvable.","danger"); return redirect(url_for("taches_view"))
    livs=db.execute("SELECT * FROM livrable WHERE id_tache=? ORDER BY date_soumission DESC",(tid,)).fetchall()
    histo=db.execute("""SELECT h.*,uc.nom en,uc.prenom ep FROM historique_tache h
        LEFT JOIN utilisateur uc ON uc.id_utilisateur=h.effectue_par
        WHERE h.id_tache=? ORDER BY h.date_action DESC""",(tid,)).fetchall()
    db.close()
    e=ecart(t["echeance_prevue"],t["echeance_reelle"])
    ec_html=""
    if e is not None:
        c="var(--er)" if e>0 else ("var(--wn)" if e==0 else "var(--ok)")
        l=f"+{e}j retard" if e>0 else (f"{abs(e)}j avant" if e<0 else "Dans les temps")
        ec_html=f'<span style="color:{c}">{l}</span>'
    livs_html="".join(f"""<div style="padding:9px 0;border-top:1px solid var(--bd)">
      <div class="fx ai jb"><div class="fw sm">{l['fichier_nom']}</div>
      <span class="bg-badge {badge(l['statut_validation'])[0]}">{badge(l['statut_validation'])[1]}</span></div>
      <div class="mu" style="font-size:11px">{l['date_soumission'][:16]}</div>
    </div>""" for l in livs)
    tl_html="".join(f"""<div class="tl-i">
      <div class="tl-d" style="background:var(--brand)"></div>
      <div class="tl-t mu">{h['date_action'][:16]} — {h['ep'] or ''} {h['en'] or ''}</div>
      <div class="tl-t fw sm">{h['type_action'].replace('_',' ')}</div>
      {f'<div class="mu sm">{h["statut_avant"]} → {h["statut_apres"]}</div>' if h['statut_avant'] else ''}
    </div>""" for h in histo)
    b=badge(t["statut"])
    body=f"""
    <div class="top">
      <div class="fx ai gp2"><a href="/taches" class="btn bg bsm">&larr;</a>
        <div class="ph">{t['libelle']}</div></div>
      <span class="bg-badge {b[0]}">{b[1]}</span>
    </div>
    <div class="ct"><div class="g2" style="gap:16px">
      <div>
        <div class="card"><div class="ch">Informations</div>
          <table style="width:100%;font-size:13px">
            <tr><td class="mu" style="padding:4px 0">Activité</td><td class="fw">{t['at_']}</td></tr>
            <tr><td class="mu" style="padding:4px 0">Agent</td><td>{t['ap']} {t['an']}</td></tr>
            <tr><td class="mu" style="padding:4px 0">Assignée par</td><td>{t['pp']} {t['pn']}</td></tr>
            <tr><td class="mu" style="padding:4px 0">Livrable</td><td>{t['type_livrable'].replace('_',' ')}</td></tr>
            <tr><td class="mu" style="padding:4px 0">Échéance prévue</td><td>{t['echeance_prevue']}</td></tr>
            <tr><td class="mu" style="padding:4px 0">Livré le</td><td>{t['echeance_reelle'] or '—'}</td></tr>
            <tr><td class="mu" style="padding:4px 0">Écart</td><td>{ec_html or '—'}</td></tr>
          </table>
        </div>
        <div class="card"><div class="ch">Livrables</div>
          {livs_html or '<div class="mu sm">Aucun livrable.</div>'}
        </div>
      </div>
      <div class="card"><div class="ch">Historique</div>
        <div class="tl">{tl_html or '<div class="mu sm">Aucune action.</div>'}</div>
      </div>
    </div></div>"""
    return render("Tâche",body,active="tch")


# ─────────────────────────────────────────
# GANTT
# ─────────────────────────────────────────
@app.route("/gantt")
@login_required
def gantt_view():
    uid=session["user_id"]; role=session["role"]; sid=session.get("id_service")
    db=get_db()
    acts=get_perimetre(db,uid,role,sid)
    gantt_html=""
    for a in acts:
        taches=db.execute("""SELECT t.*,u.nom an,u.prenom ap FROM tache t
            JOIN utilisateur u ON u.id_utilisateur=t.id_assigne_a
            WHERE t.id_activite=? ORDER BY t.echeance_prevue""",(a["id_activite"],)).fetchall()
        if not taches: continue
        nb=len(taches); val=sum(1 for t in taches if t["statut"]=="VALIDE")
        pct=round(100*val/max(nb,1))
        gantt_html+=f"""
        <div style="margin-bottom:18px">
          <div class="fx ai jb" style="margin-bottom:8px">
            <div class="fw sm">{a['titre']} <span class="pill" style="background:#EFF6FF;color:#1E40AF;margin-left:4px">{a['type']}</span></div>
            <div class="fx ai gp2">
              <div class="bw2" style="width:60px"><div class="bf" style="width:{pct}%;background:var(--brand)"></div></div>
              <span class="mu" style="font-size:11px">{pct}%</span>
              <span class="bg-badge {badge(a['statut'])[0]}">{badge(a['statut'])[1]}</span>
            </div>
          </div>"""
        try:
            d0=datetime.strptime(a["date_debut"],"%Y-%m-%d").date()
            d1=datetime.strptime(a["date_fin_prevue"],"%Y-%m-%d").date()
            span=max((d1-d0).days,1)
        except: d0=date.today(); span=30
        for t in taches:
            try:
                dt=datetime.strptime(t["echeance_prevue"],"%Y-%m-%d").date()
                off=max((dt-d0).days,0)
                lp=min(round(100*off/span),92)
                wp=max(round(300/span),5)
            except: lp,wp=0,10
            bc={"VALIDE":"var(--ok)","EN_RETARD":"var(--er)","LIVRE":"var(--wn)"}.get(t["statut"],"var(--brand)")
            gantt_html+=f"""
            <div class="gr">
              <div class="gl" title="{t['libelle']}">{t['libelle'][:20]}{'…' if len(t['libelle'])>20 else ''}</div>
              <div class="gt" style="height:14px">
                <div class="gb" style="left:{lp}%;width:{wp}%;background:{bc}"></div>
                <div style="position:absolute;top:0;left:{min(lp+wp+1,70)}%;font-size:9px;color:var(--mu);line-height:14px">{t['echeance_prevue']}</div>
              </div>
              <div style="width:70px;flex-shrink:0;text-align:right"><span class="bg-badge {badge(t['statut'])[0]}" style="font-size:10px">{badge(t['statut'])[1]}</span></div>
            </div>"""
        gantt_html+="</div><hr class='sep'>"
    db.close()
    legende="".join(f'<span class="fx ai gp2" style="font-size:12px"><span style="width:10px;height:7px;background:{c};border-radius:2px;display:inline-block"></span>{l}</span>'
        for c,l in [("var(--brand)","En cours"),("var(--ok)","Validé"),("var(--er)","En retard"),("var(--wn)","Livré")])
    body=f"""
    <div class="top"><div class="ph">Diagramme de Gantt</div>
      <div class="fx ai gp2">{legende}</div>
    </div>
    <div class="ct"><div class="card">
      {gantt_html or '<div class="mu sm">Aucune activité à afficher.</div>'}
    </div></div>"""
    return render("Gantt",body,active="gnt")


# ─────────────────────────────────────────
# PRODUCTIVITÉ
# ─────────────────────────────────────────
@app.route("/productivite")
@login_required
def perf_view():
    uid=session["user_id"]; role=session["role"]; sid=session.get("id_service")
    db=get_db()
    if role=="CHEF_SERVICE":
        agents=db.execute("SELECT u.* FROM utilisateur u JOIN activite a ON a.id_service=? WHERE u.id_service=? AND u.role='AGENT' GROUP BY u.id_utilisateur",(sid,sid)).fetchall()
    elif role=="DIRECTEUR":
        agents=db.execute("SELECT * FROM utilisateur WHERE id_service=? AND role IN ('AGENT','RESPONSABLE') AND actif=1",(sid,)).fetchall()
    else:
        agents=db.execute("SELECT * FROM utilisateur WHERE role IN ('AGENT','RESPONSABLE','CHEF_SERVICE') AND actif=1 ORDER BY role,nom").fetchall()
    stats=[]
    for ag in agents:
        taches=db.execute("SELECT * FROM tache WHERE id_assigne_a=?",(ag["id_utilisateur"],)).fetchall()
        total=len(taches); val=sum(1 for t in taches if t["statut"]=="VALIDE")
        ret=sum(1 for t in taches if t["statut"]=="EN_RETARD")
        dans=sum(1 for t in taches if t["statut"]=="VALIDE" and t["echeance_reelle"] and t["echeance_reelle"]<=t["echeance_prevue"])
        score=round(100*dans/max(val,1)) if val else 0
        pct=round(100*val/max(total,1))
        stats.append({"ag":ag,"total":total,"val":val,"ret":ret,"score":score,"pct":pct})
    stats.sort(key=lambda x:-x["score"])
    db.close()
    cards=""
    for s in stats:
        ag=s["ag"]
        sc=s["score"]
        cc="var(--ok)" if sc>=80 else ("var(--wn)" if sc>=50 else "var(--er)")
        cards+=f"""
        <div class="card" style="margin-bottom:12px">
          <div class="fx ai jb" style="margin-bottom:10px">
            <div class="fx ai gp2">
              <div class="av" style="width:32px;height:32px;font-size:11px;background:var(--brand)">{ag['prenom'][0]}{ag['nom'][0]}</div>
              <div><div class="fw sm">{ag['prenom']} {ag['nom']}</div>
                <div class="mu" style="font-size:11px">{ag['role']}</div></div>
            </div>
            <div style="font-size:20px;font-weight:600;color:{cc}">{sc}%</div>
          </div>
          <div class="g3" style="text-align:center;margin-bottom:10px">
            <div><div class="mu" style="font-size:11px">Total</div><div style="font-size:17px;font-weight:600">{s['total']}</div></div>
            <div><div class="mu" style="font-size:11px">Validées</div><div style="font-size:17px;font-weight:600;color:var(--ok)">{s['val']}</div></div>
            <div><div class="mu" style="font-size:11px">Retards</div><div style="font-size:17px;font-weight:600;color:var(--er)">{s['ret']}</div></div>
          </div>
          <div class="bw2"><div class="bf" style="width:{s['pct']}%;background:var(--brand)"></div></div>
        </div>"""
    body=f"""
    <div class="top"><div class="ph">Productivité des intervenants</div></div>
    <div class="ct"><div style="max-width:640px">{cards or '<div class="card mu sm">Aucun agent.</div>'}</div></div>"""
    return render("Productivité",body,active="prf")


# ─────────────────────────────────────────
# ÉCARTS DÉLAIS
# ─────────────────────────────────────────
@app.route("/ecarts")
@login_required
def ecarts_view():
    uid=session["user_id"]; role=session["role"]; sid=session.get("id_service")
    db=get_db()
    acts=get_perimetre(db,uid,role,sid)
    ids=[a["id_activite"] for a in acts]
    taches=[]
    if ids:
        ph=",".join("?"*len(ids))
        taches=db.execute(f"""
            SELECT t.*,u.nom an,u.prenom ap,a.titre at_,s.libelle svc
            FROM tache t JOIN utilisateur u ON u.id_utilisateur=t.id_assigne_a
            JOIN activite a ON a.id_activite=t.id_activite
            JOIN service s ON s.id_service=a.id_service
            WHERE t.id_activite IN ({ph}) AND t.statut NOT IN ('EN_ATTENTE')
            ORDER BY t.echeance_prevue
        """,ids).fetchall()
    db.close()
    dans=[t for t in taches if t["statut"]=="VALIDE" and t["echeance_reelle"] and t["echeance_reelle"]<=t["echeance_prevue"]]
    leger=[t for t in taches if t["echeance_reelle"] and t["echeance_reelle"]>t["echeance_prevue"] and ecart(t["echeance_prevue"],t["echeance_reelle"])<4]
    crit =[t for t in taches if t["echeance_reelle"] and ecart(t["echeance_prevue"],t["echeance_reelle"])>=4]
    en_c =[t for t in taches if not t["echeance_reelle"] and t["echeance_prevue"]<str(date.today()) and t["statut"] not in ("VALIDE",)]
    rows="".join(f"""<tr>
      <td class="fw sm">{t['libelle']}</td>
      <td class="mu sm">{t['at_']}</td>
      <td class="mu sm">{t['svc']}</td>
      <td>{t['ap']} {t['an']}</td>
      <td>{t['echeance_prevue']}</td>
      <td>{t['echeance_reelle'] or '—'}</td>
      <td>
        {f'<span style="color:var(--er);font-weight:500">+{ecart(t["echeance_prevue"],t["echeance_reelle"])}j</span>' if t["echeance_reelle"] and ecart(t["echeance_prevue"],t["echeance_reelle"])>0
         else ('<span style="color:var(--ok)">Dans les délais</span>' if t["echeance_reelle"] else '<span style="color:var(--er)">Non livré</span>')}
      </td>
      <td><span class="bg-badge {badge(t['statut'])[0]}">{badge(t['statut'])[1]}</span></td>
    </tr>""" for t in taches)
    total=max(len(taches),1)
    body=f"""
    <div class="top"><div class="ph">Mesure des écarts de délais</div></div>
    <div class="ct">
      <div class="g4" style="margin-bottom:16px">
        <div class="kp"><div class="kl">Dans les délais</div>
          <div class="kv" style="color:var(--ok)">{len(dans)}</div>
          <div class="ks">{round(100*len(dans)/total)}%</div></div>
        <div class="kp"><div class="kl">Léger retard (&lt;4j)</div>
          <div class="kv" style="color:var(--wn)">{len(leger)}</div>
          <div class="ks">{round(100*len(leger)/total)}%</div></div>
        <div class="kp"><div class="kl">Retard critique (&ge;4j)</div>
          <div class="kv" style="color:var(--er)">{len(crit)}</div>
          <div class="ks">{round(100*len(crit)/total)}%</div></div>
        <div class="kp"><div class="kl">Non livrés en retard</div>
          <div class="kv" style="color:var(--er)">{len(en_c)}</div>
          <div class="ks">{round(100*len(en_c)/total)}%</div></div>
      </div>
      <div class="card">
        <table class="tbl">
          <thead><tr><th>Tâche</th><th>Activité</th><th>Service</th><th>Agent</th>
            <th>Prévu</th><th>Réel</th><th>Écart</th><th>Statut</th></tr></thead>
          <tbody>{rows or '<tr><td colspan="8" style="text-align:center;color:var(--mu);padding:18px">Aucune donnée.</td></tr>'}</tbody>
        </table>
      </div>
    </div>"""
    return render("Écarts délais",body,active="ec")


# ─────────────────────────────────────────
# KPIs GLOBAUX (Directeur + DG)
# ─────────────────────────────────────────
@app.route("/kpi")
@login_required
@require_roles("DIRECTEUR","DG")
def kpi_global():
    db=get_db()
    services=db.execute("SELECT * FROM service").fetchall()
    rows=""; svc_data=[]
    for s in services:
        acts=db.execute("SELECT * FROM activite WHERE id_service=?",(s["id_service"],)).fetchall()
        _,val,_,ret,pct=kpi_from_acts(db,acts)
        nb=len(acts)
        type_counts={}
        for a in acts: type_counts[a["type"]]=type_counts.get(a["type"],0)+1
        dom=max(type_counts,key=type_counts.get) if type_counts else "—"
        svc_data.append({"svc":s,"nb":nb,"val":val,"ret":ret,"pct":pct,"dom":dom})
        rows+=f"""<tr>
          <td class="fw sm">{s['libelle']}</td>
          <td>{nb}</td>
          <td><div class="fx ai gp2"><div class="bw2" style="width:80px"><div class="bf" style="width:{pct}%;background:var(--brand)"></div></div><span class="mu sm">{pct}%</span></div></td>
          <td style="color:var(--er)">{ret}</td>
          <td><span class="pill" style="background:#EFF6FF;color:#1E40AF">{dom}</span></td>
        </tr>"""

    total_acts=sum(x["nb"] for x in svc_data)
    total_val=sum(x["val"] for x in svc_data)
    total_ret=sum(x["ret"] for x in svc_data)
    pct_global=round(100*total_val/max(sum(db.execute("SELECT COUNT(*) FROM tache").fetchone()[0] for _ in [1]),1))

    all_agents=db.execute("""
        SELECT u.nom,u.prenom,u.role,
               COUNT(t.id_tache) total, SUM(t.statut='VALIDE') val,
               SUM(t.statut='EN_RETARD') ret,s.libelle svc
        FROM utilisateur u
        LEFT JOIN tache t ON t.id_assigne_a=u.id_utilisateur
        LEFT JOIN service s ON s.id_service=u.id_service
        WHERE u.role IN ('AGENT','RESPONSABLE','CHEF_SERVICE')
        GROUP BY u.id_utilisateur ORDER BY val DESC LIMIT 8
    """).fetchall()
    db.close()

    agent_rows="".join(f"""
    <div class="gr" style="border-top:{'1px solid var(--bd)' if i>0 else 'none'}">
      <div class="gl fw">{ag['prenom']} {ag['nom']}</div>
      <div style="width:70px;flex-shrink:0;font-size:11px;color:var(--mu)">{ag['svc'][:12] if ag['svc'] else ''}</div>
      <div class="gt"><div class="gb" style="width:{round(100*(ag['val'] or 0)/max(ag['total'],1))}%;background:var(--brand);left:0"></div></div>
      <div class="gp">{ag['val'] or 0}/{ag['total'] or 0}</div>
    </div>""" for i,ag in enumerate(all_agents))

    body=f"""
    <div class="top"><div class="ph">KPIs globaux</div><span class="mu sm">Vue consolidée — toute la structure</span></div>
    <div class="ct">
      <div class="g4" style="margin-bottom:16px">
        <div class="kp"><div class="kl">Activités totales</div><div class="kv" style="color:var(--brand)">{total_acts}</div></div>
        <div class="kp"><div class="kl">Tâches validées</div><div class="kv" style="color:var(--ok)">{total_val}</div></div>
        <div class="kp"><div class="kl">Retards actifs</div><div class="kv" style="color:var(--er)">{total_ret}</div></div>
        <div class="kp"><div class="kl">Services actifs</div><div class="kv">{len(services)}</div></div>
      </div>
      <div class="g2" style="gap:16px">
        <div class="card">
          <div class="ch">Complétion par service</div>
          <table class="tbl">
            <thead><tr><th>Service</th><th>Activités</th><th>Complétion</th><th>Retards</th><th>Type dominant</th></tr></thead>
            <tbody>{rows or '<tr><td colspan="5" style="text-align:center;color:var(--mu);padding:18px">Aucun service.</td></tr>'}</tbody>
          </table>
        </div>
        <div class="card">
          <div class="ch">Top intervenants</div>
          {agent_rows or '<div class="mu sm">Aucune donnée.</div>'}
        </div>
      </div>
    </div>"""
    return render("KPIs globaux",body,active="kpi")


# ─────────────────────────────────────────
# AVIS & SIGNALEMENTS (Chef de service +)
# ─────────────────────────────────────────
@app.route("/avis", methods=["GET","POST"])
@login_required
@require_roles("CHEF_SERVICE","DIRECTEUR","DG")
def avis_view():
    uid=session["user_id"]
    db=get_db()
    if request.method=="POST":
        aid=int(request.form["id_avis"])
        nouveau_statut=request.form["statut"]
        db.execute("UPDATE avis SET statut=? WHERE id_avis=?",(nouveau_statut,aid))
        db.commit()
        flash("Avis mis à jour.","success")
        db.close(); return redirect(url_for("avis_view"))
    avis=db.execute("""
        SELECT av.*,u.nom an,u.prenom ap FROM avis av
        JOIN utilisateur u ON u.id_utilisateur=av.id_auteur
        ORDER BY av.date_soumission DESC
    """).fetchall()
    db.close()
    type_color={"SIGNALEMENT":"al-er","FONCTIONNALITE":"al-in","SUGGESTION":"al-wn"}
    cards="".join(f"""
    <div class="card" style="margin-bottom:12px">
      <div class="fx ai jb" style="margin-bottom:8px">
        <div class="fx ai gp2">
          <span class="pill {'bok' if a['type']=='FONCTIONNALITE' else ('ber' if a['type']=='SIGNALEMENT' else '')}" style="font-size:11px">{a['type'].replace('_',' ')}</span>
          {f'<span class="pill" style="background:#F1F5F9;color:#475569;font-size:11px">{a["cible"]}</span>' if a['cible'] else ''}
        </div>
        <span class="mu" style="font-size:11px">{a['date_soumission'][:10]} — {a['ap']} {a['an']}</span>
      </div>
      <div class="sm" style="margin-bottom:10px">{a['contenu']}</div>
      <div class="fx ai gp2">
        <span class="bg-badge {'bv' if a['statut']=='TRAITE' else 'bw'}">{a['statut']}</span>
        {f'''<form method="POST" style="display:inline">
          <input type="hidden" name="id_avis" value="{a['id_avis']}">
          <input type="hidden" name="statut" value="EN_TRAITEMENT">
          <button class="btn bg bsm">Prendre en charge</button>
        </form>
        <form method="POST" style="display:inline">
          <input type="hidden" name="id_avis" value="{a['id_avis']}">
          <input type="hidden" name="statut" value="TRAITE">
          <button class="btn bok bsm">Marquer traité</button>
        </form>''' if a['statut']!='TRAITE' else ''}
      </div>
    </div>""" for a in avis)
    body=f"""
    <div class="top"><div class="ph">Avis &amp; signalements</div>
      <span class="mu sm">{sum(1 for a in avis if a['statut']=='SOUMIS')} en attente</span>
    </div>
    <div class="ct"><div style="max-width:640px">{cards or '<div class="card mu sm">Aucun avis.</div>'}</div></div>"""
    return render("Avis & signalements",body,active="av")


# ─────────────────────────────────────────
# BOÎTE À IDÉES
# ─────────────────────────────────────────
@app.route("/idees")
@login_required
def idees_view():
    db=get_db()
    idees=db.execute("""
        SELECT i.*,u.nom an,u.prenom ap FROM idee i
        JOIN utilisateur u ON u.id_utilisateur=i.id_auteur
        ORDER BY i.nb_votes DESC,i.date_soumission DESC
    """).fetchall()
    db.close()
    cards="".join(f"""
    <div class="card" style="margin-bottom:12px">
      <div class="fx ai jb" style="margin-bottom:6px">
        <div class="fw sm">{i['titre']}</div>
        <div class="fx ai gp2">
          <form method="POST" action="/idees/{i['id_idee']}/vote" style="display:inline">
            <button class="btn bg bsm" style="font-size:16px;padding:3px 9px">&#9650;</button>
          </form>
          <span style="font-size:14px;font-weight:600;color:var(--brand)">{i['nb_votes']}</span>
        </div>
      </div>
      <div class="mu sm" style="margin-bottom:6px">{i['contenu'][:130]}{'…' if len(i['contenu'])>130 else ''}</div>
      <div class="fx ai jb">
        <span class="mu" style="font-size:11px">{i['ap']} {i['an']} · {i['date_soumission'][:10]}</span>
        <span class="bg-badge {'bv' if i['statut']=='RETENUE' else 'bw'}">{i['statut']}</span>
      </div>
    </div>""" for i in idees)
    body=f"""
    <div class="top"><div class="ph">Boîte à idées institutionnelle</div>
      <span class="mu sm">{len(idees)} idées soumises</span>
    </div>
    <div class="ct"><div style="max-width:640px">{cards or '<div class="card mu sm">Aucune idée.</div>'}</div></div>"""
    return render("Boîte à idées",body,active="id")

@app.route("/idees/<int:iid>/vote",methods=["POST"])
@login_required
def voter_idee(iid):
    db=get_db(); db.execute("UPDATE idee SET nb_votes=nb_votes+1 WHERE id_idee=?",(iid,)); db.commit(); db.close()
    return redirect(url_for("idees_view"))


# ─────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────
@app.route("/notifications")
@login_required
def notifs_view():
    uid=session["user_id"]; db=get_db()
    notifs=db.execute("SELECT * FROM notification WHERE id_destinataire=? ORDER BY date_envoi DESC LIMIT 60",(uid,)).fetchall()
    db.execute("UPDATE notification SET lue=1 WHERE id_destinataire=?",(uid,)); db.commit(); db.close()
    tc={"ASSIGNATION":"#EFF6FF:#1E40AF","VALIDATION":"#F0FDF4:#166534","REJET":"#FEF2F2:#991B1B","RETARD":"#FFF7ED:#92400E","INFO":"#F8FAFC:#475569","SIGNALEMENT":"#FEF2F2:#991B1B"}
    rows="".join(f"""
    <div style="padding:10px 0;border-top:1px solid var(--bd);display:flex;gap:10px;align-items:flex-start">
      <span class="pill" style="background:{tc.get(n['type'],'#F8FAFC:#475569').split(':')[0]};color:{tc.get(n['type'],'#F8FAFC:#475569').split(':')[1]};flex-shrink:0">{n['type']}</span>
      <div style="flex:1"><div class="sm">{n['message']}</div>
        <div class="mu" style="font-size:11px">{n['date_envoi'][:16]}</div></div>
      {'<span style="width:6px;height:6px;border-radius:50%;background:var(--in);flex-shrink:0;margin-top:6px"></span>' if not n['lue'] else ''}
    </div>""" for n in notifs)
    body=f"""
    <div class="top"><div class="ph">Notifications</div></div>
    <div class="ct"><div class="card">{rows or '<div class="mu sm">Aucune notification.</div>'}</div></div>"""
    return render("Notifications",body,active="nt")


