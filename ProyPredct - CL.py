# ==========================================
# 1. IMPORTACIÓN DE LIBRERÍAS
# ==========================================
import streamlit as st
import pandas as pd
import math
import requests
import numpy as np
from datetime import datetime

# ==========================================
# 2. CONFIGURACIÓN Y TEMA "GOALSTREAM"
# ==========================================
st.set_page_config(page_title="Tablero en Vivo - WC 2026", page_icon="⚽", layout="wide")

# CSS Avanzado para replicar la interfaz profesional
st.markdown("""
    <style>
    /* Fondos oscuros y tipografía */
    .stApp { background-color: #0b101a; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #1f2937; }
    header { visibility: hidden; } /* Ocultar barra superior nativa */
    .block-container { padding-top: 2rem; max-width: 1200px; }
    
    /* Ocultar elementos nativos molestos */
    footer {visibility: hidden;}
    
    /* Estilos para los selectores */
    div[data-baseweb="select"] > div { background-color: #1f2937; color: white; border: 1px solid #374151; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. MOTOR DE DATOS Y CONEXIÓN AL SERVIDOR
# ==========================================
def obtener_datos_directos(url):
    """Conexión robusta con tiempo de espera extendido a 30s"""
    try:
        respuesta = requests.get(url, timeout=30)
        if respuesta.status_code == 200:
            datos_json = respuesta.json()
            if isinstance(datos_json, list):
                matches = datos_json
            elif isinstance(datos_json, dict):
                matches = datos_json.get('data', datos_json.get('matches', datos_json.get('games', [])))
            else:
                matches = []
            if isinstance(matches, list) and len(matches) > 0:
                return matches, "🟢"
            return [], "🔴 Vacío"
        return [], f"🔴 Error {respuesta.status_code}"
    except Exception as e:
        return [], "🔴 Timeout/Error de Red"

def conversor_seguro(valor):
    """Evita errores de ValueError si el servidor envía 'null' o vacíos"""
    try:
        if valor is None or valor == "null": return 0
        return int(float(valor))
    except:
        return 0

url_api = "https://worldcup26.ir/get/games"
datos_raw, status = obtener_datos_directos(url_api)

if status != "🟢":
    st.error("Error de conexión con el servidor oficial. Por favor, reintenta en unos minutos.")
    st.stop()

# ==========================================
# 4. PROCESAMIENTO DE TABLA (MAPEO REAL)
# ==========================================
lista_limpia = []
for m in datos_raw:
    # Mapeo usando las etiquetas exactas de la estructura plana del servidor
    h_name = m.get('home_team_name_en', 'TBD')
    a_name = m.get('away_team_name_en', 'TBD')
    
    # Ignoramos si no hay equipos definidos
    if h_name == "TBD" and a_name == "TBD":
        continue
        
    # Lógica de estado de partido
    finished = str(m.get('finished', 'FALSE')).upper()
    time_elapsed = str(m.get('time_elapsed', '')).lower()
    
    if finished == "TRUE":
        estado_partido = "FINALIZADO"
    elif time_elapsed == "notstarted":
        estado_partido = "PROGRAMADO"
    else:
        estado_partido = f"EN VIVO ({time_elapsed}')"
        
    grupo_letra = m.get('group', '')
    grupo_formateado = f"Grupo {grupo_letra}" if grupo_letra else 'Fase Final'
    
    lista_limpia.append({
        "Fecha": m.get('local_date', 'TBD'),
        "Partido": f"{h_name} vs {a_name}",
        "Grupo": grupo_formateado,
        "Estado": estado_partido,
        "Local": h_name, 
        "Visita": a_name,
        "G_L": conversor_seguro(m.get('home_score')), 
        "G_V": conversor_seguro(m.get('away_score'))
    })

df = pd.DataFrame(lista_limpia)

# Funciones de Poisson para Estadísticas
def calcular_estadisticas_equipo(equipo, df_datos):
    j_l = df_datos[df_datos['Local'] == equipo]
    j_v = df_datos[df_datos['Visita'] == equipo]
    g_a = pd.to_numeric(j_l['G_L']).sum() + pd.to_numeric(j_v['G_V']).sum()
    g_r = pd.to_numeric(j_l['G_V']).sum() + pd.to_numeric(j_v['G_L']).sum()
    total = len(j_l) + len(j_v)
    if total == 0: return 1.2, 1.2
    return max(g_a / total, 0.5), max(g_r / total, 0.5)

# ==========================================
# 5. SIDEBAR - NAVEGACIÓN
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/FIFA_World_Cup_2026_Logo.png/800px-FIFA_World_Cup_2026_Logo.png", width=150)
st.sidebar.markdown("<br>", unsafe_allow_html=True)

menu = st.sidebar.radio("Navegación", ["📡 En vivo", "📅 Calendario", "📊 Posiciones", "🧠 Análisis Predictivo"])

# ==========================================
# 6. DASHBOARD PRINCIPAL (VISTA "EN VIVO")
# ==========================================
if menu == "📡 En vivo":
    
    # HEADER: TÍTULO Y FECHA
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.markdown("<h1 style='margin:0; font-size: 32px;'>Mundial 2026 — <span style='color: #2fe47a;'>Tablero en Vivo</span></h1>", unsafe_allow_html=True)
        st.markdown("<p style='color: #2fe47a; font-size: 14px;'>● Panel conectado al repositorio central</p>", unsafe_allow_html=True)
    with col_t2:
        fecha_actual = datetime.now().strftime("%d %B %Y").title()
        st.markdown(f"<div style='background-color: #1f2937; padding: 10px 20px; border-radius: 20px; text-align: center; color: #9ca3af; font-size: 14px;'>📅 {fecha_actual}</div>", unsafe_allow_html=True)

    st.markdown("<h3 style='margin-top: 30px;'>Selección de Partido</h3>", unsafe_allow_html=True)

    if df.empty:
        st.warning("El servidor no ha devuelto partidos válidos.")
        st.stop()

    # SELECTOR DE PARTIDO
    partido_sel = st.selectbox("Selecciona el partido a visualizar:", df['Partido'].tolist(), label_visibility="collapsed")
    info = df[df['Partido'] == partido_sel].iloc[0]

    # CÁLCULOS MATEMÁTICOS PARA EL DASHBOARD
    gf_l, gc_l = calcular_estadisticas_equipo(info['Local'], df)
    gf_v, gc_v = calcular_estadisticas_equipo(info['Visita'], df)
    xg_l = (gf_l + gc_v) / 2
    xg_v = (gf_v + gc_l) / 2
    
    pred_l = np.random.poisson(xg_l)
    pred_v = np.random.poisson(xg_v)
    
    # Cálculo de posesión simulada basada en fuerza ofensiva (XG)
    total_xg = xg_l + xg_v
    pos_l = int((xg_l / total_xg) * 100) if total_xg > 0 else 50
    pos_v = 100 - pos_l

    # ESTADO DEL PARTIDO (Color del Badge)
    estado_badge = "#2fe47a" if "PROGRAMADO" not in info['Estado'] else "#6b7280"

    # TARJETA HTML / CSS INYECTADA (DISEÑO GOALSTREAM)
    tarjeta_html = f"""
    <div style="background-color: #151a22; border: 1px solid #1f2937; border-radius: 16px; padding: 30px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);">
        
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <div style="background-color: {estado_badge}; color: #000; padding: 4px 16px; border-radius: 20px; font-weight: bold; font-size: 12px; display: flex; align-items: center; gap: 5px;">
                ● {info['Estado']}
            </div>
            <div style="color: #6b7280; font-size: 14px; font-weight: bold;">{info['Grupo']}</div>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; text-align: center; margin: 40px 0;">
            <div style="width: 30%;">
                <div style="width: 60px; height: 60px; background-color: #1f2937; border-radius: 50%; margin: 0 auto 10px auto; display: flex; align-items: center; justify-content: center; font-size: 24px;">🛡️</div>
                <h2 style="margin: 0; font-size: 20px;">{info['Local']}</h2>
            </div>
            
            <div style="width: 40%;">
                <h1 style="margin: 0; font-size: 64px; font-weight: 900; line-height: 1;">{info['G_L']} - {info['G_V']}</h1>
                <p style="color: #8b5cf6; font-size: 14px; margin-top: 10px; font-style: italic;">🔮 Predicción del Modelo: {pred_l} - {pred_v}</p>
            </div>

            <div style="width: 30%;">
                <div style="width: 60px; height: 60px; background-color: #1f2937; border-radius: 50%; margin: 0 auto 10px auto; display: flex; align-items: center; justify-content: center; font-size: 24px;">🛡️</div>
                <h2 style="margin: 0; font-size: 20px;">{info['Visita']}</h2>
            </div>
        </div>

        <div style="display: flex; justify-content: space-around; text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #1f2937;">
            <div>
                <h3 style="margin: 0; font-size: 24px; color: #2fe47a;">{xg_l:.2f}</h3>
                <span style="color: #6b7280; font-size: 12px; font-weight: bold;">XG (GOLES ESPERADOS)</span>
            </div>
            <div>
                <h3 style="margin: 0; font-size: 24px; color: #ffffff;">{pos_l}% - {pos_v}%</h3>
                <span style="color: #6b7280; font-size: 12px; font-weight: bold;">POSESIÓN PROYECTADA</span>
            </div>
            <div>
                <h3 style="margin: 0; font-size: 24px; color: #2fe47a;">{xg_v:.2f}</h3>
                <span style="color: #6b7280; font-size: 12px; font-weight: bold;">XG (GOLES ESPERADOS)</span>
            </div>
        </div>

        <div style="margin-top: 30px;">
            <div style="display: flex; justify-content: space-between; font-size: 10px; color: #6b7280; margin-bottom: 5px;">
                <span>MOMENTUM MATEMÁTICO</span>
                <span>{pos_l}% | {pos_v}%</span>
            </div>
            <div style="width: 100%; height: 6px; background: linear-gradient(90deg, #2fe47a {pos_l}%, #3b82f6 {pos_l}%); border-radius: 3px;"></div>
        </div>

    </div>
    """
    
    st.markdown(tarjeta_html, unsafe_allow_html=True)
    
else:
    # Vista genérica para las otras pestañas
    st.info("Pestaña en construcción. Selecciona 'En vivo' en la barra lateral para ver el tablero principal.")
    st.dataframe(df, use_container_width=True, hide_index=True)
