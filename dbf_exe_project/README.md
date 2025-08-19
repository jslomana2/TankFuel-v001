# dbf_exe_project (Flask + DBF)

- `/api/tanques_norm` (FFTANQ.DBF): tanque_id = ALMACEN-CODIGO, DESCRI, CAPACIDAD, STOCK, STOCK15, ARTICULO, ALMACEN, TEMPULT; nombre/color desde FFARTI.
- `/api/calibraciones/ultimas?tanque_id=ALM-COD&n=10` (FFCALA.DBF): filtra por ALMACEN/TANQUES, orden FECHA+HORA, `last_ts`.
- Aliases: `/api/calados/ultimas`, `/api/lecturas/ultimas`, `/api/stream/calibraciones`.
- Debug: `/api/where`, `/debug/static`.

## Ejecución con .exe
Coloca junto al exe: FFALMA.DBF, FFARTI.DBF, FFTANQ.DBF, FFCALA.DBF y `templates/` + `static/`.
