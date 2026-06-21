# ==========================================
# 1. IMPORTACIÓN DE LIBRERÍAS
# ==========================================
import streamlit as st
import pandas as pd
import plotly.express as px
import math
import requests
import numpy as np
from datetime import datetime

# ==========================================
# 2. CONFIGURACIÓN Y ESTÉTICA DARK
# ==========================================
st.set_page_config(
    page_title="🏆 Consola WC 2026 - Dark Edition",
    page_icon="⚽",
    layout="wide"
)

# Inyección de CSS para Tema Oscuro Profesional
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #deff9a; }
    div[data-testid="stExpander"] { border: 1px solid #333; border-radius: 10px; }
    .stButton>button { background-color: #deff9a; color: #000; font-weight: bold; width: 100%; border-radius: 20px; }
    h1, h2, h3 { color: #deff9a !important; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. CONEXIÓN DIRECTA AL SERVIDOR (A PRUEBA DE FALLOS)
# ==========================================
st.sidebar.header("⚙️ Configuración")
url_api = st.sidebar.text_input("URL del Servidor Original", "https://worldcup26.ir/get/games")

# Sin caché de Streamlit para forzar siempre la lectura de datos en tiempo real
def obtener_datos_directos(url):
    """Se conecta y extrae datos detectando inteligentemente la estructura del JSON"""
    try:
        respuesta = requests.get(url, timeout=60)
        if respuesta.status_code == 200:
            datos_json = respuesta.json()
            
            # Sistema de extracción blindado (cubre listas puras o diccionarios)
            if isinstance(datos_json, list):
                matches = datos_json
            elif isinstance(datos_json, dict):
                matches = datos_json.get('data', datos_json.get('matches', datos_json.get('games', [])))
            else:
                matches = []
                
            if isinstance(matches, list) and len(matches) > 0:
                return matches, "🟢 Conectado al Servidor Oficial"
                
            return [], "🔴 El servidor respondió bien (200), pero la tabla de partidos llegó vacía."
            
        return [], f"🔴 Error del Servidor: Código {respuesta.status_code}"
    except Exception as e:
        return [], f"🔴 Error interno de lectura: {str(e)}"

datos_raw, status = obtener_datos_directos(url_api)

if "🟢" in status:
    st.sidebar.success(status)
else:
    st.sidebar.error(status)
    st.error("La conexión con el servidor ha fallado. La consola se pausará hasta recuperar la conexión.")
    st.stop() # Detiene la ejecución del resto de la página si no hay datos reales

# ==========================================
# 4. LÓGICA DE HISTORIAL Y ACIERTOS
# ==========================================
if 'historial' not in st.session_state:
    st.session_state.historial = []

def registrar_prediccion(partido, local, visita, p_local, p_visita):
    nueva = {
        "id": f"{partido}_{datetime.now().strftime('%H%M%S')}",
        "partido": partido,
        "pred": f"{p_local} - {p_visita}",
        "fecha": datetime.now().strftime("%d/%m %H:%M"),
        "acierto": "Pendiente"
    }
    st.session_state.historial.insert(0, nueva)

def calcular_estadisticas_equipo(equipo, df):
    """Calcula el rendimiento real basándose estrictamente en los datos del servidor"""
    jugados_local = df[df['Local'] == equipo]
    jugados_visita = df[df['Visita'] == equipo]
    
    goles_anotados = pd.to_numeric(jugados_local['G_L'], errors='coerce').sum() + pd.to_numeric(jugados_visita['G_V'], errors='coerce').sum()
    goles_recibidos = pd.to_numeric(jugados_local['G_V'], errors='coerce').sum() + pd.to_numeric(jugados_visita['G_L'], errors='coerce').sum()
    total_partidos = len(jugados_local.dropna(subset=['G_L'])) + len(jugados_visita.dropna(subset=['G_V']))
    
    if total_partidos == 0:
        return 1.2, 1.2 # Base neutral si el torneo aún no empieza o no hay datos
        
    return max(goles_anotados / total_partidos, 0.5), max(goles_recibidos / total_partidos, 0.5)

# ==========================================
# 5. PROCESAMIENTO Y LIMPIEZA DE DATOS
# ==========================================
lista_limpia = []
for m in datos_raw:
    h_name = m.get('home_team', {}).get('nameEn', m.get('home_team', {}).get('name', 'TBD'))
    a_name = m.get('away_team', {}).get('nameEn', m.get('away_team', {}).get('name', 'TBD'))
    
    g_l = m.get('home_score')
    g_v = m.get('away_score')
    
    lista_limpia.append({
        "Fecha": m.get('localDate', m.get('date', 'TBD')),
        "Partido": f"{h_name} vs {a_name}",
        "Grupo": m.get('group', 'N/A'),
        "Estado": m.get('status', m.get('matchStatus', 'N/A')),
        "Local": h_name, 
        "Visita": a_name,
        "G_L": int(g_l) if g_l is not None else None, 
        "G_V": int(g_v) if g_v is not None else None
    })

df = pd.DataFrame(lista_limpia)

# ==========================================
# 6. INTERFAZ PRINCIPAL
# ==========================================
st.title("🌎 WC 2026 Analytics Console")
st.markdown("Plataforma de análisis de datos conectada en tiempo real al servidor oficial.")

# Selector de Partido
st.subheader("📅 Simulador de Enfrentamientos")

# Evitar error si la tabla está vacía
if df.empty:
    st.warning("El servidor se conectó, pero no envió partidos. Intenta más tarde.")
    st.stop()

sel_partido = st.selectbox("Selecciona un partido del servidor para procesar su predicción:", df['Partido'].tolist())
info = df[df['Partido'] == sel_partido].iloc[0]

col1, col2 = st.columns([1, 1])

with col1:
    if st.button("🏆 Ejecutar Modelo Predictivo"):
        # Extracción de métricas
        gf_local, gc_local = calcular_estadisticas_equipo(info['Local'], df)
        gf_visitante, gc_visitante = calcular_estadisticas_equipo(info['Visita'], df)
        
        # Cruce de variables (Ataque vs Defensa)
        xg_local = (gf_local + gc_visitante) / 2
        xg_visitante = (gf_visitante + gc_local) / 2
        
        # Simulación
        res_l = np.random.poisson(xg_local)
        res_v = np.random.poisson(xg_visitante)
        
        st.markdown(f"<h2 style='text-align: center; background-color: #1e2130; padding: 20px; border-radius: 10px; border: 1px solid #deff9a;'>⚽ Marcador Proyectado:<br>{info['Local']} {res_l} - {res_v} {info['Visita']}</h2>", unsafe_allow_html=True)
        
        registrar_prediccion(sel_partido, info['Local'], info['Visita'], res_l, res_v)
        st.success("✅ Predicción registrada en la base de datos histórica.")

# ==========================================
# 7. PANEL DE HISTÓRICO Y ACIERTOS
# ==========================================
st.markdown("---")
tab1, tab2, tab3 = st.tabs(["📊 Base de Datos del Servidor", "📈 Historial de Predicciones", "🎯 Tracking de Efectividad"])

with tab1:
    st.dataframe(df, use_container_width=True, hide_index=True)

with tab2:
    if st.session_state.historial:
        df_hist = pd.DataFrame(st.session_state.historial)
        st.table(df_hist[["fecha", "partido", "pred", "acierto"]])
    else:
        st.info("Aún no has ejecutado el modelo predictivo. Las predicciones aparecerán aquí.")

with tab3:
    st.subheader("Rendimiento del Algoritmo")
    aciertos = [h for h in st.session_state.historial if h['acierto'] != "Pendiente"]
    total = len(st.session_state.historial)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Volumen de Predicciones", total)
    c2.metric("Aciertos Exactos", len([a for a in aciertos if a['acierto'] == "Exacto"]))
    efectividad = int((len(aciertos)/total)*100) if total > 0 else 0
    c3.metric("Efectividad Global", f"{efectividad}%")
