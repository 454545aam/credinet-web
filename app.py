from flask import Flask, request, render_template
import psycopg2
import os
import urllib.parse as up

app = Flask(__name__)

def get_connection():
    db_url = os.environ["DATABASE_URL"]

    # Render PostgreSQL requiere SSL obligatorio
    return psycopg2.connect(db_url, sslmode="require")

@app.route("/", methods=["GET", "POST"])
def index():
    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"]
        cur.execute("INSERT INTO usuarios (nombre) VALUES (%s);", (nombre,))
        conn.commit()

    cur.execute("SELECT id, nombre FROM usuarios;")
    usuarios = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("index.html", usuarios=usuarios)

if __name__ == "__main__":
    app.run(debug=True)
