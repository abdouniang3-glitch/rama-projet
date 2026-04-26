-- ============================================================
--  RAMA — Système de Reporting des Activités et Monitoring
--  Schéma relationnel MySQL — Semestre 3 L2 Informatique
--  Professeur : Papa DIOP | Année : 2025-2026
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS idee, avis, notification, historique_tache,
                     livrable, tache, activite, utilisateur, service;
SET FOREIGN_KEY_CHECKS = 1;

-- ------------------------------------------------------------
-- 1. SERVICE
-- ------------------------------------------------------------
CREATE TABLE service (
    id_service      INT AUTO_INCREMENT PRIMARY KEY,
    libelle         VARCHAR(100)  NOT NULL,
    description     TEXT,
    id_directeur    INT,          -- FK vers utilisateur (ajoutée après)
    date_creation   DATETIME      DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- 2. UTILISATEUR  (relation réflexive id_superieur → N+1)
-- ------------------------------------------------------------
CREATE TABLE utilisateur (
    id_utilisateur  INT AUTO_INCREMENT PRIMARY KEY,
    nom             VARCHAR(80)   NOT NULL,
    prenom          VARCHAR(80)   NOT NULL,
    email           VARCHAR(150)  NOT NULL UNIQUE,
    mot_de_passe    VARCHAR(255)  NOT NULL,          -- bcrypt hash
    role            ENUM('DG','DIRECTEUR','CHEF_SERVICE',
                         'RESPONSABLE','AGENT')      NOT NULL,
    id_superieur    INT           DEFAULT NULL,       -- N+1 (self-join)
    id_service      INT           DEFAULT NULL,
    actif           TINYINT(1)    DEFAULT 1,
    date_creation   DATETIME      DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_util_superieur FOREIGN KEY (id_superieur)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE SET NULL ON UPDATE CASCADE,

    CONSTRAINT fk_util_service FOREIGN KEY (id_service)
        REFERENCES service(id_service)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- FK différée : directeur du service → utilisateur
ALTER TABLE service
    ADD CONSTRAINT fk_svc_directeur FOREIGN KEY (id_directeur)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE SET NULL ON UPDATE CASCADE;

-- ------------------------------------------------------------
-- 3. ACTIVITE
-- ------------------------------------------------------------
CREATE TABLE activite (
    id_activite       INT AUTO_INCREMENT PRIMARY KEY,
    titre             VARCHAR(200)  NOT NULL,
    type              ENUM('MISSION','ATELIER','SALON','FORUM',
                           'COLLOQUE','SEMINAIRE','AUTRE') NOT NULL,
    description       TEXT,
    date_debut        DATE          NOT NULL,
    date_fin_prevue   DATE          NOT NULL,
    date_fin_reelle   DATE          DEFAULT NULL,
    statut            ENUM('PLANIFIEE','EN_COURS','ACHEVEE',
                           'ANNULEE')  DEFAULT 'PLANIFIEE',
    id_service        INT           NOT NULL,
    id_createur       INT           NOT NULL,
    date_creation     DATETIME      DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_act_service  FOREIGN KEY (id_service)
        REFERENCES service(id_service)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT fk_act_createur FOREIGN KEY (id_createur)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- 4. TACHE  (id_assigne_par = N+1 ; id_assigne_a = N)
-- ------------------------------------------------------------
CREATE TABLE tache (
    id_tache          INT AUTO_INCREMENT PRIMARY KEY,
    libelle           VARCHAR(200)  NOT NULL,
    type_livrable     ENUM('CONVOCATION','TERMES_REFERENCE',
                           'RAPPORT','COMPTE_RENDU','PV',
                           'FICHE_TECHNIQUE','DOSSIER_MARCHE',
                           'APPEL_CANDIDATURES','AUTRE') NOT NULL,
    description       TEXT,
    echeance_prevue   DATE          NOT NULL,
    echeance_reelle   DATE          DEFAULT NULL,
    statut            ENUM('EN_ATTENTE','EN_COURS','LIVRE',
                           'VALIDE','REJETE','EN_RETARD') DEFAULT 'EN_ATTENTE',
    id_activite       INT           NOT NULL,
    id_assigne_par    INT           NOT NULL,   -- N+1
    id_assigne_a      INT           NOT NULL,   -- N
    date_assignation  DATETIME      DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_tache_activite  FOREIGN KEY (id_activite)
        REFERENCES activite(id_activite)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT fk_tache_assigne_par FOREIGN KEY (id_assigne_par)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT fk_tache_assigne_a  FOREIGN KEY (id_assigne_a)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- 5. LIVRABLE
-- ------------------------------------------------------------
CREATE TABLE livrable (
    id_livrable         INT AUTO_INCREMENT PRIMARY KEY,
    id_tache            INT           NOT NULL,
    fichier_url         VARCHAR(500)  NOT NULL,
    type_fichier        VARCHAR(50),                 -- pdf, docx, xlsx…
    commentaire         TEXT,
    date_soumission     DATETIME      DEFAULT CURRENT_TIMESTAMP,
    statut_validation   ENUM('EN_ATTENTE','VALIDE','REJETE') DEFAULT 'EN_ATTENTE',
    id_validateur       INT           DEFAULT NULL,
    date_validation     DATETIME      DEFAULT NULL,
    motif_rejet         TEXT          DEFAULT NULL,

    CONSTRAINT fk_livrable_tache     FOREIGN KEY (id_tache)
        REFERENCES tache(id_tache)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT fk_livrable_validateur FOREIGN KEY (id_validateur)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- 6. HISTORIQUE_TACHE  (traçabilité réaffectations)
-- ------------------------------------------------------------
CREATE TABLE historique_tache (
    id_historique       INT AUTO_INCREMENT PRIMARY KEY,
    id_tache            INT           NOT NULL,
    type_action         ENUM('ASSIGNATION_INITIALE','REASSIGNATION',
                             'RETRAIT','CHANGEMENT_STATUT',
                             'CHANGEMENT_ECHEANCE') NOT NULL,
    id_utilisateur_avant INT          DEFAULT NULL,
    id_utilisateur_apres INT          DEFAULT NULL,
    statut_avant        VARCHAR(50)   DEFAULT NULL,
    statut_apres        VARCHAR(50)   DEFAULT NULL,
    motif               TEXT,
    effectue_par        INT           NOT NULL,      -- l'acteur qui a fait l'action
    date_action         DATETIME      DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_histo_tache    FOREIGN KEY (id_tache)
        REFERENCES tache(id_tache)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT fk_histo_avant    FOREIGN KEY (id_utilisateur_avant)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE SET NULL ON UPDATE CASCADE,

    CONSTRAINT fk_histo_apres    FOREIGN KEY (id_utilisateur_apres)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE SET NULL ON UPDATE CASCADE,

    CONSTRAINT fk_histo_acteur   FOREIGN KEY (effectue_par)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- 7. NOTIFICATION
-- ------------------------------------------------------------
CREATE TABLE notification (
    id_notification  INT AUTO_INCREMENT PRIMARY KEY,
    id_destinataire  INT           NOT NULL,
    type             ENUM('ASSIGNATION','RETARD','VALIDATION',
                          'REJET','SIGNALEMENT','INFO') NOT NULL,
    message          TEXT          NOT NULL,
    lue              TINYINT(1)    DEFAULT 0,
    date_envoi       DATETIME      DEFAULT CURRENT_TIMESTAMP,
    id_tache         INT           DEFAULT NULL,
    id_activite      INT           DEFAULT NULL,

    CONSTRAINT fk_notif_dest     FOREIGN KEY (id_destinataire)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT fk_notif_tache    FOREIGN KEY (id_tache)
        REFERENCES tache(id_tache)
        ON DELETE SET NULL ON UPDATE CASCADE,

    CONSTRAINT fk_notif_activite FOREIGN KEY (id_activite)
        REFERENCES activite(id_activite)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- 8. AVIS  (sur fonctionnalités ou signalement compromission)
-- ------------------------------------------------------------
CREATE TABLE avis (
    id_avis          INT AUTO_INCREMENT PRIMARY KEY,
    id_auteur        INT           NOT NULL,
    type             ENUM('FONCTIONNALITE','SIGNALEMENT',
                          'SUGGESTION') NOT NULL,
    cible            VARCHAR(100),   -- ex: 'module_taches', 'interface'
    contenu          TEXT          NOT NULL,
    statut           ENUM('SOUMIS','EN_TRAITEMENT','TRAITE',
                          'REJETE') DEFAULT 'SOUMIS',
    date_soumission  DATETIME      DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_avis_auteur FOREIGN KEY (id_auteur)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- 9. IDEE  (boîte à idées institutionnelle)
-- ------------------------------------------------------------
CREATE TABLE idee (
    id_idee          INT AUTO_INCREMENT PRIMARY KEY,
    id_auteur        INT           NOT NULL,
    titre            VARCHAR(200)  NOT NULL,
    contenu          TEXT          NOT NULL,
    nb_votes         INT           DEFAULT 0,
    statut           ENUM('SOUMISE','EN_ETUDE','RETENUE',
                          'REJETEE') DEFAULT 'SOUMISE',
    date_soumission  DATETIME      DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_idee_auteur FOREIGN KEY (id_auteur)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- INDEX (performances des requêtes KPI et Gantt)
-- ============================================================
CREATE INDEX idx_activite_service   ON activite(id_service);
CREATE INDEX idx_activite_statut    ON activite(statut);
CREATE INDEX idx_activite_type      ON activite(type);
CREATE INDEX idx_tache_activite     ON tache(id_activite);
CREATE INDEX idx_tache_assigne_a    ON tache(id_assigne_a);
CREATE INDEX idx_tache_statut       ON tache(statut);
CREATE INDEX idx_tache_echeance     ON tache(echeance_prevue);
CREATE INDEX idx_histo_tache        ON historique_tache(id_tache);
CREATE INDEX idx_notif_dest_lue     ON notification(id_destinataire, lue);
CREATE INDEX idx_util_superieur     ON utilisateur(id_superieur);
CREATE INDEX idx_util_service       ON utilisateur(id_service);

-- ============================================================
-- VUES UTILES
-- ============================================================

-- Vue : tâches en retard (pour alertes DG et notifications)
CREATE OR REPLACE VIEW v_taches_retard AS
SELECT
    t.id_tache,
    t.libelle,
    t.echeance_prevue,
    DATEDIFF(CURDATE(), t.echeance_prevue) AS jours_retard,
    t.statut,
    u.nom AS agent,
    u.prenom AS agent_prenom,
    a.titre AS activite,
    a.type  AS type_activite,
    s.libelle AS service
FROM tache t
JOIN utilisateur u  ON u.id_utilisateur = t.id_assigne_a
JOIN activite a     ON a.id_activite    = t.id_activite
JOIN service s      ON s.id_service     = a.id_service
WHERE t.statut NOT IN ('VALIDE','ANNULEE')
  AND t.echeance_prevue < CURDATE();

-- Vue : productivité par intervenant
CREATE OR REPLACE VIEW v_productivite AS
SELECT
    u.id_utilisateur,
    u.nom,
    u.prenom,
    u.role,
    s.libelle AS service,
    COUNT(t.id_tache)                                        AS total_taches,
    SUM(t.statut = 'VALIDE')                                 AS taches_validees,
    SUM(t.statut = 'VALIDE'
        AND (t.echeance_reelle IS NULL
             OR t.echeance_reelle <= t.echeance_prevue))     AS dans_les_delais,
    ROUND(
      100.0 * SUM(t.statut = 'VALIDE'
                  AND (t.echeance_reelle IS NULL
                       OR t.echeance_reelle <= t.echeance_prevue))
            / NULLIF(COUNT(t.id_tache), 0), 1)               AS taux_respect_delais
FROM utilisateur u
LEFT JOIN tache t   ON t.id_assigne_a = u.id_utilisateur
LEFT JOIN service s ON s.id_service   = u.id_service
GROUP BY u.id_utilisateur, u.nom, u.prenom, u.role, s.libelle;

-- Vue : écarts délais par tâche
CREATE OR REPLACE VIEW v_ecarts_delais AS
SELECT
    t.id_tache,
    t.libelle,
    t.echeance_prevue,
    t.echeance_reelle,
    DATEDIFF(t.echeance_reelle, t.echeance_prevue) AS ecart_jours,
    CASE
        WHEN t.echeance_reelle IS NULL                          THEN 'en_cours'
        WHEN t.echeance_reelle <= t.echeance_prevue             THEN 'dans_les_delais'
        WHEN DATEDIFF(t.echeance_reelle, t.echeance_prevue) <= 3 THEN 'leger_retard'
        ELSE 'retard_critique'
    END AS categorie_ecart,
    a.titre  AS activite,
    a.type   AS type_activite,
    s.libelle AS service,
    u.nom    AS agent
FROM tache t
JOIN activite    a ON a.id_activite   = t.id_activite
JOIN service     s ON s.id_service    = a.id_service
JOIN utilisateur u ON u.id_utilisateur = t.id_assigne_a;

-- Vue : type d'activités dominant par service
CREATE OR REPLACE VIEW v_activite_par_service AS
SELECT
    s.id_service,
    s.libelle AS service,
    a.type,
    COUNT(*) AS nb_activites
FROM activite a
JOIN service s ON s.id_service = a.id_service
GROUP BY s.id_service, s.libelle, a.type
ORDER BY s.id_service, nb_activites DESC;

-- ============================================================
-- DONNÉES DE TEST (optionnel — à retirer en production)
-- ============================================================
INSERT INTO service (libelle, description) VALUES
    ('Direction administrative', 'Gestion admin. et RH'),
    ('Direction technique',      'Projets et systèmes informatiques'),
    ('Direction financière',     'Budget, comptabilité, marchés');

INSERT INTO utilisateur (nom, prenom, email, mot_de_passe, role, id_service) VALUES
    ('DIOP',   'Amadou',  'dg@rama.sn',         '$2b$12$hash_dg',   'DG',           NULL),
    ('SARR',   'Fatou',   'dir.admin@rama.sn',  '$2b$12$hash_dir1', 'DIRECTEUR',    1),
    ('NDIAYE', 'Moussa',  'dir.tech@rama.sn',   '$2b$12$hash_dir2', 'DIRECTEUR',    2),
    ('FALL',   'Khady',   'chef1@rama.sn',      '$2b$12$hash_c1',   'CHEF_SERVICE', 1),
    ('BA',     'Ibrahim', 'resp1@rama.sn',      '$2b$12$hash_r1',   'RESPONSABLE',  1),
    ('KANE',   'Aissatou','agent1@rama.sn',     '$2b$12$hash_a1',   'AGENT',        1);

-- Mise à jour des supérieurs hiérarchiques
UPDATE utilisateur SET id_superieur = 1 WHERE email = 'dir.admin@rama.sn';
UPDATE utilisateur SET id_superieur = 1 WHERE email = 'dir.tech@rama.sn';
UPDATE utilisateur SET id_superieur = 2 WHERE email = 'chef1@rama.sn';
UPDATE utilisateur SET id_superieur = 4 WHERE email = 'resp1@rama.sn';
UPDATE utilisateur SET id_superieur = 5 WHERE email = 'agent1@rama.sn';

INSERT INTO activite (titre, type, date_debut, date_fin_prevue, statut, id_service, id_createur)
VALUES ('Atelier national RAMA 2026', 'ATELIER', '2026-04-01', '2026-04-30', 'EN_COURS', 1, 2);

INSERT INTO tache (libelle, type_livrable, echeance_prevue, statut, id_activite, id_assigne_par, id_assigne_a)
VALUES
    ('Rédiger les termes de référence', 'TERMES_REFERENCE', '2026-04-10', 'VALIDE',     1, 5, 6),
    ('Produire la convocation',         'CONVOCATION',       '2026-04-12', 'EN_COURS',   1, 5, 6),
    ('Rédiger le rapport final',        'RAPPORT',           '2026-04-28', 'EN_ATTENTE', 1, 5, 6);
