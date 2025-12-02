# app.py
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import psycopg2
import os
from datetime import datetime

# -------------------- PILA PERSONALIZADA --------------------
class PilaUsuarios:
    def __init__(self, limite=5):
        self.limite = limite
        self.elementos = []

    def push(self, valor):
        if valor in self.elementos:
            self.elementos.remove(valor)
        self.elementos.append(valor)
        if len(self.elementos) > self.limite:
            self.elementos.pop(0)

    def pop(self):
        return self.elementos.pop() if self.elementos else None

    def tope(self):
        return self.elementos[-1] if self.elementos else None

    def esta_vacia(self):
        return len(self.elementos) == 0

    def obtener_elementos(self):
        return list(reversed(self.elementos))

    def obtener(self):
        return self.obtener_elementos()

historial_login = PilaUsuarios(limite=5)

# -------------------- CONFIGURACIÓN --------------------
app = Flask(__name__, template_folder="templates")
app.secret_key = 'secret-key'

def get_connection():
    db_url = os.environ["DATABASE_URL"]
    return psycopg2.connect(db_url, sslmode="require")

# -------------------- INICIALIZACIÓN DE BASE DE DATOS --------------------
def init_db():
    admin_username = "admin"
    admin_password = "1234"
    admin_rol = "ADMIN"
    conn = get_connection()
    cur = conn.cursor()
    
    # Crear tabla usuarios
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(100) NOT NULL,
            fecha_creacion DATE,
            rol VARCHAR(10) DEFAULT 'ALUMNO'
        );
    """)
    
    # Crear tabla alumnos
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alumnos (
            matricula VARCHAR(20) PRIMARY KEY,
            nombre VARCHAR(100),
            carrera VARCHAR(100),
            semestre INTEGER,
            deuda NUMERIC(10,2)
        );
    """)
    
    # Verificar usuario admin
    cur.execute("SELECT id FROM usuarios WHERE username=%s", (admin_username,))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO usuarios (username, password, fecha_creacion, rol)
            VALUES (%s, %s, %s, %s)
        """, (admin_username, admin_password, datetime.today().date(), admin_rol))
    else:
        cur.execute("""
            UPDATE usuarios SET password=%s, rol=%s WHERE username=%s
        """, (admin_password, admin_rol, admin_username))
    
    conn.commit()
    cur.close()
    conn.close()

# -------------------- RUTAS --------------------
@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json', mimetype='application/json')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.route("/")
def home():
    return render_template("homeshell.html")
@app.route("/juego")
def juego ():
    return render_template("juego.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            return render_template("login.html", error="Faltan datos", historial=historial_login.obtener())
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, rol FROM usuarios WHERE username=%s AND password=%s", (username, password))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            id_usuario, rol = row
            rol_str = str(rol).upper() if rol else "ALUMNO"
            session['user_id'] = id_usuario
            session['rol'] = rol_str
            session['username'] = username
            historial_login.push(username)
            if rol_str == "ADMIN":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("ver_deuda_alumno"))
        else:
            return render_template("login.html", error="Usuario o contraseña incorrectos", historial=historial_login.obtener())
    return render_template("login.html", historial=historial_login.obtener())

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/registro", methods=["POST"])
def registro():
    username = request.form.get("username")
    password = request.form.get("password")
    if not username or not password:
        return redirect(url_for("login", error="Faltan datos en el registro."))
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO usuarios (username, password, fecha_creacion, rol)
            VALUES (%s, %s, %s, %s)
        """, (username, password, datetime.today().date(), "ALUMNO"))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return redirect(url_for("login", error=f"Error: {str(e)}"))
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/deuda_alumno")
def ver_deuda_alumno():
    if 'user_id' not in session or session.get('rol') != "ALUMNO":
        return redirect(url_for("login"))

    matricula = session.get("username")

    conn = get_connection()
    cur = conn.cursor()

    # Traemos TODA la información
    cur.execute("""
        SELECT nombre, carrera, semestre, deuda
        FROM alumnos 
        WHERE matricula=%s
    """, (matricula,))

    deuda_registro = cur.fetchone()

    cur.close()
    conn.close()

    if deuda_registro:
        nombre_alumno, carrera, semestre, deuda_monto = deuda_registro
        return render_template("tablero_alumno.html",
                               nombre=nombre_alumno,
                               carrera=carrera,
                               semestre=semestre,
                               deuda=deuda_monto,
                               matricula=matricula,
                               now=datetime.now)
    else:
        return render_template("tablero_alumno.html",
                               nombre=matricula,
                               carrera="N/A",
                               semestre="N/A",
                               deuda=0.00,
                               matricula=matricula,
                               msg="Ficha de deuda pendiente.",
                               now=datetime.now)

