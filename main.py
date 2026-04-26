import os

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

# Rendre app accessible à gunicorn
application = app
