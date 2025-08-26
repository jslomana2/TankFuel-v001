# PROCONSI – SondaTanques (Flask + DBF)

**Reglas**:
- volumen = última no nula de FFCALA.LITROS (dentro de las últimas 5).
- litros15 = última no nula de FFCALA.LITROS15 (dentro de las últimas 5).
- temperatura = última no nula de FFCALA.TEMPERA (dentro de las últimas 5).
- Si no hay lecturas válidas, **NO se muestra el tanque** (sin fallback a FFTANQ).

Coloca FFCALA.DBF, FFTANQ.DBF, FFALMA.DBF, FFARTI.DBF junto a app.py (o junto al EXE).
