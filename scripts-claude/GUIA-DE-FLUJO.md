# Simulación de la sección IV — guía paso a paso

Archivos: `sim_solicitudes.py` (todo E1, E2 y preparación de E3), `e3_analisis.py`, `requirements.txt`.

## Paso 1. Preparar el entorno (15 min)
1. Instala Python 3.10+ y Docker Desktop.
2. En la carpeta de los archivos:  `pip install -r requirements.txt`
3. Levanta PostgreSQL limitado a 2 CPU / 4 GB (lo que dice tu paper):
   `docker run -d --name pg-solicitudes --cpus=2 --memory=4g -e POSTGRES_PASSWORD=clave123 -p 5433:5433 postgres:16`
   (si tu máquina es Windows/Mac y no tienes Docker, instala PostgreSQL normal y usa `--reinicio` con el comando que lo reinicie)

## Paso 2. Ejecutar E1 (≈1 min)  ← hazlo primero
`python sim_solicitudes.py --password clave123 --sin-e2`
Genera la carpeta `resultados/`. **Pégame el contenido de `resultados/resumen_para_paper.txt`.**

## Paso 3. Ejecutar E2 (30–60 min, déjalo corriendo)
`python sim_solicitudes.py --password clave123`
Cada repetición "en frío" reinicia el contenedor. Si te falta tiempo: `--reps-fria 10 --escalas 1,10` (y lo declaras en el paper).
Pégame de nuevo `resumen_para_paper.txt` (ya incluye E2 y el entorno).

## Paso 4. E3 con personas (lo que más tarda: consíguelas ya)
Mínimo 6 participantes (ideal 8). Todo está en `resultados/e3/`:
- `base_manual_periodo_A.xlsx` y `_B.xlsx`: el "antes" (3 fuentes sueltas + instrucciones). El participante hace R1 y R2 en Excel y tú cronometras.
- "Después": instala Metabase (`docker run -d -p 3000:3000 --name metabase metabase/metabase`), conéctalo a PostgreSQL (host `host.docker.internal`, esquema `sim_x1`), y crea 4 preguntas SQL con las consultas de `reportes_modelo.sql`. El participante solo abre la pregunta y exporta. Alternativa rápida: pgAdmin con las consultas ya guardadas.
- `e3_tiempos.csv`: ya viene con el diseño cruzado (G1: manual→A, luego modelo→B; G2: modelo→A, luego manual→B). Rellena `minutos` y `correcto_1_0` (compara con `respuestas_correctas_*.csv`).
- Ejecuta: `python e3_analisis.py resultados/e3/e3_tiempos.csv` y **pégame `e3_resultados.txt`**.
Si no consigues personas, avísame y reformulamos H1 de forma honesta (no inventes tiempos).

## Qué va en el paper (te lo completo yo cuando me pases los resultados)
| Placeholder del paper | Sale de |
|---|---|
| [versión], entorno | `entorno.txt` |
| [N], [x], [y], [z] | E1 (N, descartados, fusionados, únicas) |
| exactitud, completitud | E1 |
| tiempos de caché fría/caliente | E2 |
| min manual → modelo, % | E3 |
| [URL del repositorio] | sube estos archivos a GitHub |

## Parámetros
Todo el ruido y los supuestos están al inicio de `sim_solicitudes.py`. Decláralos en la subsección *Datos*. **No los ajustes después de ver resultados para que salgan mejor.**
