# Créer un main.py intelligent
with open("main.py", "w") as f:
    f.write("""
import os

vue = os.environ.get("VUE", "management")

if vue == "agent":
    with open("rama_agent (3) (1).py") as f2:
        exec(f2.read().split("if __name__")[0], globals())
elif vue == "responsable":
    with open("rama_responsable (3).py") as f2:
        exec(f2.read().split("if __name__")[0], globals())
else:
    with open("rama_management (2).py") as f2:
        exec(f2.read().split("if __name__")[0], globals())

init_db()
""")
print("✅ main.py créé")
