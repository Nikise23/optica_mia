# 🧿 ÓpticaApp

Sistema web local para gestión integral de ópticas. Permite administrar productos, pacientes, médicos, recetas, ventas y caja, con métricas en tiempo real.

## 🚀 Tecnologías

- **Backend**: Flask + SQLAlchemy
- **Base de datos**: SQLite
- **Frontend**: HTML + Bootstrap
- **ORM**: SQLAlchemy

## 📦 Funcionalidades

- CRUD de productos con alertas de bajo stock.
- Gestión de pacientes y médicos con comisiones.
- Recetario vinculado a pacientes y médicos.
- Registro automático de ventas al cargar receta.
- Caja con métodos de pago y cierres diarios/mensuales.
- Dashboard con métricas clave y ranking de médicos.

## 📁 Estructura
optica_app/ 
├── app.py 
├── config.py 
├── models/    
    └── models.py │
├── templates/ │   
    ├── base.html │   
    ├── dashboard.html │   
    ├── productos.html │   
    ├── pacientes.html │   
    ├── medicos.html │   
    ├── recetas.html │   
    ├── caja.html │   
    └── cierres.html │
├── static/ │   
    └── styles.css 
├── seeds.sql 
├── requirements.txt 
└── README.md