@app.route("/admin_dashboard", methods=["GET", "POST"])
def admin_dashboard():
    if session.get('rol') != "ADMIN":
        return redirect(url_for("login", error="Acceso denegado."))
    msg_success = request.args.get("msg_success")
    error_msg = request.args.get("error")
    conn = get_connection()
    cur = conn.cursor()
    if request.method == "POST":
        accion = request.form.get("accion")
        matricula = request.form.get("matricula")
        try:
            if accion == "eliminar":
                cur.execute("DELETE FROM alumnos WHERE matricula=%s", (matricula,))
                msg_success = f"Ficha de deuda para {matricula} eliminada."
            elif accion == "editar":
                nombre = request.form.get("nombre")
                carrera = request.form.get("carrera")
                semestre = int(request.form.get("semestre"))
                deuda = float(request.form.get("deuda"))
                cur.execute("""
                    UPDATE alumnos SET nombre=%s, carrera=%s, semestre=%s, deuda=%s
                    WHERE matricula=%s
                """, (nombre, carrera, semestre, deuda, matricula))
                msg_success = f"Ficha de deuda para {nombre} actualizada."
            conn.commit()
        except Exception as e:
            conn.rollback()
            error_msg = f"Error: {str(e)}"
    # GET: cargar registros y usuarios
    cur.execute("SELECT matricula, nombre, carrera, semestre, deuda FROM alumnos")
    registros = cur.fetchall()
    cur.execute("SELECT username FROM usuarios WHERE rol='ALUMNO' ORDER BY username")
    usuarios = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return render_template("admin_registros.html", registros=registros, usuarios=usuarios, msg_success=msg_success, error=error_msg)

@app.route("/admin/crear_ficha", methods=["POST"])
def admin_crear_ficha():
    if session.get('rol') != "ADMIN":
        return redirect(url_for("login", error="Acceso denegado."))
    matricula = request.form.get("matricula")
    nombre = request.form.get("nombre")
    carrera = request.form.get("carrera")
    semestre = request.form.get("semestre")
    deuda = request.form.get("deuda")
    if not all([matricula, nombre, carrera, semestre, deuda]):
        return redirect(url_for("admin_dashboard", error="Todos los campos son obligatorios."))
    try:
        semestre = int(semestre)
        deuda = float(deuda)
    except ValueError:
        return redirect(url_for("admin_dashboard", error="Semestre o deuda inválidos."))
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM usuarios WHERE username=%s", (matricula,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        return redirect(url_for("admin_dashboard", error=f"No existe usuario '{matricula}'"))
    try:
        cur.execute("""
            INSERT INTO alumnos (matricula, nombre, carrera, semestre, deuda)
            VALUES (%s, %s, %s, %s, %s)
        """, (matricula, nombre, carrera, semestre, deuda))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return redirect(url_for("admin_dashboard", error=f"Error: {str(e)}"))
    cur.close()
    conn.close()
    return redirect(url_for("admin_dashboard", msg_success=f"Ficha de deuda para {nombre} ({matricula}) registrada."))

# -------------------- STATIC --------------------

# -------------------- MAIN --------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
