
import os
exec(open("rama_management.py").read().split("if __name__")[0])
init_db()

if __name__ == "__main__":
    app.run()
