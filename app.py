from flask import Flask, render_template, request, session, redirect
import pandas as pd
import joblib
from datetime import datetime, timezone
from collections import Counter
import json
import os

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'
modelo = joblib.load('modelo.pkl')
scaler = joblib.load('escalador.pkl')



# Cargar usuarios si existe el archivo
# Cargar usuarios si existe el archivo
usuarios = []

if os.path.exists('usuarios.json'):
    with open('usuarios.json', 'r', encoding='utf-8') as f:
        contenido = f.read().strip()
        if contenido:
            usuarios = json.loads(contenido)

# Preguntas de trivia sobre astronautas
trivia_preguntas = [
    {
        'id': 1,
        'pregunta': '¿Quién fue el primer humano en caminar en la Luna?',
        'opciones': ['Yuri Gagarin', 'Neil Armstrong', 'Buzz Aldrin', 'Alan Shepard'],
        'respuesta': 'Neil Armstrong'
    },
    {
        'id': 2,
        'pregunta': '¿Cuál es el nombre del primer satélite artificial lanzado al espacio?',
        'opciones': ['Voyager 1', 'Sputnik 1', 'Apollo 11', 'Hubble'],
        'respuesta': 'Sputnik 1'
    },
    {
        'id': 3,
        'pregunta': '¿Qué planeta es conocido como el planeta rojo?',
        'opciones': ['Venus', 'Júpiter', 'Marte', 'Saturno'],
        'respuesta': 'Marte'
    },
    {
        'id': 4,
        'pregunta': '¿Cuál es el nombre de la agencia espacial estadounidense?',
        'opciones': ['ESA', 'Roscosmos', 'NASA', 'CNSA'],
        'respuesta': 'NASA'
    },
    {
        'id': 5,
        'pregunta': '¿Qué nave llevó a los primeros humanos a la Luna?',
        'opciones': ['Apollo 11', 'Challenger', 'Soyuz', 'Discovery'],
        'respuesta': 'Apollo 11'
    },
    {
        'id': 6,
        'pregunta': '¿Cuál fue la misión espacial que llevó el primer rover a Marte?',
        'opciones': ['Viking 1', 'Curiosity', 'Spirit', 'Opportunity'],
        'respuesta': 'Viking 1'
    },
    {
        'id': 7,
        'pregunta': '¿En qué año se fundó la Agencia Espacial Europea (ESA)?',
        'opciones': ['1964', '1975', '1982', '1990'],
        'respuesta': '1975'
    },
    {
        'id': 8,
        'pregunta': '¿Cuál es el satélite natural más grande del planeta Júpiter?',
        'opciones': ['Europa', 'Ganímedes', 'Ío', 'Calisto'],
        'respuesta': 'Ganímedes'
    },
    {
        'id': 9,
        'pregunta': '¿Qué astronauta pasó más tiempo acumulado en el espacio hasta 2020?',
        'opciones': ['Peggy Whitson', 'Sergei Krikalev', 'Scott Kelly', 'Gennady Padalka'],
        'respuesta': 'Gennady Padalka'
    },
    {
        'id': 10,
        'pregunta': '¿Cuál fue el nombre del telescopio espacial lanzado en 1990 que revolucionó la astronomía?',
        'opciones': ['Kepler', 'Hubble', 'Spitzer', 'Chandra'],
        'respuesta': 'Hubble'
    }
]

@app.route('/')
def index():
    session.clear()
    return render_template('index.html')

@app.route('/trivia', methods=['GET', 'POST'])
def trivia():
    if request.method == 'POST':
        respuestas_usuario = {str(p['id']): request.form.get(str(p['id'])) for p in trivia_preguntas}
        puntaje = sum(1 for p in trivia_preguntas if respuestas_usuario.get(str(p['id'])) == p['respuesta'])
        session['trivia_puntaje'] = puntaje
        session['trivia_total'] = len(trivia_preguntas)
        session['trivia_inicio'] = datetime.now(timezone.utc)
        return redirect('/juego')
    return render_template('trivia.html', preguntas=trivia_preguntas)

@app.route('/juego', methods=['GET', 'POST'])
def juego():
    if request.method == 'POST':
        session['laberinto_tiempo'] = float(request.form['tiempo'])
        return redirect('/formulario')
    return render_template('juego.html')

@app.route('/formulario')
def formulario():
    if 'laberinto_tiempo' not in session:
        return redirect('/trivia')
    return render_template('form.html')

