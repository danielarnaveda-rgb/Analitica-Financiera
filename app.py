import hashlib
# --- PARCHE BLINDADO PARA REPORTLAB ---
class Md5Wrapper:
    def __init__(self, original):
        self.original = original
    def __call__(self, *args, **kwargs):
        kwargs.pop('usedforsecurity', None)
        return self.original(*args, **kwargs)
    def __getattr__(self, name):
        return getattr(self.original, name)

hashlib.md5 = Md5Wrapper(hashlib.md5)
# -------------------------------------

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
import io

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

st.set_page_config(page_title="Sistema Financiero - Esc. Téc. Nº 10", page_icon="🏫", layout="wide")

# --- DISEÑO Y ESTILOS INSTITUCIONALES (Azules sobrios y Rojos sutiles) ---
st.markdown("""
    <style>
    .stApp {
        background-color: #f8fafc;
    }
    /* Tarjetas de alertas sutiles con rojos semitransparentes */
    .element-container div.stAlert {
        background-color: rgba(239, 68, 68, 0.08);
        border-left: 4px solid rgba(239, 68, 68, 0.4);
        color: #1e293b;
    }
    </style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS ---
def obtener_conexion():
    return sqlite3.connect('finanzas.db')

def inicializar_base_de_datos():
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cuentas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE,
            tipo TEXT,
            saldo REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transacciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cuenta_id INTEGER,
            categoria TEXT,
            monto REAL,
            tipo TEXT,
            fecha TEXT,
            descripcion TEXT,
            FOREIGN KEY (cuenta_id) REFERENCES cuentas (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS presupuestos (
            categoria TEXT PRIMARY KEY,
            limite REAL
        )
    ''')

    cursor.execute("SELECT COUNT(*) FROM cuentas")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO cuentas (nombre, tipo, saldo) VALUES (?, ?, ?)", [
            ('Banco Principal', 'Banco', 500000.0),
            ('Caja Chica', 'Efectivo', 50000.0),
            ('Mercado Pago', 'Billetera', 120000.0)
        ])

    cursor.execute("SELECT COUNT(*) FROM presupuestos")
    if cursor.fetchone()[0] == 0:
        defaults = [('Insumos', 200000.0), ('Servicios', 100000.0), ('Sueldos', 400000.0), ('Mantenimiento', 150000.0), ('Impuestos', 80000.0)]
        cursor.executemany("INSERT INTO presupuestos VALUES (?, ?)", defaults)

    conn.commit()
    conn.close()

def cargar_datos():
    conn = obtener_conexion()
    df_trans = pd.read_sql_query("SELECT * FROM transacciones", conn)
    df_cuentas = pd.read_sql_query("SELECT * FROM cuentas", conn)
    conn.close()
    if not df_trans.empty:
        df_trans['fecha'] = pd.to_datetime(df_trans['fecha'])
    return df_trans, df_cuentas

inicializar_base_de_datos()
df_trans, df_cuentas = cargar_datos()

# --- BARRA LATERAL INSTITUCIONAL ---
st.sidebar.title("🏫 Panel Institucional")
st.sidebar.markdown("**Esc. Téc. Nº 10 'Martín M. de Güemes'**")
st.sidebar.markdown("---")

st.sidebar.header("🔍 Filtros de Visualización")
fecha_min = df_trans['fecha'].min().date() if not df_trans.empty else datetime.now().date()
fecha_max = df_trans['fecha'].max().date() if not df_trans.empty else datetime.now().date()

rango_fechas = st.sidebar.date_input("Rango de Fechas", [fecha_min, fecha_max])
cuentas_opciones = ["Todas"] + list(df_cuentas['nombre'].unique()) if not df_cuentas.empty else ["Todas"]
cuenta_filtrada = st.sidebar.selectbox("Filtrar por Cuenta", cuentas_opciones)

st.sidebar.markdown("---")

st.sidebar.header("➕ Registrar Nuevo Movimiento")
cuentas_dict = dict(zip(df_cuentas['nombre'], df_cuentas['id'])) if not df_cuentas.empty else {}

with st.sidebar.form("form_alta_sidebar"):
    cuenta_sel = st.selectbox("Cuenta", list(cuentas_dict.keys())) if cuentas_dict else None
    tipo_mov = st.selectbox("Tipo", ["Egreso", "Ingreso"])
    cat_opciones = ['Insumos', 'Servicios', 'Sueldos', 'Mantenimiento', 'Impuestos'] if tipo_mov == "Egreso" else ['insumos', 'servicios', 'Sueldos' 'Mantenimiento' 'Impuestos']
    cat_sel = st.selectbox("Categoría", cat_opciones)
    monto_in = st.number_input("Monto ($)", min_value=1.0, step=100.0)
    fecha_in = st.date_input("Fecha", datetime.now())
    desc_in = st.text_input("Descripción")
    
    submit_alta = st.form_submit_button("Guardar Movimiento")

if submit_alta and cuenta_sel:
    conn = obtener_conexion()
    cursor = conn.cursor()
    c_id = cuentas_dict[cuenta_sel]
    cursor.execute("INSERT INTO transacciones (cuenta_id, categoria, monto, tipo, fecha, descripcion) VALUES (?, ?, ?, ?, ?, ?)",
                   (c_id, cat_sel, monto_in, tipo_mov, fecha_in.strftime('%Y-%m-%d'), desc_in))
    
    monto_efecto = monto_in if tipo_mov == "Ingreso" else -monto_in
    cursor.execute("UPDATE cuentas SET saldo = saldo + ? WHERE id = ?", (monto_efecto, c_id))
    
    conn.commit()
    conn.close()
    st.success("¡Movimiento guardado con éxito! Recargue la página (F5) para ver los cambios.")

# --- FILTROS APLICADOS ---
df_filtrado = df_trans.copy()
if len(rango_fechas) == 2 and not df_filtrado.empty:
    df_filtrado = df_filtrado[(df_filtrado['fecha'].dt.date >= rango_fechas[0]) & (df_filtrado['fecha'].dt.date <= rango_fechas[1])]

if cuenta_filtrada != "Todas" and not df_filtrado.empty:
    c_id = df_cuentas[df_cuentas['nombre'] == cuenta_filtrada]['id'].values[0]
    df_filtrado = df_filtrado[df_filtrado['cuenta_id'] == c_id]

# --- DASHBOARD PRINCIPAL ---
st.title("📊 Plataforma de Analítica Financiera")
st.markdown("### Escuela Técnica N.º 10 'Martín Miguel de Güemes' — Gestión Contable y de Proyectos")
st.markdown("---")

col1, col2, col3, col4 = st.columns(4)
ingresos = df_filtrado[df_filtrado['tipo'] == 'Ingreso']['monto'].sum() if not df_filtrado.empty else 0.0
egresos = df_filtrado[df_filtrado['tipo'] == 'Egreso']['monto'].sum() if not df_filtrado.empty else 0.0
balance = ingresos - egresos
saldo_cuentas = df_cuentas['saldo'].sum() if not df_cuentas.empty else 0.0

col1.metric("Ingresos Filtrados", f"${ingresos:,.2f}")
col2.metric("Egresos Filtrados", f"${egresos:,.2f}")
col3.metric("Balance del Período", f"${balance:,.2f}")
col4.metric("Saldo Total en Cuentas", f"${saldo_cuentas:,.2f}")

st.markdown("---")

# --- PRESUPUESTOS Y ASESOR ---
st.subheader("🚨 Control Presupuestario y Asesor Inteligente")
conn = obtener_conexion()
df_pres = pd.read_sql_query("SELECT * FROM presupuestos", conn)
conn.close()
presupuestos_dict = dict(zip(df_pres['categoria'], df_pres['limite'])) if not df_pres.empty else {}

if presupuestos_dict:
    cols_pres = st.columns(len(presupuestos_dict))
    df_egresos_cat = df_filtrado[df_filtrado['tipo'] == 'Egreso'].groupby('categoria')['monto'].sum().to_dict() if not df_filtrado.empty else {}
    consejos_activos = []

    for idx, (cat, limite) in enumerate(presupuestos_dict.items()):
        gastado = df_egresos_cat.get(cat, 0.0)
        porcentaje = (gastado / limite) * 100 if limite > 0 else 0
        with cols_pres[idx]:
            if porcentaje >= 100:
                st.error(f"**{cat}**\n\n${gastado:,.0f} / ${limite:,.0f}\n\nExcedido ({porcentaje:.0f}%)")
                consejos_activos.append(f"🔴 **Presupuesto Excedido en {cat}**: Límite superado. Se sugiere evaluar reasignación de partidas.")
            elif porcentaje >= 80:
                st.warning(f"**{cat}**\n\n${gastado:,.0f} / ${limite:,.0f}\n\nAlerta ({porcentaje:.0f}%)")
                consejos_activos.append(f"🟡 **Alerta en {cat}**: Cerca del límite ({porcentaje:.0f}%). Monitorear de cerca.")
            else:
                st.success(f"**{cat}**\n\n${gastado:,.0f} / ${limite:,.0f}\n\nOK ({porcentaje:.0f}%)")

    if consejos_activos:
        st.markdown("### 💡 Sugerencias del Asesor Institucional")
        for consejo in consejos_activos:
            st.info(consejo)
    else:
        st.success("🟢 **Estado Óptimo**: Ejecución presupuestaria dentro de los parámetros esperados.")

st.markdown("---")

# --- GRÁFICOS CON TONOS AZULES NO VIBRANTES ---
palette_azules = ['#2C3E50', '#34495E', '#2980B9', '#4A6572', '#546E7A']

cg1, cg2 = st.columns(2)
with cg1:
    st.subheader("Distribución de Egresos")
    df_egr = df_filtrado[df_filtrado['tipo'] == 'Egreso'] if not df_filtrado.empty else pd.DataFrame()
    if not df_egr.empty:
        fig_pie = px.pie(df_egr, values='monto', names='categoria', hole=0.4, color_discrete_sequence=palette_azules)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No hay egresos en el período.")

with cg2:
    st.subheader("Evolución Temporal")
    if not df_filtrado.empty:
        df_linea = df_filtrado.groupby(['fecha', 'tipo'])['monto'].sum().reset_index()
        fig_line = px.line(df_linea, x='fecha', y='monto', color='tipo', markers=True, color_discrete_map={'Ingreso': '#2980B9', 'Egreso': '#C0392B'})
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("No hay movimientos en el período.")

st.markdown("---")

# --- HISTORIAL Y EDICIÓN ---
st.subheader("📜 Registro Histórico y Gestión de Movimientos")
if not df_trans.empty:
    st.dataframe(df_trans.sort_values(by='fecha', ascending=False), use_container_width=True)
    
    st.markdown("### ✏️ Modificar o Eliminar Movimiento")
    col_id, _ = st.columns([2, 1])
    with col_id:
        id_seleccionado = st.number_input("ID del movimiento a editar:", min_value=int(df_trans['id'].min()), max_value=int(df_trans['id'].max()), step=1)
    
    row_sel = df_trans[df_trans['id'] == id_seleccionado]

    if not row_sel.empty:
        reg = row_sel.to_dict(orient='records')[0]
        with st.form("form_edicion"):
            st.write(f"Editando ID: **{reg['id']}**")
            cuentas_dict_inv = dict(zip(df_cuentas['id'], df_cuentas['nombre']))
            nombre_cuenta_act = cuentas_dict_inv.get(reg['cuenta_id'], list(cuentas_dict.keys())[0])
            
            edit_cuenta = st.selectbox("Cuenta", list(cuentas_dict.keys()), index=list(cuentas_dict.keys()).index(nombre_cuenta_act) if nombre_cuenta_act in cuentas_dict else 0)
            edit_tipo = st.selectbox("Tipo", ["Egreso", "Ingreso"], index=0 if reg['tipo'] == "Egreso" else 1)
            cat_opciones_edit = ['Insumos', 'Servicios', 'Sueldos', 'Mantenimiento', 'Impuestos'] if edit_tipo == "Egreso" else ['Ventas', 'Cobro Servicios', 'Rendimientos']
            idx_cat = cat_opciones_edit.index(reg['categoria']) if reg['categoria'] in cat_opciones_edit else 0
            edit_cat = st.selectbox("Categoría", cat_opciones_edit, index=idx_cat)
            edit_monto = st.number_input("Monto ($)", value=float(reg['monto']), min_value=1.0, step=100.0)
            edit_fecha = st.date_input("Fecha", pd.to_datetime(reg['fecha']).date())
            edit_desc = st.text_input("Descripción", value=str(reg['descripcion']))

            c_f1, c_f2 = st.columns(2)
            with c_f1:
                btn_act = st.form_submit_button("💾 Guardar Cambios")
            with c_f2:
                btn_del = st.form_submit_button("🗑️ Eliminar")
            
            if btn_act:
                conn = obtener_conexion()
                cursor = conn.cursor()
                monto_viejo = reg['monto']
                efecto_viejo = -monto_viejo if reg['tipo'] == "Ingreso" else monto_viejo
                cursor.execute("UPDATE cuentas SET saldo = saldo + ? WHERE id = ?", (efecto_viejo, reg['cuenta_id']))
                
                nuevo_c_id = cuentas_dict[edit_cuenta]
                cursor.execute('''
                    UPDATE transacciones 
                    SET cuenta_id = ?, categoria = ?, monto = ?, tipo = ?, fecha = ?, descripcion = ?
                    WHERE id = ?
                ''', (nuevo_c_id, edit_cat, edit_monto, edit_tipo, edit_fecha.strftime('%Y-%m-%d'), edit_desc, id_seleccionado))
                
                nuevo_efecto = edit_monto if edit_tipo == "Ingreso" else -edit_monto
                cursor.execute("UPDATE cuentas SET saldo = saldo + ? WHERE id = ?", (nuevo_efecto, nuevo_c_id))
                conn.commit()
                conn.close()
                st.success("¡Actualizado con éxito! Presione F5 para reflejar.")

            if btn_del:
                conn = obtener_conexion()
                cursor = conn.cursor()
                monto_del = reg['monto']
                efecto_del = -monto_del if reg['tipo'] == "Ingreso" else monto_del
                cursor.execute("UPDATE cuentas SET saldo = saldo + ? WHERE id = ?", (efecto_del, reg['cuenta_id']))
                cursor.execute("DELETE FROM transacciones WHERE id = ?", (id_seleccionado,))
                conn.commit()
                conn.close()
                st.success("¡Eliminado correctamente! Presione F5 para reflejar.")
else:
    st.info("No hay registros disponibles para editar.")

st.markdown("---")

# --- EXPORTACIÓN ---
st.subheader("📄 Exportación de Reportes Institucionales")
col_exp1, col_exp2 = st.columns(2)

with col_exp1:
    if not df_filtrado.empty:
        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
            df_filtrado.to_excel(writer, index=False, sheet_name='Transacciones')
        st.download_button(
            label="📊 Exportar a Excel (.xlsx)",
            data=buffer_excel.getvalue(),
            file_name="reporte_financiero_escuela.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    else:
        st.button("📊 Exportar a Excel (.xlsx)", disabled=True, use_container_width=True)

with col_exp2:
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)
    c.drawString(50, 750, "ESCUELA TÉCNICA N.º 10 - REPORTE FINANCIERO")
    c.drawString(50, 735, f"Fecha de emisión: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    c.line(50, 725, 550, 725)
    
    y = 700
    c.drawString(50, y, f"Total Ingresos: ${ingresos:,.2f}")
    y -= 20
    c.drawString(50, y, f"Total Egresos: ${egresos:,.2f}")
    y -= 20
    c.drawString(50, y, f"Balance: ${balance:,.2f}")
    y -= 40
    c.drawString(50, y, "Detalle:")
    y -= 20
    
    datos_pdf = df_filtrado if not df_filtrado.empty else df_trans
    for idx, row in datos_pdf.head(20).iterrows():
        if y < 100:
            c.showPage()
            y = 750
        c.drawString(60, y, f"{str(row['fecha'])[:10]} | {row['tipo']} | {row['categoria']} | ${row['monto']:,.2f}")
        y -= 18
        
    c.save()
    st.download_button(
        label="📄 Descargar Reporte PDF Oficial",
        data=pdf_buffer.getvalue(),
        file_name="reporte_financiero_escuela.pdf",
        mime="application/pdf",
        use_container_width=True
    )
