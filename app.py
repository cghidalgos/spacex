from flask import Flask, render_template, request, session, redirect
import pandas as pd
import joblib
from datetime import datetime, timezone
from collections import Counter
import json
import os

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'

# Carga del modelo (opcional). Si no existe, se calcula puntaje de habilidades con normalización simple
try:
    modelo = joblib.load('modelo.pkl')
    scaler = joblib.load('escalador.pkl')
except Exception:
    modelo = None
    scaler = None



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
        # Ir al juego de gravedad cero antes del formulario
        return redirect('/gravedad-cero')
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

    # Probabilidad por ML (si hay modelo). No afecta el 33/33/33, se mantiene como dato informativo opcional
    probabilidad = None
    if scaler is not None and modelo is not None:
        try:
            entrada_df = pd.DataFrame([entrada])
            entrada_esc = scaler.transform(entrada_df)
            probabilidad = float(modelo.predict_proba(entrada_esc)[0][1])
        except Exception:
            probabilidad = None

    # Calcular puntajes combinados (33.3% cada componente)
    # 1) Trivia: correctas / total
    trivia_correctas = session.get('trivia_puntaje', 0)
    trivia_total = session.get('trivia_total', 5)
    trivia_total = trivia_total if trivia_total else 5
    trivia_score = (trivia_correctas / trivia_total) if trivia_total > 0 else 0.0

    # 2) Laberinto: eficiencia = 1 - tiempo/120 (cap entre 0 y 1)
    tiempo_laberinto = float(session.get('laberinto_tiempo', 0))
    laberinto_score = max(0.0, min(1.0, 1.0 - (tiempo_laberinto / 120.0)))

    # 2.5) Gravedad cero: normalización según dificultad
    gravedad_score_raw = int(session.get('gravedad_score', 0))
    gravedad_combo = int(session.get('gravedad_combo', 0))
    gravedad_dificultad = session.get('gravedad_dificultad', 'medium')
    caps = {'easy': 200.0, 'medium': 300.0, 'hard': 400.0}
    cap = caps.get(gravedad_dificultad, 300.0)
    gravedad_score = max(0.0, min(1.0, gravedad_score_raw / cap))

    # 3) Habilidades del formulario: normalización simple de campos clave
    def clamp01(x: float) -> float:
        return max(0.0, min(1.0, x))

    norm_promedio = clamp01(entrada['promedio'] / 5.0)
    norm_deportes = clamp01(entrada['deportes'] / 10.0)
    norm_liderazgo = clamp01(entrada['liderazgo'] / 10.0)
    norm_club = clamp01(entrada['club_ciencia'] / 10.0)
    norm_ingles = clamp01(entrada['ingles'] / 10.0)
    norm_condicion = clamp01(entrada['condicion_fisica'] / 10.0)
    norm_equipo = clamp01(entrada['trabajo_equipo'] / 10.0)
    norm_idiomas = clamp01(min(entrada['idiomas'], 3) / 3.0)  # 3+ idiomas se considera 1.0
    norm_creatividad = clamp01(entrada['creatividad'] / 10.0)

    skills_norm_list = [
        norm_promedio, norm_deportes, norm_liderazgo, norm_club,
        norm_ingles, norm_condicion, norm_equipo, norm_idiomas, norm_creatividad
    ]
    habilidades_score = sum(skills_norm_list) / len(skills_norm_list)

    # Puntaje final (0..1) con 4 componentes (25% cada uno)
    entrada['puntaje_final'] = (trivia_score + laberinto_score + habilidades_score + gravedad_score) / 4.0
    entrada['nombre'] = nombre
    if probabilidad is not None:
        entrada['probabilidad'] = probabilidad
    entrada.update({
        'trivia_puntaje': trivia_correctas,
        'trivia_total': trivia_total,
        'laberinto_tiempo': tiempo_laberinto,
        'habilidades_score': habilidades_score,
        'gravedad_puntos': gravedad_score_raw,
        'gravedad_combo': gravedad_combo,
        'gravedad_dificultad': gravedad_dificultad,
        'gravedad_score': gravedad_score
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

    # Clasificación de tipo de ingeniero/perfil
    # Calculamos scores ponderados para cada perfil
    score_lider = (
        norm_liderazgo * 0.3 +
        norm_equipo * 0.25 +
        norm_creatividad * 0.2 +
        norm_promedio * 0.15 +
        norm_club * 0.1
    )
    
    score_comunicaciones = (
        norm_ingles * 0.35 +
        norm_idiomas * 0.35 +
        norm_equipo * 0.2 +
        norm_promedio * 0.1
    )
    
    score_sistemas = (
        norm_club * 0.35 +
        norm_promedio * 0.25 +
        norm_creatividad * 0.25 +
        norm_liderazgo * 0.15
    )
    
    score_explorador = (
        norm_condicion * 0.35 +
        norm_deportes * 0.35 +
        norm_equipo * 0.2 +
        norm_liderazgo * 0.1
    )

    # Encontrar el perfil con mayor score
    perfiles_scores = {
        'Líder de misión': score_lider,
        'Oficial de comunicaciones': score_comunicaciones,
        'Ingeniería de sistemas y nave': score_sistemas,
        'Especialista EVA y exploración': score_explorador
    }

    # Asignar el perfil con mayor score (siempre habrá uno)
    tipo_ingeniero = max(perfiles_scores.items(), key=lambda x: x[1])[0]

    entrada['tipo_ingeniero'] = tipo_ingeniero

    # Áreas de mejora sugeridas
    mejoras = []
    if norm_ingles < 0.7 or norm_idiomas < 0.7:
        mejoras.append({'area': 'Inglés e idiomas', 'detalle': 'Refuerza tu inglés y suma idiomas adicionales para mejorar comunicaciones.'})
    if norm_promedio < 0.7:
        mejoras.append({'area': 'Matemáticas y ciencias', 'detalle': 'Mejora tu base académica (promedio) con foco en STEM.'})
    if max(norm_deportes, norm_condicion) < 0.7:
        mejoras.append({'area': 'Deportes y condición física', 'detalle': 'Incrementa la actividad física y resistencia.'})
    if norm_equipo < 0.7:
        mejoras.append({'area': 'Trabajo en equipo', 'detalle': 'Participa en proyectos colaborativos y roles de equipo.'})
    entrada['mejoras'] = mejoras

    # Porcentajes para UI
    porcentajes = {
        'trivia': trivia_score * 100.0,
        'laberinto': laberinto_score * 100.0,
        'habilidades': habilidades_score * 100.0,
        'gravedad': gravedad_score * 100.0
    }
    entrada['porcentajes'] = porcentajes

    entrada['evaluaciones'] = evaluaciones
    entrada['mejor_habilidad'] = mejor_habilidad

    usuarios.append(entrada)

    # Guardar usuarios en archivo JSON
    with open('usuarios.json', 'w', encoding='utf-8') as f:
        json.dump(usuarios, f, ensure_ascii=False, indent=4)

    return render_template(
        'resultados.html',
        datos=entrada,
        probabilidad=probabilidad,
        evaluaciones=evaluaciones,
        mejor_habilidad=mejor_habilidad,
        porcentajes=porcentajes
    )

@app.route('/gravedad-cero')
def gravedad_cero():
    return render_template('gravedad_cero.html')

@app.route('/gravedad-cero/fin', methods=['POST'])
def gravedad_cero_fin():
    # Guardar resultados del mini-juego en sesión y continuar al formulario
    try:
        session['gravedad_score'] = int(request.form.get('score', 0))
        session['gravedad_combo'] = int(request.form.get('combo', 0))
        session['gravedad_dificultad'] = request.form.get('dificultad', 'medium')
    except Exception:
        session['gravedad_score'] = 0
        session['gravedad_combo'] = 0
        session['gravedad_dificultad'] = 'medium'
    return redirect('/formulario')

@app.route('/ranking')
def ranking():
    # Leer usuarios.json cada vez
    usuarios_actual = []
    if os.path.exists('usuarios.json'):
        with open('usuarios.json', 'r', encoding='utf-8') as f:
            contenido = f.read().strip()
            if contenido:
                usuarios_actual = json.loads(contenido)

    top_usuarios = sorted(
        usuarios_actual,
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

    promedio = sum(u.get('puntaje_final', 0) for u in top_usuarios) / len(top_usuarios) if top_usuarios else 0
    mejor = max(u.get('puntaje_final', 0) for u in top_usuarios) if top_usuarios else 0
    peor = min(u.get('puntaje_final', 0) for u in top_usuarios) if top_usuarios else 0

    mejores_habilidades = [u.get('mejor_habilidad', 'No disponible') for u in top_usuarios]
    conteo_habilidades = Counter(mejores_habilidades)
    labels_habilidades = list(conteo_habilidades.keys())
    valores_habilidades = list(conteo_habilidades.values())

    return render_template(
        'ranking.html',
        usuarios=top_usuarios,
        promedio=promedio,
        mejor=mejor,
        peor=peor,
        labels_habilidades=labels_habilidades,
        valores_habilidades=valores_habilidades
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5004)