@app.route('/procesar', methods=['POST'])
def procesar():
    nombre = request.form['nombre']
    entrada = {
        'edad': int(request.form['edad']),
        'promedio': float(request.form['promedio']),
        'deportes': int(request.form['deportes']),
        'liderazgo': int(request.form['liderazgo']),
        'club_ciencia': int(request.form['club_ciencia']),
        'ingles': int(request.form['ingles']),
        'condicion_fisica': int(request.form['condicion_fisica']),
        'trabajo_equipo': int(request.form['trabajo_equipo']),
        'idiomas': int(request.form['idiomas']),
        'creatividad': int(request.form['creatividad'])
    }

    entrada_df = pd.DataFrame([entrada])
    entrada_esc = scaler.transform(entrada_df)
    probabilidad = modelo.predict_proba(entrada_esc)[0][1]

    # Calcular puntajes combinados
    trivia_score = session.get('trivia_puntaje', 0) / session.get('trivia_total', 5)
    laberinto_score = max(0, 1 - (session.get('laberinto_tiempo', 0) / 120))  # Máximo 2 minutos
    
    entrada['puntaje_final'] = 0.5 * probabilidad + 0.3 * trivia_score + 0.2 * laberinto_score
    entrada['nombre'] = nombre
    entrada['probabilidad'] = probabilidad
    entrada.update({
        'trivia_puntaje': session.get('trivia_puntaje', 0),
        'trivia_total': session.get('trivia_total', 5),
        'laberinto_tiempo': session.get('laberinto_tiempo', 0)
    })

    habilidades = {
        'liderazgo': entrada['liderazgo'],
        'club_ciencia': entrada['club_ciencia'],
        'ingles': entrada['ingles'],
        'condicion_fisica': entrada['condicion_fisica'],
        'trabajo_equipo': entrada['trabajo_equipo'],
        'idiomas': entrada['idiomas'],
        'creatividad': entrada['creatividad']
    }

    def evaluar(valor, clave=None):
        if clave == 'idiomas':
            if valor >= 2:
                return "🟢 Alto - excelente"
            elif valor == 1:
                return "🟡 Medio - aceptable, pero mejorable"
            else:
                return "🔴 Bajo - necesita mejorar"
        if valor in (0, 1):
            return "🟢 Sí" if valor == 1 else "🔴 No"
        elif valor >= 8:
            return "🟢 Alto - excelente"
        elif valor >= 5:
            return "🟡 Medio - aceptable, pero mejorable"
        else:
            return "🔴 Bajo - necesita mejorar"

    evaluaciones = {k: (v, evaluar(v, k)) for k, v in habilidades.items()}

    def valor_para_comparar(x):
        return x[1] if x[1] > 1 else (10 if x[1] == 1 else 0)

    mejor_habilidad = max(habilidades.items(), key=valor_para_comparar)[0].replace('_', ' ').capitalize()

    entrada['evaluaciones'] = evaluaciones
    entrada['mejor_habilidad'] = mejor_habilidad

    usuarios.append(entrada)

    # Guardar usuarios en archivo JSON
    with open('usuarios.json', 'w', encoding='utf-8') as f:
        json.dump(usuarios, f, ensure_ascii=False, indent=4)

    return render_template('resultados.html', 
                         datos=entrada,
                         probabilidad=probabilidad,
                         evaluaciones=evaluaciones,
                         mejor_habilidad=mejor_habilidad)

@app.route('/ranking')
def ranking():
    top_usuarios = sorted(
        usuarios,
        key=lambda x: x.get('puntaje_final', 0),
        reverse=True
    )

    # Asegurar campos para compatibilidad
    for u in top_usuarios:
        u.setdefault('puntaje_final', 0)
        u.setdefault('trivia_puntaje', 0)
        u.setdefault('trivia_total', 5)
        u.setdefault('laberinto_tiempo', 0)
        u.setdefault('mejor_habilidad', 'No disponible')
        u.setdefault('evaluaciones', {})

    promedio = sum(u.get('puntaje_final', 0) for u in usuarios) / len(usuarios) if usuarios else 0
    mejor = max(u.get('puntaje_final', 0) for u in usuarios) if usuarios else 0
    peor = min(u.get('puntaje_final', 0) for u in usuarios) if usuarios else 0

    mejores_habilidades = [u.get('mejor_habilidad', 'No disponible') for u in usuarios]
    conteo_habilidades = Counter(mejores_habilidades)
    labels_habilidades = list(conteo_habilidades.keys())
    valores_habilidades = list(conteo_habilidades.values())

    return render_template(
        'ranking.html',
        usuarios=top_usuarios[:15],
        promedio=promedio,
        mejor=mejor,
        peor=peor,
        labels_habilidades=labels_habilidades,
        valores_habilidades=valores_habilidades
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5004)
