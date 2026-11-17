#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis de E3 (eficiencia en la preparación de reportes, hipótesis H1).

Entrada : e3_tiempos.csv  con las columnas
          participante, grupo, orden, condicion (manual|modelo), periodo, reporte, minutos, correcto_1_0, observaciones
          (rellene 'minutos' con el tiempo real cronometrado de cada reporte y 'correcto_1_0' con 1 si el
           reporte coincide con respuestas_correctas_*.csv y 0 si no).
Salida  : e3_resultados.txt  (copie y pegue su contenido para pasárselo a Claude)

Uso:  python e3_analisis.py e3/e3_tiempos.csv
"""
import sys, itertools
import numpy as np
import pandas as pd

ruta = sys.argv[1] if len(sys.argv) > 1 else 'e3_tiempos.csv'
df = pd.read_csv(ruta)
df['minutos'] = pd.to_numeric(df['minutos'], errors='coerce')
df = df.dropna(subset=['minutos'])
if df.empty:
    sys.exit('El archivo no tiene tiempos (columna "minutos" vacía).')

L = ['=== RESULTADOS E3 ===']
# 1) Tiempo medio por reporte (lo que pide el paper)
por_rep = df.groupby('condicion').minutos.agg(['count', 'mean', 'std'])
L.append('Tiempo por reporte (min):\n' + por_rep.round(2).to_string())
m_man, m_mod = por_rep.loc['manual', 'mean'], por_rep.loc['modelo', 'mean']
L.append(f'Reducción del tiempo medio por reporte = {100 * (1 - m_mod / m_man):.1f} %  ({m_man:.2f} -> {m_mod:.2f} min)')

# 2) Análisis pareado por participante (suma de sus reportes en cada condición)
t = df.pivot_table(index='participante', columns='condicion', values='minutos', aggfunc='sum').dropna()
n = len(t)
L.append(f'\nParticipantes con ambas condiciones: n = {n}')
if n >= 2:
    d = (t['manual'] - t['modelo']).values
    red_ind = 100 * (1 - t['modelo'] / t['manual'])
    L.append(f'Reducción individual media = {red_ind.mean():.1f} %  (min {red_ind.min():.1f} %, max {red_ind.max():.1f} %)')
    rng = np.random.default_rng(1)
    boots = []
    for _ in range(10000):
        idx = rng.integers(0, n, n)
        boots.append(100 * (1 - t['modelo'].values[idx].sum() / t['manual'].values[idx].sum()))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    L.append(f'IC 95 % (bootstrap) de la reducción global = [{lo:.1f} %, {hi:.1f} %]')
    # prueba de permutación de signos (exacta si n <= 20)
    obs = d.mean()
    if n <= 20:
        signos = np.array(list(itertools.product([-1, 1], repeat=n)))
        medias = (signos * d).mean(axis=1)
    else:
        signos = rng.choice([-1, 1], size=(200000, n))
        medias = (signos * d).mean(axis=1)
    p1 = float((medias >= obs - 1e-12).mean())
    p2 = float((np.abs(medias) >= abs(obs) - 1e-12).mean())
    L.append(f'Prueba de permutación de signos (pareada): p una cola = {p1:.4f} | p dos colas = {p2:.4f}')
    L.append(f'(con n={n} el menor p posible a dos colas es {2 / 2 ** n:.4f})')
    dz = d.mean() / d.std(ddof=1) if d.std(ddof=1) > 0 else float('nan')
    L.append(f"Tamaño del efecto (d de Cohen pareado) = {dz:.2f}")
    meta = 30
    L.append(f'H1 (reducción >= {meta} %): ' + ('SE CONFIRMA' if lo >= meta else
             'NO SE CONFIRMA con certeza (el IC incluye valores < 30 %)' if red_ind.mean() >= meta else 'NO SE CONFIRMA'))
    L.append('Orden/periodo (control del diseño cruzado): ' + str(
        df.groupby(['condicion', 'periodo']).minutos.mean().round(2).to_dict()))

# 3) Corrección de los reportes
if 'correcto_1_0' in df and df['correcto_1_0'].notna().any():
    cor = pd.to_numeric(df['correcto_1_0'], errors='coerce')
    L.append('\n% de reportes correctos por condición:\n' + (cor.groupby(df['condicion']).mean() * 100).round(1).to_string())

txt = '\n'.join(L)
print(txt)
open('e3_resultados.txt', 'w', encoding='utf-8').write(txt)
