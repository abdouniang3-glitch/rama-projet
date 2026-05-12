-- ============================================================
--  RAMA — Schéma PostgreSQL partagé
--  À exécuter UNE SEULE FOIS sur la base PostgreSQL Render
--  (via la console Render ou psql)
-- ============================================================

CREATE TABLE IF NOT EXISTS service (
    id_service   SERIAL PRIMARY KEY,
    libelle      TEXT NOT NULL,
    description  TEXT
);

CREATE TABLE IF NOT EXISTS utilisateur (
    id_utilisateur SERIAL PRIMARY KEY,
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
    id_activite     SERIAL PRIMARY KEY,
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
    id_tache         SERIAL PRIMARY KEY,
    libelle          TEXT NOT NULL,
    type_livrable    TEXT NOT NULL,
    description      TEXT,
    echeance_prevue  TEXT NOT NULL,
    echeance_reelle  TEXT,
    statut           TEXT DEFAULT 'EN_ATTENTE',
    id_activite      INTEGER REFERENCES activite(id_activite),
    id_assigne_par   INTEGER REFERENCES utilisateur(id_utilisateur),
    id_assigne_a     INTEGER REFERENCES utilisateur(id_utilisateur),
    date_assignation TEXT DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS')
);

CREATE TABLE IF NOT EXISTS livrable (
    id_livrable       SERIAL PRIMARY KEY,
    id_tache          INTEGER REFERENCES tache(id_tache),
    fichier_nom       TEXT NOT NULL,
    commentaire       TEXT,
    date_soumission   TEXT DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
    statut_validation TEXT DEFAULT 'EN_ATTENTE',
    id_validateur     INTEGER REFERENCES utilisateur(id_utilisateur),
    date_validation   TEXT,
    motif_rejet       TEXT
);

CREATE TABLE IF NOT EXISTS historique_tache (
    id_historique        SERIAL PRIMARY KEY,
    id_tache             INTEGER REFERENCES tache(id_tache),
    type_action          TEXT NOT NULL,
    id_utilisateur_avant INTEGER,
    id_utilisateur_apres INTEGER,
    statut_avant         TEXT,
    statut_apres         TEXT,
    motif                TEXT,
    effectue_par         INTEGER REFERENCES utilisateur(id_utilisateur),
    date_action          TEXT DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS')
);

CREATE TABLE IF NOT EXISTS notification (
    id_notification SERIAL PRIMARY KEY,
    id_destinataire INTEGER REFERENCES utilisateur(id_utilisateur),
    type            TEXT NOT NULL,
    message         TEXT NOT NULL,
    lue             INTEGER DEFAULT 0,
    date_envoi      TEXT DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
    id_tache        INTEGER REFERENCES tache(id_tache)
);

CREATE TABLE IF NOT EXISTS idee (
    id_idee         SERIAL PRIMARY KEY,
    id_auteur       INTEGER REFERENCES utilisateur(id_utilisateur),
    titre           TEXT NOT NULL,
    contenu         TEXT NOT NULL,
    nb_votes        INTEGER DEFAULT 0,
    statut          TEXT DEFAULT 'SOUMISE',
    date_soumission TEXT DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS')
);

CREATE TABLE IF NOT EXISTS avis (
    id_avis         SERIAL PRIMARY KEY,
    id_auteur       INTEGER REFERENCES utilisateur(id_utilisateur),
    type            TEXT NOT NULL,
    cible           TEXT,
    contenu         TEXT NOT NULL,
    statut          TEXT DEFAULT 'SOUMIS',
    date_soumission TEXT DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS')
);
