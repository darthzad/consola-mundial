# ==========================================
# 1. IMPORTACIÓN DE LIBRERÍAS
# ==========================================
import streamlit as st
import pandas as pd
import requests
import numpy as np
import math
from datetime import datetime, timedelta
import pytz
import json
import os

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
    /* Estilos para los expanders (acordeones) */
    div[data-testid="stExpander"] { background-color: #151a22; border: 1px solid #1f2937; border-radius: 12px; }
    div[data-testid="stExpander"] > summary { color: #ffffff; font-weight: bold; font-size: 16px; padding: 10px; }
    div[data-testid="stMetricValue"] { color: #2fe47a; }
    </style>
    """, unsafe_allow_html=True)

# DICCIONARIO DE BANDERAS
BANDERAS = {
    "Mexico": "🇲🇽", "South Africa": "🇿🇦", "Argentina": "🇦🇷", "Brazil": "🇧🇷",
    "United States": "🇺🇸", "Canada": "🇨🇦", "France": "🇫🇷", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Spain": "🇪🇸", "Germany": "🇩🇪", "Italy": "🇮🇹", "Portugal": "🇵🇹",
    "Netherlands": "🇳🇱", "Belgium": "🇧🇪", "Uruguay": "🇺🇾", "Colombia": "🇨🇴",
    "Chile": "🇨🇱", "Peru": "🇵🇪", "Japan": "🇯🇵", "South Korea": "🇰🇷",
    "Australia": "🇦🇺", "Morocco": "🇲🇦", "Senegal": "🇸🇳", "Egypt": "🇪🇬",
    "Nigeria": "🇳🇬", "Saudi Arabia": "🇸🇦", "Iran": "🇮🇷", "Ecuador": "🇪🇨",
    "Croatia": "🇭🇷", "Switzerland": "🇨🇭", "Denmark": "🇩🇰", "Sweden": "🇸🇪",
    "Poland": "🇵🇱", "Serbia": "🇷🇸", "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿", "Costa Rica": "🇨🇷",
    "Panama": "🇵🇦", "Honduras": "🇭🇳", "Jamaica": "🇯🇲", "El Salvador": "🇸🇻",
    "Guatemala": "🇬🇹", "Nicaragua": "🇳🇮", "Curaçao": "🇨🇼", "Haiti": "🇭🇹",
    "Trinidad and Tobago": "🇹🇹", "Czechia": "🇨🇿", "Bosnia and Herz.": "🇧🇦",
    "Paraguay": "🇵🇾", "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿"
}

def obtener_bandera(equipo):
    return BANDERAS.get(equipo, "🏳️")

# ==========================================
# 3. MOTOR DE DATOS (SISTEMA ANTI-CAÍDAS)
# ==========================================
def obtener_datos_resilientes(url):
    archivo_backup = "backup_mundial.json"
    try:
        respuesta = requests.get(url, timeout=15)
        if respuesta.status_code == 200:
            datos_json = respuesta.json()
            if isinstance(datos_json, list): matches = datos_json
            elif isinstance(datos_json, dict): matches = datos_json.get('data', datos_json.get('matches', datos_json.get('games', [])))
            else: matches = []
            
            if len(matches) > 0:
                with open(archivo_backup, 'w', encoding='utf-8') as f:
                    json.dump(matches, f)
                return matches, "🟢 Conectado"
    except Exception: pass

    if os.path.exists(archivo_backup):
        with open(archivo_backup, 'r', encoding='utf-8') as f:
            return json.load(f), "🟡 Offline (Respaldo)"
    return [], "🔴 Caído"

def conversor_seguro(valor):
    try:
        if valor is None or valor == "null": return 0
        return int(float(valor))
    except: return 0

url_api = "https://worldcup26.ir/get/games"
with st.spinner("Sincronizando base de datos..."):
    datos_raw, status = obtener_datos_resilientes(url_api)

if "🔴" in status:
    st.error("⚠️ Servidor caído. Intenta más tarde.")
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
    
    lista_limpia.append({
        "Fecha_Raw": m.get('local_date', '01/01/2026 00:00'),
        "Partido": f"{h_name} vs {a_name}",
        "Grupo": f"Grupo {grupo_letra}" if grupo_letra else 'Fase Final',
        "Estado": estado_partido,
        "Local": h_name, "Visita": a_name,
        "G_L": conversor_seguro(m.get('home_score')), 
        "G_V": conversor_seguro(m.get('away_score'))
    })

df = pd.DataFrame(lista_limpia)
df['Fecha_Obj'] = pd.to_datetime(df['Fecha_Raw'], format='mixed', errors='coerce')

def calcular_fuerza(equipo, df_datos):
    j_l = df_datos[df_datos['Local'] == equipo]
    j_v = df_datos[df_datos['Visita'] == equipo]
    g_a = pd.to_numeric(j_l['G_L']).sum() + pd.to_numeric(j_v['G_V']).sum()
    g_r = pd.to_numeric(j_l['G_V']).sum() + pd.to_numeric(j_v['G_L']).sum()
    total = len(j_l) + len(j_v)
    if total == 0: return 1.2, 1.2
    return max(g_a / total, 0.5), max(g_r / total, 0.5)

def calcular_probabilidades_1x2(xg_l, xg_v):
    p_l, p_e, p_v = 0, 0, 0
    for i in range(10):
        for j in range(10):
            prob = (math.exp(-xg_l) * (xg_l**i) / math.factorial(i)) * (math.exp(-xg_v) * (xg_v**j) / math.factorial(j))
            if i > j: p_l += prob
            elif i == j: p_e += prob
            else: p_v += prob
    total = p_l + p_e + p_v
    if total == 0: return 33.3, 33.3, 33.3
    return (p_l/total)*100, (p_e/total)*100, (p_v/total)*100

def predecir_partido(local, visita, df):
    gf_l, gc_l = calcular_fuerza(local, df)
    gf_v, gc_v = calcular_fuerza(visita, df)
    xg_l = (gf_l + gc_v) / 2
    xg_v = (gf_v + gc_l) / 2
    np.random.seed(sum(ord(c) for c in local + visita))
    return xg_l, xg_v, np.random.poisson(xg_l), np.random.poisson(xg_v)

def evaluar_acierto(gl_real, gv_real, gl_pred, gv_pred):
    res_real = 'L' if gl_real > gv_real else ('V' if gv_real > gl_real else 'E')
    res_pred = 'L' if gl_pred > gv_pred else ('V' if gv_pred > gl_pred else 'E')
    return res_real == res_pred

# ==========================================
# 5. SIDEBAR Y MÉTRICAS GLOBALES
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/FIFA_World_Cup_2026_Logo.png/800px-FIFA_World_Cup_2026_Logo.png", width=150)
st.sidebar.markdown(f"<p style='color: #9ca3af; font-size: 12px; text-align: center;'>Servidor: {status}</p>", unsafe_allow_html=True)
menu = st.sidebar.radio("Navegación", ["📡 Tablero en Vivo", "📊 Histórico de Datos"])

if menu == "📡 Tablero en Vivo":
    
    # ENCABEZADO
    tz_nicaragua = pytz.timezone('America/Managua')
    fecha_actual_nic = datetime.now(tz_nicaragua).date()
    
    col1, col2 = st.columns([3, 1])
    with col1: st.markdown("<h1 style='margin:0; font-size: 32px;'>Consola Data-Driven <span style='color: #2fe47a;'>WC 26</span></h1>", unsafe_allow_html=True)
    with col2: st.markdown(f"<div style='background-color: #1f2937; padding: 10px; border-radius: 20px; text-align: center; color: #9ca3af;'>📅 {fecha_actual_nic.strftime('%d %b %Y')} (NIC)</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ------------------------------------------
    # NUEVO: DASHBOARD DE ESTADÍSTICAS GLOBALES
    # ------------------------------------------
    st.subheader("📈 Rendimiento Global del Modelo")
    
    partidos_finalizados = df[df['Estado'] == "FINALIZADO"]
    total_juegos = len(df)
    juegos_listos = len(partidos_finalizados)
    juegos_pendientes = total_juegos - juegos_listos
    
    aciertos = 0
    for idx, row in partidos_finalizados.iterrows():
        _, _, pred_l, pred_v = predecir_partido(row['Local'], row['Visita'], df)
        if evaluar_acierto(row['G_L'], row['G_V'], pred_l, pred_v):
            aciertos += 1
            
    tasa_acierto = (aciertos / juegos_listos * 100) if juegos_listos > 0 else 0.0

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Partidos Totales", total_juegos)
    kpi2.metric("Pendientes / En Vivo", juegos_pendientes)
    kpi3.metric("Juegos Analizados", juegos_listos)
    kpi4.metric("Precisión (1X2)", f"{tasa_acierto:.1f}%")
    
    st.markdown("<br>", unsafe_allow_html=True)

    # ------------------------------------------
    # SECCIÓN: PARTIDOS DE HOY Y MAÑANA (ACORDEONES)
    # ------------------------------------------
    st.subheader("🗓️ Partidos en Agenda (Próximas 48 hrs)")
    fecha_manana_nic = fecha_actual_nic + timedelta(days=1)
    df['Solo_Fecha'] = df['Fecha_Obj'].dt.date
    partidos_agenda = df[(df['Solo_Fecha'] == fecha_actual_nic) | (df['Solo_Fecha'] == fecha_manana_nic)]
    
    if partidos_agenda.empty:
        st.info("No hay partidos programados para hoy ni mañana.")
    else:
        for idx, row in partidos_agenda.iterrows():
            flag_l = obtener_bandera(row['Local'])
            flag_v = obtener_bandera(row['Visita'])
            titulo = f"{row['Fecha_Raw'][-5:]} | {flag_l} {row['Local']}  {row['G_L']} - {row['G_V']}  {row['Visita']} {flag_v}  ({row['Estado']})"
            
            with st.expander(titulo):
                xg_l, xg_v, pred_l, pred_v = predecir_partido(row['Local'], row['Visita'], df)
                prob_l, prob_e, prob_v = calcular_probabilidades_1x2(xg_l, xg_v)
                
                # Renderizado limpio sin errores HTML
                st.markdown(f"<h4 style='text-align: center; color: #8b5cf6; font-style: italic;'>🎯 Marcador Predicho: {pred_l} - {pred_v}</h4>", unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns(3)
                c1.metric(f"XG - {row['Local']}", f"{xg_l:.2f}")
                c2.metric("Prob. Empate", f"{prob_e:.1f}%")
                c3.metric(f"XG - {row['Visita']}", f"{xg_v:.2f}")
                
                # Barra de probabilidades formateada a la izquierda (Sin espacios iniciales)
                barra_html = f"""
<div style="text-align: left; font-size: 10px; color: #6b7280; margin-bottom: 5px; margin-top: 15px;">PROBABILIDADES DE VICTORIA (1X2)</div>
<div style="display: flex; width: 100%; height: 8px; border-radius: 4px; overflow: hidden;">
<div style="width: {prob_l}%; background-color: #2fe47a;" title="Local: {prob_l:.1f}%"></div>
<div style="width: {prob_e}%; background-color: #6b7280;" title="Empate: {prob_e:.1f}%"></div>
<div style="width: {prob_v}%; background-color: #3b82f6;" title="Visita: {prob_v:.1f}%"></div>
</div>
<div style="display: flex; justify-content: space-between; font-size: 12px; font-weight: bold; margin-top: 5px;">
<span style="color: #2fe47a;">{prob_l:.1f}% (L)</span>
<span style="color: #6b7280;">{prob_e:.1f}% (E)</span>
<span style="color: #3b82f6;">{prob_v:.1f}% (V)</span>
</div>
"""
                st.markdown(barra_html, unsafe_allow_html=True)

    # ------------------------------------------
    # SECCIÓN: AUDITORÍA
    # ------------------------------------------
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.subheader("🎯 Auditoría de Aciertos")
    
    if partidos_finalizados.empty:
        st.warning("Aún no hay partidos finalizados para auditar.")
    else:
        columnas = st.columns(3)
        for col_idx, (idx, row) in enumerate(partidos_finalizados.iterrows()):
            xg_l, xg_v, pred_l, pred_v = predecir_partido(row['Local'], row['Visita'], df)
            acierto = evaluar_acierto(row['G_L'], row['G_V'], pred_l, pred_v)
            
            color_borde = "#10b981" if acierto else "#ef4444"
            icono = "✅ ACIERTO" if acierto else "❌ FALLO"
            flag_l = obtener_bandera(row['Local'])
            flag_v = obtener_bandera(row['Visita'])
            
            # HTML formateado a la izquierda
            tarjeta_historial = f"""
<div style="background-color: #111827; border-left: 4px solid {color_borde}; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
<div style="font-size: 12px; color: #9ca3af; margin-bottom: 5px;">{row['Fecha_Raw'][:10]} | {row['Grupo']}</div>
<div style="font-weight: bold; font-size: 16px;">{flag_l} {row['Local']} {row['G_L']} - {row['G_V']} {row['Visita']} {flag_v}</div>
<div style="display: flex; justify-content: space-between; margin-top: 10px; font-size: 12px;">
<span style="color: #8b5cf6;">Pred: {pred_l}-{pred_v}</span>
<span style="color: {color_borde}; font-weight: bold;">{icono}</span>
</div>
</div>
"""
            columnas[col_idx % 3].markdown(tarjeta_historial, unsafe_allow_html=True)

else:
    st.title("Base de Datos Histórica")
    st.dataframe(df.drop(columns=['Fecha_Obj']), use_container_width=True)
