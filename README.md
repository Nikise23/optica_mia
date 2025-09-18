# 🧿 ÓpticaApp

Sistema web completo para gestión integral de ópticas: productos, pacientes, médicos, recetas, caja con pagos parciales, gastos, reportes diarios/mensuales y dashboard con métricas en tiempo real.

## 🚀 Tecnologías

- **Backend**: Flask (3.x) + SQLAlchemy (2.x) + Flask-SQLAlchemy
- **Base de datos**: SQLite
- **Frontend**: Jinja2 + Bootstrap 5 + Chart.js
- **ORM**: SQLAlchemy

## 📦 Funcionalidades principales

### 🏥 Gestión de Entidades
- **Productos**: CRUD completo con control de stock y alertas de bajo stock
- **Pacientes**: CRUD completo con información de contacto y obra social
- **Médicos**: CRUD completo con comisiones configurables por porcentaje
- **Recetas**: Vinculadas a paciente y médico (opcional), con armazón que descuenta stock automáticamente

### 💰 Sistema de Caja Avanzado
- **Pagos parciales**: Sistema de señas con descuentos en porcentaje
- **Apertura automática**: La caja se abre automáticamente cada día al acceder
- **Cierre manual**: Control total sobre el cierre diario de caja
- **Múltiples métodos**: Efectivo, tarjeta, transferencia
- **Exportación CSV**: Descarga de reportes diarios con todos los detalles

### 📊 Reportes y Análisis
- **Reporte Diario**: Análisis completo de cualquier día específico
- **Reporte Mensual**: Selector de mes/año para revisar historial completo
- **Dashboard en tiempo real**: KPIs, saldo mensual, gráficos de evolución
- **Comisiones médicas**: Cálculo automático sobre montos netos cobrados

### 💸 Gestión de Gastos
- **Registro de gastos**: Categorización y descripción detallada
- **Control de caja**: Solo se pueden registrar gastos con caja abierta
- **Reportes integrados**: Gastos incluidos en reportes diarios y mensuales

## 🗂️ Estructura del proyecto

```
optica_mia/
├── app.py                    # Aplicación Flask principal
├── config.py                 # Configuración de la aplicación
├── models/
│   └── models.py            # Modelos de base de datos (SQLAlchemy)
├── templates/
│   ├── base.html            # Template base con navbar y footer
│   ├── dashboard.html       # Dashboard principal con KPIs
│   ├── productos.html / producto_form.html
│   ├── pacientes.html / paciente_form.html
│   ├── medicos.html / medico_form.html
│   ├── recetas.html / receta_form.html
│   ├── caja.html / pago_form.html / cierre_form.html
│   ├── gastos.html / gasto_form.html
│   ├── reporte_diario.html  # Reporte detallado por día
│   └── reporte_mensual.html # Reporte detallado por mes
├── static/
│   ├── styles.css           # Estilos personalizados
│   ├── logo.png             # Logo de la óptica
│   ├── favicon.png          # Favicon PNG
│   └── favicon.ico          # Favicon ICO
├── tools/
│   └── make_favicon.py      # Script para generar favicons
├── seeds.sql                # Datos de ejemplo
├── requirements.txt         # Dependencias Python
├── run_optica_mia.bat      # Script de inicio rápido
└── README.md               # Este archivo
```

## 🔧 Configuración y ejecución

### 🚀 Inicio rápido (Windows)
**Doble clic en `run_optica_mia.bat`** - El script se encarga de todo automáticamente.

### 📋 Instalación manual

1) **Crear entorno virtual e instalar dependencias**
```bash
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) **Variables de entorno (opcional)**
```bash
SECRET_KEY=tu-clave-secreta
DATABASE_URL=sqlite:///optica.db
FLASK_ENV=development
```

3) **Ejecutar la aplicación**
```bash
set FLASK_APP=app.py
flask run
```

4) **Datos de ejemplo (opcional)**
```bash
sqlite3 optica.db ".read seeds.sql"
```

### 🌐 Acceso
- **URL**: http://localhost:5000
- **Usuario**: No requiere autenticación (desarrollo)

## 💳 Flujo de pagos con descuento

### 📝 Proceso completo:
1. **Crear receta** con total (ej. $165,000)
2. **Caja → Nuevo pago**: aplicar descuento en % (ej. 20%) → total pasa a $132,000
3. **Elegir tipo de pago**:
   - **Total**: autocompleta y bloquea el monto con el restante neto
   - **Parcial**: monto editable; valida no exceder el saldo restante
4. **Control automático**: Cuando el saldo llega a 0, la receta desaparece del selector
5. **Comisiones**: Se calculan automáticamente sobre pagos netos cobrados

### 🔄 Gestión de caja:
- **Apertura automática**: Al acceder a `/caja` se abre automáticamente si no existe cierre para hoy
- **Cierre manual**: Control total sobre cuándo cerrar la caja
- **Reapertura**: Posibilidad de reabrir la caja si es necesario
- **Bloqueo de transacciones**: No se pueden registrar pagos/gastos con caja cerrada

## 📊 Reportes disponibles

### 📅 Reporte Diario
- **URL**: `/reporte-diario?fecha=AAAA-MM-DD`
- **Funcionalidades**:
  - Análisis completo de cualquier día específico
  - Resumen por método de pago
  - Detalle de recetas con descuentos aplicados
  - Gastos del día
  - Cierre de caja (si existe)
  - Función de impresión

### 📆 Reporte Mensual
- **URL**: `/reporte-mensual?mes=X&año=YYYY`
- **Funcionalidades**:
  - Selector de mes y año (historial completo)
  - Resumen ejecutivo con KPIs
  - Detalle de recetas del mes
  - Gastos del mes
  - Comisiones por médico
  - Función de impresión

### 📤 Exportación CSV
- **Endpoint**: `/caja/cierre/csv?fecha=AAAA-MM-DD`
- **Incluye**: Pagos (método, monto) y gastos del día
- **Uso**: Descarga directa para análisis externo

## 🖼️ Recursos estáticos

### 📁 Carpeta `static/`
- **`styles.css`**: Estilos personalizados (puede estar vacío)
- **`logo.png`**: Logo de la óptica (aparece en navbar)
- **`favicon.png/ico`**: Favicon del navegador
- **Generación**: Usar `tools/make_favicon.py` para crear favicons desde logo

### 🎨 Personalización
- Podés reemplazar `logo.png` con tu propio logo
- El favicon se actualiza automáticamente
- Footer personalizable con tu nombre/empresa

## 🔧 Características técnicas

### 🗄️ Base de datos
- **SQLite**: Base de datos local, no requiere servidor
- **Migraciones automáticas**: Se agregan columnas nuevas automáticamente
- **Eliminación en cascada**: Eliminar entidades elimina registros relacionados
- **Integridad referencial**: Control automático de relaciones

### 🚀 Rendimiento
- **Consultas optimizadas**: Uso de `joinedload` para evitar N+1 queries
- **Índices automáticos**: SQLAlchemy crea índices en claves foráneas
- **Caché de sesión**: Reutilización de conexiones de base de datos

## 📝 Notas de desarrollo

- **Entorno**: Configurado para desarrollo (sin autenticación)
- **Logs**: Errores se muestran en consola y flash messages
- **Backup**: Hacer backup regular de `optica.db`
- **Actualizaciones**: Reiniciar app después de cambios en modelos
