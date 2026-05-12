# ============================================================
#  RAMA — db_helper.py
#  Couche de compatibilité SQLite → PostgreSQL partagée
#  À déployer dans le repo et importer dans chaque app
# ============================================================

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get("DATABASE_URL", "")


# ─── Row compatible sqlite3 (accès par nom ET par index) ───
class Row(dict):
    """Imite sqlite3.Row : row['col'] ET row[0] fonctionnent."""
    def __init__(self, description, values):
        keys = [d[0] for d in description]
        super().__init__(zip(keys, values))
        self._values = list(values)
        self._keys   = keys

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)

    def keys(self):
        return self._keys


# ─── Curseur wrapper ───
class WrappedCursor:
    def __init__(self, cur):
        self._cur = cur

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        return Row(self._cur.description, row)

    def fetchall(self):
        rows = self._cur.fetchall()
        if not rows:
            return []
        return [Row(self._cur.description, r) for r in rows]


# ─── Connexion wrapper ───
class DB:
    def __init__(self, conn):
        self._conn = conn
        self._cur  = conn.cursor()

    # Convertit ? → %s et corrige les fonctions SQLite
    @staticmethod
    def _fix(sql):
        sql = sql.replace("?", "%s")
        sql = sql.replace("datetime('now')", "NOW()")
        sql = sql.replace("date('now')",     "CURRENT_DATE")
        return sql

    def execute(self, sql, params=None):
        sql = self._fix(sql)
        if params:
            self._cur.execute(sql, params)
        else:
            self._cur.execute(sql)
        return WrappedCursor(self._cur)

    def executemany(self, sql, params_list):
        sql = self._fix(sql)
        self._cur.executemany(sql, params_list)

    def executescript(self, sql):
        """Exécute plusieurs instructions séparées par ';'."""
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                stmt = self._fix(stmt)
                try:
                    self._cur.execute(stmt)
                except Exception:
                    pass  # Ignore "table already exists" etc.

    def commit(self):
        self._conn.commit()

    def close(self):
        try:
            self._cur.close()
            self._conn.close()
        except Exception:
            pass


def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return DB(conn)
