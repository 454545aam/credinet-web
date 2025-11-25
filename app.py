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

@app.route('/tablero_alumno')
def tablero_alumno():
    return render_template('tablero_alumno.html')

@app.route('/juego')
def juego():
    return render_template('juego.html')


@app.route('/admin_registros')
def admin_registros():
    return render_template('admin_registros.html')

@app.route("/home")
def home():
   
    return render_template("homeshell.html")
 
@app.route("/login", methods=["GET", "POST"])
def login():
    """
    MANEJA EL ENDPOINT 'login' (GET y POST).
    POST: Valida credenciales y redirige al dashboard correcto.
    """
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if not username or not password:
            return render_template("login.html", error="Faltan datos", historial=historial_login.obtener()) 

        with get_db() as db:
            cur = db.cursor()
            cur.execute("SELECT id, rol FROM usuarios WHERE username=? AND password=?", (username, password))
            row = cur.fetchone()
            
            if row:
                id_usuario, rol = row[0], row[1]
                
                rol_str = 'ALUMNO' 
                if rol is not None:
                    rol_str = str(rol).strip().upper() 

                session['user_id'] = id_usuario
                session['rol'] = rol_str 
                session['username'] = username 

                # ✅ Agregar usuario al historial de logins
                historial_login.push(username)
                
                if rol_str == "ADMIN" or username.lower() == "admin": 
                    if username.lower() == "admin":
                        session['rol'] = 'ADMIN' 
                    return redirect(url_for("admin_dashboard")) 
                else:
                    return redirect(url_for("ver_deuda_alumno")) 
            else:
                return render_template("login.html", error="Usuario o contraseña incorrectos", historial=historial_login.obtener())

    msg = request.args.get('msg')
    error = request.args.get('error')
    
    # ✅ Pasamos el historial al render para el modo GET
    return render_template("login.html", msg=msg, error=error, historial=historial_login.obtener())

if __name__ == "__main__":
    app.run(debug=True)
