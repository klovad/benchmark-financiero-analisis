# Acceso a los datos

Este repo lee el data mart con un rol de **solo lectura**: ve únicamente `marts.*` (no
`staging` ni `meta`) y sus sesiones arrancan en `read_only`, así que ningún notebook puede
modificar datos.

## Crear el rol (una vez por servidor)

Lo crea el repo del ETL (`benchmark-bancos`), como superusuario de Postgres. Desde la
carpeta de ese repo, en PowerShell:

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -h localhost -p 5432 -U postgres -d postgres -v ON_ERROR_STOP=1 -v app_db=benchmark_cartera_depositos -f sql/admin/rol_lectura.sql
```

Pide primero la contraseña de `postgres` y después la que quieras para el nuevo rol
`analista`. Crea también el grupo `marts_lectura`, que es el que tiene los permisos (la
migración `sql/42` del ETL los mantiene para tablas futuras). Detalle en
`benchmark-bancos/docs/despliegue_y_orquestacion.md` §3.4.

Cambiar la contraseña más adelante (como `postgres`):

```sql
ALTER ROLE analista PASSWORD 'nueva';
```

## Configurar este repo

```powershell
Copy-Item .env.example .env   # y completar POSTGRES_PASSWORD con la del rol analista
uv sync
uv run python -c "from benchmark_analisis import consulta; print(consulta('select current_user, count(*) from marts.dim_entidad group by 1'))"
```

Debe imprimir `analista` y 444 entidades.

## Si algo falla

| Síntoma | Causa | Qué hacer |
|---|---|---|
| `password authentication failed for user "analista"` | contraseña del `.env` distinta | corregir `.env` o `ALTER ROLE` |
| `role "analista" does not exist` | no se corrió `rol_lectura.sql` en este servidor | correrlo (arriba) |
| `permission denied for schema marts` / `for table ...` | el grupo existe pero faltan permisos (tabla nueva antes de `sql/42`) | en el ETL: `uv run benchmark-bancos migrate`, o volver a correr `rol_lectura.sql` |
| `cannot execute ... in a read-only transaction` | se intentó escribir | esperado: este repo no escribe en la base. Guardar resultados en `salidas/` o `data/` |
