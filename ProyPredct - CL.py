# ==========================================
# 1. IMPORTACIÓN DE LIBRERÍAS
# ==========================================
import streamlit as st
import pandas as pd
import plotly.express as px
import math
import requests
import numpy as np

# ==========================================
# 2. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="🏆 Consola Inteligente Mundial 2026",
    page_icon="🌎",
    layout="wide"
)

# ==========================================
# 3. MOTOR DE EXTRACCIÓN (CON PLAN B AUTOMÁTICO)
# ==========================================
st.sidebar.header("⚙️ Configuración del Servidor")
# Aquí está el enlace público fijado como predeterminado
api_url = st.sidebar.text_input("URL del Repositorio (API)", "https://worldcup26.ir/get/matches")
st.sidebar.markdown("---")

@st.cache_data(ttl=60)
def obtener_datos_repositorio(url):
    """Intenta extraer datos de la API; si falla, activa el respaldo de emergencia"""
    try:
        respuesta = requests.get(url, timeout=5)
        if respuesta.status_code == 200:
            datos_json = respuesta.json()
            matches = datos_json.get('data', datos_json.get('matches', datos_json))
            if isinstance(matches, list) and len(matches) > 0:
                return matches, "🟢 Conectado a la API Oficial"
    except Exception:
        pass

    # PLAN B: Base de datos de contingencia con la estructura exacta de la API
    respaldo = [
        {"date": "2026-06-11", "group": "Grupo A", "home_team": {"name": "México"}, "away_team": {"name": "Curazao"}, "home_score": 0, "away_score": 0, "status": "Programado"},
        {"date": "2026-06-11", "group": "Grupo D", "home_team": {"name": "Argentina"}, "away_team": {"name": "Suecia"}, "home_score": 2, "away_score": 1, "status": "Finalizado"},
        {"date": "2026-06-12", "group": "Grupo B", "home_team": {"name": "Estados Unidos"}, "away_team": {"name": "Haití"}, "home_score": 0, "away_score": 0, "status": "Programado"},
        {"date": "2026-06-12", "group": "Grupo E", "home_team": {"name": "Brasil"}, "away_team": {"name": "Turquía"}, "home_score": 0, "away_score": 0, "status": "Programado"},
        {"date": "2026-06-13", "group": "Grupo F", "home_team": {"name": "Francia"}, "away_team": {"name": "Jordania"}, "home_score": 0, "away_score": 0, "status": "Programado"},
        {"date": "2026-06-13", "group": "Grupo G", "home_team": {"name": "España"}, "away_team": {"name": "Japón"}, "home_score": 0, "away_score": 0, "status": "Programado"}
    ]
    return respaldo, "🟡 Modo Respaldo (API Oficial Fuera de Línea)"

def obtener_nombre(equipo_obj):
    if isinstance(equipo_obj, dict):
        return equipo_obj.get('nameEn', equipo_obj.get('name', 'Desconocido'))
    return str(equipo_obj) if equipo_obj else "Desconocido"

# ==========================================
# 4. PROCESAMIENTO Y LIMPIEZA DE DATOS
# ==========================================
datos_crudos, estado_conexion = obtener_datos_repositorio(api_url)

if "🟢" in estado_conexion:
    st.sidebar.success(estado_conexion)
else:
    st.sidebar.warning(estado_conexion)

lista_limpia = []
for m in datos_crudos:
    local = obtener_nombre(m.get('home_team', m.get('homeTeam')))
    visitante = obtener_nombre(m.get('away_team', m.get('awayTeam')))
    
    if local == "Desconocido" or visitante == "Desconocido":
        continue
        
    goles_l = m.get('home_score', m.get('homeScore', 0))
    goles_v = m.get('away_score', m.get('awayScore', 0))
    
    lista_limpia.append({
        'Fecha': m.get('localDate', m.get('date', 'TBD')),
        'Grupo': m.get('group', 'Fase Final'),
        'Local': local,
        'Visitante': visitante,
        'Goles_Local': int(goles_l) if goles_l is not None else 0,
        'Goles_Visitante': int(goles_v) if goles_v is not None else 0,
        'Estado': m.get('status', m.get('matchStatus', 'Programado'))
    })

df_calendario = pd.DataFrame(lista_limpia)

# ==========================================
# 5. MOTOR MATEMÁTICO DE PREDICCIÓN
# ==========================================
def poisson_prob(esperado, ocurrencia):
    return (math.exp(-esperado) * (esperado**ocurrencia)) / math.factorial(ocurrencia)

def calcular_estadisticas_equipo(equipo, df):
    """Calcula el rendimiento ofensivo/defensivo real promediando los datos de la API"""
    jugados_local = df[df['Local'] == equipo]
    jugados_visita = df[df['Visitante'] == equipo]
    
    goles_anotados = jugados_local['Goles_Local'].sum() + jugados_visita['Goles_Visitante'].sum()
    goles_recibidos = jugados_local['Goles_Visitante'].sum() + jugados_visita['Goles_Local'].sum()
    total_partidos = len(jugados_local) + len(jugados_visita)
    
    if total_partidos == 0:
        return 1.2, 1.2 # Valores base neutrales si no hay historial en el repositorio
        
    promedio_anotados = goles_anotados / total_partidos
    promedio_recibidos = goles_recibidos / total_partidos
    
    return max(promedio_anotados, 0.5), max(promedio_recibidos, 0.5)

