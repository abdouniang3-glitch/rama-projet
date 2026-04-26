import os

with open("rama_management (2).py") as f:
    code = f.read().split("if __name__")[0]
    exec(code, globals())

init_db()
