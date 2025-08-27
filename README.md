# PROCONSI – Tanques (Vista avanzada) — Estado por porcentaje

Este paquete parte del **ZIP funcional** que nos enviaste y añade una mejora:
el **estado junto al nombre del tanque** (círculo + texto) ahora se calcula por **porcentaje de llenado**:

- **Alto** (círculo verde) cuando **> 70%**
- **Medio** (círculo amarillo) cuando **21% – 69%**
- **Bajo** (círculo rojo) cuando **≤ 20%**

## Qué he modificado

1. `sondastanques_mod.js`  
   - Eliminado el uso de `t.status` para el chip del estado visual.
   - Añadida lógica local: calcula el % (si no existe `pct`), decide el nivel y aplica **color** y **texto** dinámicos.
2. `sondastanques_mod.html`  
   - Leyenda del pie actualizada a **Alto / Medio / Bajo**.
   - Añadido **cache-busting** al script: `sondastanques_mod.js?v=20250827-4` para forzar recarga del navegador.

> ⚠️ No se han tocado ni estructura ni estilos fuera de lo anterior. El resto del proyecto queda **tal cual**.

## Cómo desplegar

1. Copia los archivos de este ZIP **encima** de tu proyecto actual (respeta rutas/estructura).
2. Abre la vista en el navegador y fuerza recarga: **Ctrl + F5** (o vacía caché).
3. Comprueba en DevTools (F12 → Elements/Sources) que el `<script>` carga con `?v=20250827-4`.

## Verificación rápida

- Localiza una tarjeta con % alto/bajo y verifica que el **texto** y el **círculo** cambian entre **Alto / Medio / Bajo** según el %.
- La leyenda del pie debe mostrar **Alto, Medio, Bajo, Agua**.

## Notas

- Si en el futuro quieres volver a usar estados ajenos al % (por ejemplo, alarmas de sensor), podemos combinar ambos
  (p.ej., mostrar un **icono extra** o un **borde** de tarjeta) sin perder esta lectura por porcentaje.