# ==========================================
# 6. DISEÑO DE LA INTERFAZ GRÁFICA
# ==========================================
st.title("🌎 Consola Data-Driven Mundial 2026")
st.markdown("Fixture interactivo alimentado por los datos en tiempo real del repositorio oficial.")
st.markdown("---")

# --- PANEL DE CONTROL ---
st.sidebar.header("📅 Seleccionar Partido")

lista_partidos_combo = [
    f"{r['Fecha']} | {r['Local']} vs {r['Visitante']}" 
    for _, r in df_calendario.iterrows()
]
partido_seleccionado_texto = st.sidebar.selectbox("Partidos Disponibles", lista_partidos_combo)

indice_seleccionado = lista_partidos_combo.index(partido_seleccionado_texto)
info_partido = df_calendario.iloc[indice_seleccionado]

equipo_local = info_partido['Local']
equipo_visitante = info_partido['Visitante']

boton_simular = st.sidebar.button("🏆 Simular Predicción")

# --- SECCIÓN 1: FIXTURE OFICIAL ---
st.subheader("📅 Calendario y Resultados Sincronizados")
st.dataframe(df_calendario, use_container_width=True, hide_index=True)
st.markdown("---")

# --- SECCIÓN 2: SIMULACIÓN ACTIVA ---
if boton_simular:
    st.subheader(f"⚔️ Análisis Táctico de Enfrentamiento")
    
    # Extracción de promedios de rendimiento directo desde la tabla
    gf_local, gc_local = calcular_estadisticas_equipo(equipo_local, df_calendario)
    gf_visitante, gc_visitante = calcular_estadisticas_equipo(equipo_visitante, df_calendario)
    
    # Cruce de variables (Ataque de uno contra defensa del otro)
    xg_local = (gf_local + gc_visitante) / 2
    xg_visitante = (gf_visitante + gc_local) / 2
    
    # Ejecución de la simulación del marcador
    goles_sim_local = np.random.poisson(xg_local)
    goles_sim_visitante = np.random.poisson(xg_visitante)
    
    st.markdown(f"<h1 style='text-align: center; background-color: #f0f2f6; padding: 15px; border-radius: 10px; color: #333;'>⚽ Resultado Simulado: {equipo_local} {goles_sim_local} - {goles_sim_visitante} {equipo_visitante}</h1>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Generación de la matriz probabilística (Resultados exactos)
    matriz_resultados = []
    for i in range(6): 
        for j in range(6):
            prob_resultado = poisson_prob(xg_local, i) * poisson_prob(xg_visitante, j)
            matriz_resultados.append({'Marcador': f"{i} - {j}", 'Probabilidad': prob_resultado * 100})
            
    # Simulación de córners basada en volumen ofensivo
    xg_corners = (xg_local + xg_visitante) * 3.5
    matriz_corners = []
    for k in range(5, 16):
        prob_corner = poisson_prob(xg_corners, k)
        matriz_corners.append({'Córners': f"{k} exactos", 'Probabilidad': prob_corner * 100})

    df_resultados = pd.DataFrame(matriz_resultados).sort_values(by='Probabilidad', ascending=False).head(10)
    df_corners = pd.DataFrame(matriz_corners).sort_values(by='Probabilidad', ascending=False).head(10)
    
    colores_barras = ['Top 3 (Muy Probable)'] * 3 + ['Otras Probabilidades'] * 7
    df_resultados['Categoría'] = colores_barras
    df_corners['Categoría'] = colores_barras

    # Despliegue de los Gráficos de barras con Plotly
    st.subheader("🎯 Tendencias Estadísticas (Top 10)")
    col_graf1, col_graf2 = st.columns(2)
    mapa_colores = {'Top 3 (Muy Probable)': '#28a745', 'Otras Probabilidades': '#6c757d'}
    
    with col_graf1:
        st.markdown("**Marcadores más probables**")
        fig_res = px.bar(df_resultados, x='Marcador', y='Probabilidad', color='Categoría', color_discrete_map=mapa_colores, text='Probabilidad')
        fig_res.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_res.update_layout(showlegend=False, yaxis_title="Probabilidad (%)", xaxis_title="Resultado Exacto")
        fig_res.update_yaxes(range=[0, df_resultados['Probabilidad'].max() + 5]) 
        st.plotly_chart(fig_res, use_container_width=True)
        
    with col_graf2:
        st.markdown("**Total de Córners en el partido**")
        fig_cor = px.bar(df_corners, x='Córners', y='Probabilidad', color='Categoría', color_discrete_map=mapa_colores, text='Probabilidad')
        fig_cor.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_cor.update_layout(showlegend=False, yaxis_title="Probabilidad (%)", xaxis_title="Cantidad de Córners")
        fig_cor.update_yaxes(range=[0, df_corners['Probabilidad'].max() + 5])
        st.plotly_chart(fig_cor, use_container_width=True)