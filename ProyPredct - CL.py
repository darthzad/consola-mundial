# ==========================================
# 1. IMPORTACIÓN DE LIBRERÍAS
# ==========================================
import streamlit as st
import pandas as pd
import requests
import numpy as np
from datetime import datetime, timedelta
import pytz

# ==========================================
# 2. CONFIGURACIÓN Y ESTÉTICA "GOALSTREAM"
# ==========================================
st.set_page_config(page_title="WC 2026 Live Dashboard", page_icon="⚽", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b101a; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #1f2937; }
    header { visibility: hidden; }
    .block-container { padding-top: 2rem; max-width: 1200px; }
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. MOTOR DE DATOS (CON CACHÉ DE PROTECCIÓN)
# ==========================================
# Añadimos @st.cache_data por 60 segundos para evitar colapsar el servidor si recargas la página
@st.cache_data(ttl=60)
def obtener_datos_directos(url):
    try:
        respuesta = requests.get(url, timeout=60)
        if respuesta.status_code == 200:
            datos_json = respuesta.json()
            if isinstance(datos_json, list): matches = datos_json
            elif isinstance(datos_json, dict): matches = datos_json.get('data', datos_json.get('matches', datos_json.get('games', [])))
            else: matches = []
            
            if len(matches) > 0: return matches, "🟢"
            return [], "🔴 Servidor vacío"
        return [], f"🔴 Error {respuesta.status_code}"
    except Exception as e:
        return [], "🔴 Timeout/Error de Red"

def conversor_seguro(valor):
    try:
        if valor is None or valor == "null": return 0
        return int(float(valor))
    except: return 0

url_api = "https://worldcup26.ir/get/games"
datos_raw, status = obtener_datos_directos(url_api)

if status != "🟢":
    st.error("⚠️ El servidor oficial está experimentando problemas de conexión. Reintentando...")
    st.stop()

# ==========================================
# 4. PROCESAMIENTO E INTELIGENCIA DEL MODELO
# ==========================================
lista_limpia = []
for m in datos_raw:
    h_name = m.get('home_team_name_en', 'TBD')
    a_name = m.get('away_team_name_en', 'TBD')
    if h_name == "TBD" and a_name == "TBD": continue
        
    finished = str(m.get('finished', 'FALSE')).upper()
    time_elapsed = str(m.get('time_elapsed', '')).lower()
    
    if finished == "TRUE": estado_partido = "FINALIZADO"
    elif time_elapsed == "notstarted": estado_partido = "PROGRAMADO"
    else: estado_partido = f"EN VIVO ({time_elapsed}')"
        
    grupo_letra = m.get('group', '')
    grupo_formateado = f"Grupo {grupo_letra}" if grupo_letra else 'Fase Final'
    
    lista_limpia.append({
        "Fecha_Raw": m.get('local_date', '01/01/2026 00:00'),
        "Partido": f"{h_name} vs {a_name}",
        "Grupo": grupo_formateado,
        "Estado": estado_partido,
        "Local": h_name, "Visita": a_name,
        "G_L": conversor_seguro(m.get('home_score')), 
        "G_V": conversor_seguro(m.get('away_score'))
    })

df = pd.DataFrame(lista_limpia)
# Convertir textos de fecha a objetos de tiempo reales para poder filtrarlos
df['Fecha_Obj'] = pd.to_datetime(df['Fecha_Raw'], format='mixed', errors='coerce')

def calcular_fuerza(equipo, df_datos):
    j_l = df_datos[df_datos['Local'] == equipo]
    j_v = df_datos[df_datos['Visita'] == equipo]
    g_a = pd.to_numeric(j_l['G_L']).sum() + pd.to_numeric(j_v['G_V']).sum()
    g_r = pd.to_numeric(j_l['G_V']).sum() + pd.to_numeric(j_v['G_L']).sum()
    total = len(j_l) + len(j_v)
    if total == 0: return 1.2, 1.2
    return max(g_a / total, 0.5), max(g_r / total, 0.5)

def predecir_partido(local, visita, df):
    """Genera la predicción fijando una semilla para que el resultado pasado no cambie"""
    gf_l, gc_l = calcular_fuerza(local, df)
    gf_v, gc_v = calcular_fuerza(visita, df)
    xg_l = (gf_l + gc_v) / 2
    xg_v = (gf_v + gc_l) / 2
    
    # Truco de Semilla: Usamos las letras de los países para fijar la matemática
    semilla = sum(ord(c) for c in local + visita)
    np.random.seed(semilla)
    
    pred_l = np.random.poisson(xg_l)
    pred_v = np.random.poisson(xg_v)
    return xg_l, xg_v, pred_l, pred_v

def evaluar_acierto(gl_real, gv_real, gl_pred, gv_pred):
    """Compara si atinamos al Ganador, Perdedor o Empate (Formato 1X2)"""
    res_real = 'L' if gl_real > gv_real else ('V' if gv_real > gl_real else 'E')
    res_pred = 'L' if gl_pred > gv_pred else ('V' if gv_pred > gl_pred else 'E')
    return res_real == res_pred

def crear_tarjeta_principal(info, xg_l, xg_v, pred_l, pred_v):
    """Genera el HTML de la tarjeta grande (GoalStream)"""
    total_xg = xg_l + xg_v
    pos_l = int((xg_l / total_xg) * 100) if total_xg > 0 else 50
    pos_v = 100 - pos_l
    estado_badge = "#2fe47a" if "PROGRAMADO" not in info['Estado'] else "#6b7280"
    
    return f"""
    <div style="background-color: #151a22; border: 1px solid #1f2937; border-radius: 16px; padding: 30px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5); margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <div style="background-color: {estado_badge}; color: #000; padding: 4px 16px; border-radius: 20px; font-weight: bold; font-size: 12px;">● {info['Estado']}</div>
            <div style="color: #6b7280; font-size: 14px; font-weight: bold;">{info['Grupo']} | {info['Fecha_Raw']}</div>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; text-align: center; margin: 40px 0;">
            <div style="width: 30%;"><h2 style="margin: 0; font-size: 24px;">{info['Local']}</h2></div>
            <div style="width: 40%;">
                <h1 style="margin: 0; font-size: 64px; font-weight: 900; line-height: 1;">{info['G_L']} - {info['G_V']}</h1>
                <p style="color: #8b5cf6; font-size: 14px; margin-top: 10px; font-style: italic;">🔮 Predicción: {pred_l} - {pred_v}</p>
            </div>
            <div style="width: 30%;"><h2 style="margin: 0; font-size: 24px;">{info['Visita']}</h2></div>
        </div>
        <div style="display: flex; justify-content: space-around; text-align: center; border-top: 1px solid #1f2937; padding-top: 20px;">
            <div><h3 style="margin: 0; font-size: 24px; color: #2fe47a;">{xg_l:.2f}</h3><span style="color: #6b7280; font-size: 10px;">XG</span></div>
            <div><h3 style="margin: 0; font-size: 24px; color: #fff;">{pos_l}% - {pos_v}%</h3><span style="color: #6b7280; font-size: 10px;">POSESIÓN</span></div>
            <div><h3 style="margin: 0; font-size: 24px; color: #2fe47a;">{xg_v:.2f}</h3><span style="color: #6b7280; font-size: 10px;">XG</span></div>
        </div>
    </div>
    """

# ==========================================
# 5. SIDEBAR - NAVEGACIÓN
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/FIFA_World_Cup_2026_Logo.png/800px-FIFA_World_Cup_2026_Logo.png", width=150)
menu = st.sidebar.radio("Navegación", ["📡 En vivo", "📅 Calendario", "📊 Posiciones"])

# ==========================================
# 6. DASHBOARD PRINCIPAL (AUTOMATIZADO)
# ==========================================
if menu == "📡 En vivo":
    
    # 6.1 HEADER Y LÓGICA DE TIEMPO
    tz_nicaragua = pytz.timezone('America/Managua')
    fecha_actual_nic = datetime.now(tz_nicaragua).date()
    fecha_manana_nic = fecha_actual_nic + timedelta(days=1)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("<h1 style='margin:0; font-size: 32px;'>Mundial 2026 — <span style='color: #2fe47a;'>Autopilot</span></h1>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div style='background-color: #1f2937; padding: 10px; border-radius: 20px; text-align: center; color: #9ca3af;'>📅 {fecha_actual_nic.strftime('%d %b %Y')}</div>", unsafe_allow_html=True)

    st.markdown("---")
    
    # 6.2 SECCIÓN: PARTIDOS DE HOY Y MAÑANA (Sin listas desplegables)
    st.subheader("🗓️ Partidos en Agenda (Hoy y Mañana)")
    
    # Filtrar partidos basados en la fecha
    df['Solo_Fecha'] = df['Fecha_Obj'].dt.date
    partidos_agenda = df[(df['Solo_Fecha'] == fecha_actual_nic) | (df['Solo_Fecha'] == fecha_manana_nic)]
    
    if partidos_agenda.empty:
        st.info(f"No hay partidos programados para el {fecha_actual_nic.strftime('%d/%m')} ni para el {fecha_manana_nic.strftime('%d/%m')} en la base de datos.")
    else:
        # Dibujar tarjetas dinámicamente
        for idx, row in partidos_agenda.iterrows():
            xg_l, xg_v, pred_l, pred_v = predecir_partido(row['Local'], row['Visita'], df)
            st.markdown(crear_tarjeta_principal(row, xg_l, xg_v, pred_l, pred_v), unsafe_allow_html=True)

    # 6.3 SECCIÓN: EVALUACIÓN DEL MODELO (Aciertos y Fallos)
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.subheader("🎯 Auditoría del Modelo Predictivo")
    st.markdown("<p style='color: #9ca3af;'>Se evalúa si el modelo acertó al ganador o al empate de los partidos ya finalizados.</p>", unsafe_allow_html=True)
    
    partidos_finalizados = df[df['Estado'] == "FINALIZADO"]
    
    if partidos_finalizados.empty:
        st.warning("Aún no hay partidos finalizados para auditar.")
    else:
        # Mostrar en cuadrícula de 3 columnas
        columnas = st.columns(3)
        col_idx = 0
        
        for idx, row in partidos_finalizados.iterrows():
            xg_l, xg_v, pred_l, pred_v = predecir_partido(row['Local'], row['Visita'], df)
            acierto = evaluar_acierto(row['G_L'], row['G_V'], pred_l, pred_v)
            
            # Lógica de colores: Verde (#10b981) si acertó ganador/empate, Rojo (#ef4444) si falló
            color_borde = "#10b981" if acierto else "#ef4444"
            icono = "✅ ACIERTO" if acierto else "❌ FALLO"
            
            tarjeta_historial = f"""
            <div style="background-color: #111827; border-left: 4px solid {color_borde}; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                <div style="font-size: 12px; color: #9ca3af; margin-bottom: 5px;">{row['Fecha_Raw'][:10]} | {row['Grupo']}</div>
                <div style="font-weight: bold; font-size: 16px;">{row['Local']} {row['G_L']} - {row['G_V']} {row['Visita']}</div>
                <div style="display: flex; justify-content: space-between; margin-top: 10px; font-size: 12px;">
                    <span style="color: #8b5cf6;">Predicción: {pred_l}-{pred_v}</span>
                    <span style="color: {color_borde}; font-weight: bold;">{icono}</span>
                </div>
            </div>
            """
            columnas[col_idx % 3].markdown(tarjeta_historial, unsafe_allow_html=True)
            col_idx += 1

else:
    st.info("Pestaña en construcción. Selecciona 'En vivo'.")
    st.dataframe(df, use_container_width=True)
