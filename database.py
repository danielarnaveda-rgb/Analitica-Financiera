import sqlite3
from datetime import datetime, timedelta
import random

def init_db():
    conn = sqlite3.connect('finanzas.db')
    cursor = conn.cursor()
    
    # Tabla de Cuentas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cuentas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            tipo TEXT NOT NULL,
            saldo REAL NOT NULL
        )
    ''')
    
    # Tabla de Transacciones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transacciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cuenta_id INTEGER,
            categoria TEXT NOT NULL,
            monto REAL NOT NULL,
            tipo TEXT NOT NULL,
            fecha DATE NOT NULL,
            descripcion TEXT,
            FOREIGN KEY (cuenta_id) REFERENCES cuentas (id)
        )
    ''')
    
    # Cargar datos de prueba si la base está vacía
    cursor.execute("SELECT COUNT(*) FROM cuentas")
    if cursor.fetchone()[0] == 0:
        cursor.executemany('''
            INSERT INTO cuentas (nombre, tipo, saldo) VALUES (?, ?, ?)
        ''', [
            ('Banco Principal', 'Banco', 1500000.0),
            ('Mercado Pago', 'Billetera Virtual', 350000.0),
            ('Caja Chica', 'Efectivo', 80000.0)
        ])
        
        # Insertar movimientos ficticios de los últimos 30 días
        categorias_egresos = ['Insumos', 'Servicios', 'Sueldos', 'Mantenimiento', 'Impuestos']
        categorias_ingresos = ['Ventas', 'Cobro Servicios', 'Rendimientos']
        
        hoy = datetime.now()
        for i in range(40):
            dias_atras = random.randint(0, 30)
            fecha = (hoy - timedelta(days=dias_atras)).strftime('%Y-%m-%d')
            tipo = random.choice(['Ingreso', 'Egreso', 'Egreso']) # Más egresos para realismo
            
            if tipo == 'Ingreso':
                cat = random.choice(categorias_ingresos)
                monto = round(random.uniform(50000, 300000), 2)
            else:
                cat = random.choice(categorias_egresos)
                monto = round(random.uniform(10000, 120000), 2)
                
            cursor.execute('''
                INSERT INTO transacciones (cuenta_id, categoria, monto, tipo, fecha, descripcion)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (random.randint(1, 3), cat, monto, tipo, fecha, f'Movimiento automático {i+1}'))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("¡Base de datos finanzas.db inicializada con éxito en Linux!")