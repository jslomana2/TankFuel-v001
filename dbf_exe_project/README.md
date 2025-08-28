
# PROCONSI – SondaTanques (HEADER_WHITE baseline)

Estructura:
```
dbf_exe_project/
  app.py
  requirements.txt
  templates/sondastanques_mod.html
  static/sondastanques_mod.css
  static/sondastanques_mod.js
  .github/workflows/build-windows-exe.yml
```

Notas:
- El **texto del estado** ahora cambia con el % junto al **icono/bola** (<=20% ⚠ "Bajo", 21-50 "Medio", 51-90 "Alto", 91-100 "Muy alto").
- Los endpoints están stub: con tu backend real seguirán funcionando. El HTML/JS es la parte corregida.
- Si compilas en GitHub Actions, coloca los DBF junto al EXE fuera del repo como haces normalmente.
