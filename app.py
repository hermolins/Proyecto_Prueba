from flask import Flask, render_template, request, redirect, url_for, session # <- Importar 'session'
import json
import os

app = Flask(__name__)
# Agrega una clave secreta para la seguridad de las sesiones
app.secret_key = 'una_clave_secreta_muy_fuerte_y_unica' # CAMBIA ESTO EN PRODUCCIÓN

# =========================
# LISTA ENLAZADA DE USUARIOS
# =========================

class NodoUsuario:
    def __init__(self, nombre, email, contraseña):
        self.nombre = nombre
        self.email = email
        self.contraseña = contraseña
        self.siguiente = None

class ListaUsuarios:
    def __init__(self):
        self.cabeza = None
        self.cargar_desde_json()

    def registrar_usuario(self, nombre, email, contraseña):
        if self.buscar_por_email(email):
            return False  # Ya existe

        nuevo = NodoUsuario(nombre, email, contraseña)
        if not self.cabeza:
            self.cabeza = nuevo
        else:
            actual = self.cabeza
            while actual.siguiente:
                actual = actual.siguiente
            actual.siguiente = nuevo

        self.guardar_en_json()
        return True

    def buscar_por_email(self, email):
        actual = self.cabeza
        while actual:
            if actual.email == email:
                return actual
            actual = actual.siguiente
        return None

    def obtener_todos(self):
        usuarios = []
        actual = self.cabeza
        while actual:
            usuarios.append({
                "nombre": actual.nombre,
                "email": actual.email,
                "contraseña": actual.contraseña
            })
            actual = actual.siguiente
        return usuarios

    def guardar_en_json(self):
        with open("usuarios.json", "w") as archivo:
            json.dump(self.obtener_todos(), archivo, indent=4)

    def cargar_desde_json(self):
        # Asegurarse de que la lista esté vacía antes de cargar
        self.cabeza = None 
        
        if os.path.exists("usuarios.json"):
            with open("usuarios.json", "r") as archivo:
                datos = json.load(archivo)
                actual = None
                
                for usuario in datos:
                    # Construcción directa de la lista enlazada
                    nuevo = NodoUsuario(usuario["nombre"], usuario["email"], usuario["contraseña"])
                    
                    if not self.cabeza:
                        self.cabeza = nuevo
                        actual = self.cabeza
                    else:
                        actual.siguiente = nuevo
                        actual = nuevo


usuarios = ListaUsuarios()

# =========================
# ÁRBOL BINARIO DE MENSAJES
# =========================

class NodoMensaje:
    def __init__(self, remitente, destinatario, asunto, cuerpo):
        self.id = id(self) # Usamos el id en memoria como un ID simple
        self.remitente = remitente
        self.destinatario = destinatario
        self.asunto = asunto
        self.cuerpo = cuerpo
        self.izquierda = None
        self.derecha = None

class ArbolMensajes:
    def __init__(self):
        self.raiz = None

    def _insertar_recursivo(self, nodo, nuevo_mensaje):
        # Usamos el 'id' del mensaje como clave de comparación
        if nuevo_mensaje.id < nodo.id:
            if nodo.izquierda is None:
                nodo.izquierda = nuevo_mensaje
            else:
                self._insertar_recursivo(nodo.izquierda, nuevo_mensaje)
        else:
            if nodo.derecha is None:
                nodo.derecha = nuevo_mensaje
            else:
                self._insertar_recursivo(nodo.derecha, nuevo_mensaje)

    def insertar(self, remitente, destinatario, asunto, cuerpo):
        nuevo_mensaje = NodoMensaje(remitente, destinatario, asunto, cuerpo)
        if self.raiz is None:
            self.raiz = nuevo_mensaje
        else:
            self._insertar_recursivo(self.raiz, nuevo_mensaje)
        return True

    def _obtener_inorden(self, nodo, mensajes):
        if nodo is not None:
            self._obtener_inorden(nodo.izquierda, mensajes)
            mensajes.append({
                "id": nodo.id,
                "remitente": nodo.remitente,
                "destinatario": nodo.destinatario,
                "asunto": nodo.asunto,
                "cuerpo": nodo.cuerpo
            })
            self._obtener_inorden(nodo.derecha, mensajes)

    def obtener_todos(self):
        mensajes = []
        self._obtener_inorden(self.raiz, mensajes)
        return mensajes

# Inicializamos el árbol
mensajes = ArbolMensajes()


# =========================
# RUTAS FLASK (TODAS DEBEN IR ANTES DE app.run())
# =========================

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    mensaje = ""
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        contraseña = request.form['contraseña']

        if usuarios.registrar_usuario(nombre, email, contraseña):
            mensaje = "✅ Usuario registrado con éxito!"
        else:
            mensaje = "❌ El email ya está registrado."

    return render_template('registro.html', mensaje=mensaje)

@app.route('/login', methods=['GET', 'POST'])
def login():
    mensaje = ""
    if request.method == 'POST':
        email = request.form['email']
        contraseña = request.form['contraseña']
        usuario = usuarios.buscar_por_email(email)

        if usuario and usuario.contraseña == contraseña:
            # ✅ Almacenar el email en la sesión
            session['usuario_email'] = usuario.email 
            # Redirigir a 'componer_correo' sin parámetros en la URL
            return redirect(url_for('componer_correo')) 
        else:
            mensaje = "❌ Email o contraseña incorrectos."

    return render_template('login.html', mensaje=mensaje)

@app.route('/usuarios')
def ver_usuarios():
    lista = usuarios.obtener_todos()
    return render_template('usuarios.html', usuarios=lista)

@app.route('/correo', methods=['GET', 'POST'])
def componer_correo():
    # 🛑 Verificar si el usuario está logueado
    if 'usuario_email' not in session:
        # Si no hay sesión, redirigir al login
        return redirect(url_for('login')) 
    
    # 🚀 Obtener el email del remitente de la sesión
    remitente = session['usuario_email']
    
    mensaje = ""
    # El request.args.get('remitente_email', 'Desconocido') ya no es necesario
    # porque lo obtienes de la sesión

    if request.method == 'POST':
        destinatario = request.form['destinatario']
        asunto = request.form['asunto']
        cuerpo = request.form['cuerpo']

        # Insertar el mensaje en el Árbol
        mensajes.insert(remitente, destinatario, asunto, cuerpo)
        mensaje = "✅ Mensaje enviado y guardado con éxito!"

    # Pasamos el email del remitente (de la sesión) a la plantilla
    return render_template('correo.html', mensaje=mensaje, remitente_email=remitente)

@app.route('/logout')
def logout():
    session.pop('usuario_email', None) # Elimina el email de la sesión
    return redirect(url_for('login')) # Redirige al login

@app.route('/mensajes')
def ver_mensajes():
    lista_mensajes = mensajes.obtener_todos()
    return render_template('mensajes.html', mensajes=lista_mensajes)


@app.route('/')
def home():
    return redirect(url_for('registro'))

if __name__ == '__main__':
    app.run(debug=True)