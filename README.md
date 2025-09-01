# PROCONSI · TankFuel v001

Demo avanzada de monitorización de tanques (Fuelsoft → Web Flask).  
Proyecto preparado para empaquetar en **EXE Windows** con **PyInstaller** y distribución vía **GitHub Actions**.

---

## 🚀 Características principales

- **Flask backend** con APIs ultra-rápidas para datos de tanques.
- **Lectura directa de DBF** (`FFALMA`, `FFARTI`, `FFTANQ`, `FFCALA`).
- **UI avanzada** en HTML + JS + CSS (`templates/sondastanques_mod.html`).
- **Dashboard de tanques** con:
  - Colores propios por producto (Gasóleo A/B/C, AdBlue, Gasolina, etc.).
  - Estado dinámico según % de llenado (⚠ Bajo, Medio, Alto, Top).
  - Selector de almacenes (multi-sede).
  - Auto-refresco en tiempo real.
- **Caché persistente** → arranques casi instantáneos si DBFs no cambian.

---

## 📂 Estructura del proyecto

```
dbf_exe_project/
│── app.py                   # Servidor Flask (backend)
│── requirements.txt         # Dependencias Python
│── static/
│   ├── sondastanques_mod.css
│   └── sondastanques_mod.js
│── templates/
│   └── sondastanques_mod.html
│── README.md
```

---

## ⚙️ Instalación y uso

1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

2. Ejecutar en local:
   ```bash
   python app.py
   ```
   → Servidor en `http://127.0.0.1:5000`

3. Para compilar EXE (Windows):
   ```bash
   pyinstaller --onefile app.py
   ```

---

## 🔗 Endpoints disponibles

- `GET /api/almacenes` → Lista de almacenes + tanques + últimas lecturas.
- `GET /api/tanque_historico?almacen=&tanque=` → Histórico de un tanque.
- `GET /api/status` → Estado de refresco (usado en autorefresco UI).

> **Nota**: Los DBF (`FFALMA`, `FFARTI`, `FFTANQ`, `FFCALA`) deben estar en la **misma carpeta que el EXE**.

---

## 🆕 Mejoras recientes

- ✅ **Fix**: Los tanques ya no desaparecen si no tienen calado reciente → se muestran con 0 L.  
- ✅ **Fix**: Colores por producto normalizados (`#RRGGBB`, valores numéricos o con espacios).  
- ✅ **Fix**: Alineado del círculo/⚠ en el status.  
- ⚡ **Optimizaciones**:  
  - Preload ultra-rápido de FFCALA (últimas lecturas).  
  - Caché persistente en disco → arranques instantáneos si los DBF no cambian.

---

## 👨‍💻 Autor

Proyecto interno **PROCONSI Fuelsoft** · Técnico: Javier Delgado Llamas.

---
