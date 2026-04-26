import os, hashlib, sqlite3

vue = os.environ.get("VUE", "management")

if vue == "agent":
    with open("rama_agent (3) (1).py") as f:
        code = f.read().split("if __name__")[0]
elif vue == "responsable":
    with open("rama_responsable (3).py") as f:
        code = f.read().split("if __name__")[0]
else:
    with open("rama_management (2).py") as f:
        code = f.read().split("if __name__")[0]

exec(code, globals())
init_db()

# Créer les utilisateurs de démo si absents
def seed():
    db = sqlite3.connect('rama.db')
    h = hashlib.sha256(b"admin").hexdigest()
    users = [
        ("resp@rama.sn", h, "responsable", "Amadou", "DIOP"),
        ("agent@rama.sn", h, "agent", "Aissa", "KANE"),
        ("dg@rama.sn", h, "dg", "Directeur", "General"),
        ("chef@rama.sn", h, "chef_service", "Chef", "Service"),
    ]
    for email, pwd, role, prenom, nom in users:
        try:
            db.execute(
                "INSERT OR IGNORE INTO utilisateur(email, mot_de_passe, role, prenom, nom) VALUES(?,?,?,?,?)",
                (email, pwd, role, prenom, nom)
            )
        except:
            pass
    db.commit()
    db.close()

seed()

application = app
