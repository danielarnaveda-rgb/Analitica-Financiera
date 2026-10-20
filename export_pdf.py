import sqlite3
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime

def generar_reporte_pdf(nombre_archivo="reporte_financiero_oficial.pdf"):
    conn = sqlite3.connect('finanzas.db')
    cursor = conn.cursor()
    cursor.execute("SELECT tipo, SUM(monto) FROM transacciones GROUP BY tipo")
    totales = cursor.fetchall()
    
    cursor.execute("SELECT fecha, tipo, categoria, monto, descripcion FROM transacciones ORDER BY fecha DESC LIMIT 15")
    movimientos = cursor.fetchall()
    conn.close()

    c = canvas.Canvas(nombre_archivo, pagesize=letter)
    c.drawString(50, 750, "INFORME DE GESTIÓN FINANCIERA")
    c.drawString(50, 735, f"Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    c.line(50, 725, 550, 725)
    
    y = 700
    c.drawString(50, y, "Resumen de Totales:")
    y -= 20
    for tipo, suma in totales:
        c.drawString(70, y, f"- {tipo}: ${suma:,.2f}")
        y -= 18
        
    y -= 20
    c.drawString(50, y, "Últimos Movimientos:")
    y -= 20
    
    for fecha, tipo, cat, monto, desc in movimientos:
        if y < 100:
            c.showPage()
            y = 750
        c.drawString(70, y, f"{fecha} | {tipo} | {cat} | ${monto:,.2f} | {desc}")
        y -= 15
        
    c.save()