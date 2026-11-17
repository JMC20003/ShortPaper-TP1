#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulación del modelo dimensional de solicitudes académicas (Short paper, sección IV).

Hace, en orden:
  1. Genera datos SINTÉTICOS: una "verdad" (cada solicitud con sus 4 hitos) y la proyecta a
     3 fuentes con ruido controlado (duplicados, fechas/estados/tipos mal escritos, faltantes,
     desfases de actualización). Genera extracciones diarias (carga diaria).
  2. Ejecuta el ETL con las 4 reglas del paper (limpieza, estandarización, deduplicación,
     seudonimización) y carga el esquema estrella en PostgreSQL.
  3. E1: compara los 8 KPI calculados con SQL contra un oráculo independiente (pandas/numpy
     sobre la verdad) y mide duplicados, completitud y exactitud de hitos.
  4. E2: mide el tiempo de respuesta de las consultas de KPI (30 repeticiones, caché fría/caliente).
  5. Prepara el paquete de E3 (Excel de la línea base manual, SQL del "después", plantilla de tiempos).

Uso típico:   python sim_solicitudes.py --db postgres --password TU_CLAVE
"""
import argparse, os, sys, json, time, hmac, hashlib, subprocess, unicodedata, difflib, random, io, re, platform
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from functools import lru_cache
import numpy as np
import pandas as pd

# =====================================================================================
# 1. PARÁMETROS DEL ESCENARIO  (todo lo que está aquí debe declararse en la sección "Datos")
# =====================================================================================
SEED = 2026
INICIO, FIN = date(2025, 3, 3), date(2025, 12, 31)          # periodo simulado
FERIADOS = ['2025-04-17', '2025-04-18', '2025-05-01', '2025-06-07', '2025-06-29', '2025-07-23',
            '2025-07-28', '2025-07-29', '2025-08-06', '2025-08-30', '2025-10-08', '2025-10-31',
            '2025-11-01', '2025-12-08', '2025-12-09', '2025-12-25']   # calendario simulado (aprox.)
FER = np.array(FERIADOS, dtype='datetime64[D]')

AREAS = ['Registros Académicos', 'Secretaría Académica', 'Coordinación Académica', 'Atención al Estudiante']
# tipo: nombre, SLA (días hábiles), área habitual, mediana del tiempo en proceso, peso en el volumen
TIPOS = {
    'CONST': dict(nombre='Constancia de estudios', sla=3, area=0, med=1.5, peso=0.30),
    'CERT': dict(nombre='Certificado de estudios', sla=10, area=1, med=6.0, peso=0.20,
                 sla_nuevo=7, desde=date(2025, 7, 1)),            # cambio de SLA a mitad del periodo (prueba del SCD tipo 2)
    'RECT': dict(nombre='Rectificación de matrícula', sla=5, area=0, med=2.5, peso=0.20),
    'CONV': dict(nombre='Convalidación', sla=15, area=2, med=9.0, peso=0.10),
    'RECL': dict(nombre='Reclamo', sla=10, area=3, med=5.0, peso=0.20),
}
PROB_FUENTE = {'A': 0.75, 'B': 0.45, 'C': 0.60}                # prob. de que una solicitud aparezca en cada fuente
PROB_REASIGNADA = 0.12                                          # solicitudes cuya área final no es la habitual
PROB_GEMELAS = 0.005                                            # solicitudes DISTINTAS con misma clave natural
RUIDO = dict(
    est_vacio={'A': 0.005, 'B': 0.02, 'C': 0.03},               # código de estudiante faltante
    fecha_vacia={'A': 0.0, 'B': 0.01, 'C': 0.02},               # fecha de registro faltante
    B_reg_mas1=0.05,                                            # mesa de partes sella la fecha 1 día después
    typo=0.02,                                                  # error tipográfico en el tipo de trámite (B y C)
    C_fecha_aten=0.55,                                          # la hoja de área escribe la fecha de atención
    lag_p0={'B': 0.85, 'C': 0.70},                              # prob. de actualizar el estado el mismo día (si no, +1 día)
)
HMAC_CLAVE = b'clave-secreta-de-la-simulacion'                  # en producción: fuera de la base de datos

# Variantes de texto que escriben las fuentes
VAR_TIPO = {
    'CONST': ['constancia de estudios', 'Constancia de Estudios', 'const. de estudios', 'constancia estudios', 'CONSTANCIA DE ESTUDIOS'],
    'CERT': ['certificado de estudios', 'Certificado de Estudios', 'certif. de estudios', 'certificado estudios'],
    'RECT': ['rectificacion de matricula', 'Rectificación de matrícula', 'rectif. matricula', 'RECTIFICACION MATRICULA'],
    'CONV': ['convalidacion', 'Convalidación', 'convalidación de cursos', 'CONVALIDACION'],
    'RECL': ['reclamo', 'Reclamo', 'reclamo academico', 'Reclamo académico', 'RECLAMO'],
}
VAR_ESTADO = {
    'A': {1: ['REGISTRADA'], 2: ['ASIGNADA'], 3: ['ATENDIDA'], 4: ['CERRADA']},
    'B': {1: ['Recibido', 'recibido'], 2: ['Derivado', 'derivado a area']},
    'C': {2: ['asignado', 'En proceso', 'EN PROCESO', 'asignada'], 3: ['atendido', 'Atendida', 'listo', 'ATENDIDO'],
          4: ['cerrado', 'Cerrada', 'archivado']},
}
VAR_AREA = {0: ['registros academicos', 'Registros Académicos', 'REGISTROS', 'registro academico'],
            1: ['secretaria academica', 'Secretaría Académica', 'SECRETARIA'],
            2: ['coordinacion academica', 'Coordinación Académica', 'COORDINACION'],
            3: ['atencion al estudiante', 'Atención al Estudiante', 'ATENCION']}
FMT_FECHA = {'iso': '%Y-%m-%d', 'dmy': '%d/%m/%Y', 'dmy2': '%d-%m-%y', 'dmy3': '%d/%m/%y'}
ESTADO_NOM = {1: 'Registrada', 2: 'Asignada', 3: 'Atendida', 4: 'Cerrada'}
# E3: solicitudes registradas en una semana; la información se corta 14 días después (reporte de seguimiento)
PERIODOS_E3 = [('A', date(2025, 9, 15), date(2025, 9, 21)), ('B', date(2025, 10, 13), date(2025, 10, 19))]
CORTE_E3_DIAS = 14


# =====================================================================================
# 2. UTILIDADES DE CALENDARIO
# =====================================================================================
def d_hab(x, y):
    """d(x,y): días hábiles en el intervalo (x, y]  (misma definición que nro_habil(y) - nro_habil(x))."""
    uno = np.timedelta64(1, 'D')
    return np.busday_count(x + uno, y + uno, holidays=FER)


def clave_fecha(a):
    s = pd.to_datetime(pd.Series(a))
    return (s.dt.year * 10000 + s.dt.month * 100 + s.dt.day).astype('Int64')


def ym(a):
    m = a.astype('datetime64[M]').astype(int)
    return (1970 + m // 12) * 100 + (m % 12 + 1)


def construir_dims():
    dias = pd.date_range(INICIO, FIN)
    d64 = dias.values.astype('datetime64[D]')
    hab = np.is_busday(d64, holidays=FER)
    nro = np.cumsum(hab)
    dim_fecha = pd.DataFrame({
        'sk_fecha': clave_fecha(d64).values, 'fecha': dias.strftime('%Y-%m-%d'),
        'anio': dias.year.values, 'mes': dias.month.values, 'anio_mes': (dias.year * 100 + dias.month).values,
        'dia_semana': (dias.dayofweek + 1).values, 'es_habil': hab.astype(int), 'nro_habil': nro})
    nro_d = dict(zip(dias.date, nro.tolist()))
    tipos, sk = [], 1
    base_sk = {}
    for cod, t in TIPOS.items():
        base_sk[cod] = sk
        if 'sla_nuevo' in t:
            tipos.append((sk, cod, t['nombre'], t['sla'], INICIO.isoformat(), (t['desde'] - timedelta(days=1)).isoformat(), 0))
            tipos.append((sk + 1, cod, t['nombre'], t['sla_nuevo'], t['desde'].isoformat(), '9999-12-31', 1))
            sk += 2
        else:
            tipos.append((sk, cod, t['nombre'], t['sla'], INICIO.isoformat(), '9999-12-31', 1))
            sk += 1
    dim_tipo = pd.DataFrame(tipos, columns=['sk_tipo', 'cod_tipo', 'nombre_tipo', 'sla_dias', 'vigente_desde', 'vigente_hasta', 'es_vigente'])
    dim_estado = pd.DataFrame({'sk_estado': [1, 2, 3, 4], 'cod_estado': [1, 2, 3, 4],
                               'nombre_estado': [ESTADO_NOM[k] for k in (1, 2, 3, 4)], 'es_final': [0, 0, 1, 1]})
    dim_area = pd.DataFrame({'sk_area': range(1, 5), 'nombre_area': AREAS})
    return dict(fecha=dim_fecha, tipo=dim_tipo, estado=dim_estado, area=dim_area, nro=nro_d, base_sk=base_sk)


def sk_tipo_de(cod, reg_date, base_sk):
    t = TIPOS[cod]
    if 'sla_nuevo' in t and reg_date >= t['desde']:
        return base_sk[cod] + 1
    return base_sk[cod]


# =====================================================================================
# 3. GENERADOR DE LA "VERDAD"  (vectorizado: sirve para 20 mil y para 2 millones de solicitudes)
# =====================================================================================
def generar_verdad(n, rng):
    cods = list(TIPOS)
    dias = pd.date_range(INICIO, FIN).values.astype('datetime64[D]')
    w = np.where(np.is_busday(dias, holidays=FER), 1.0, 0.12)
    mes = dias.astype('datetime64[M]').astype(int) % 12 + 1
    w = w * np.where(np.isin(mes, [3, 8]), 1.6, 1.0)             # picos de inicio de semestre
    w = w / w.sum()
    reg = dias[rng.choice(len(dias), size=n, p=w)]
    tipo_i = rng.choice(len(cods), size=n, p=np.array([TIPOS[c]['peso'] for c in cods]))
    n_est = max(100, n // 3)
    est = rng.integers(0, n_est, size=n)
    # solicitudes gemelas: distintas pero con la misma clave natural (estudiante, tipo, fecha de registro)
    m = int(PROB_GEMELAS * n)
    gem = np.zeros(n, dtype=bool)
    if m > 0:
        idx = rng.choice(n, m, replace=False)
        par = (idx + 1) % n
        est[idx], tipo_i[idx], reg[idx] = est[par], tipo_i[par], reg[par]
        gem[idx] = True
    area_hab = np.array([TIPOS[c]['area'] for c in cods])[tipo_i]
    reasig = rng.random(n) < PROB_REASIGNADA
    area = np.where(reasig, rng.integers(0, 4, size=n), area_hab)
    espera = rng.choice([0, 1, 2, 3], size=n, p=[.55, .30, .10, .05])
    med = np.array([TIPOS[c]['med'] for c in cods])[tipo_i]
    proc = np.maximum(0, np.rint(rng.lognormal(np.log(med), 0.55))).astype(int)
    cie = rng.choice([0, 1, 2], size=n, p=[.6, .3, .1])
    asig = np.busday_offset(reg, espera, roll='forward', holidays=FER)
    aten = np.busday_offset(asig, proc, roll='forward', holidays=FER)
    cierre = np.busday_offset(aten, cie, roll='forward', holidays=FER)
    fin = np.datetime64(FIN, 'D')
    nat = np.datetime64('NaT', 'D')
    asig, aten, cierre = [np.where(a > fin, nat, a).astype('datetime64[D]') for a in (asig, aten, cierre)]
    sla = np.array([TIPOS[c]['sla'] for c in cods])[tipo_i]
    for j, c in enumerate(cods):
        if 'sla_nuevo' in TIPOS[c]:
            sla = np.where((tipo_i == j) & (reg >= np.datetime64(TIPOS[c]['desde'], 'D')), TIPOS[c]['sla_nuevo'], sla)
    return dict(id=np.arange(n), est=est, n_est=n_est, tipo=np.array(cods)[tipo_i], tipo_i=tipo_i, area=area,
                reg=reg, asig=asig, aten=aten, cierre=cierre, sla=sla, gemela=gem)


# =====================================================================================
# 4. PROYECCIÓN A LAS 3 FUENTES (con ruido) Y EXTRACCIONES DIARIAS
# =====================================================================================
def _fmt(d, f):
    return d.strftime(FMT_FECHA[f])


def _typo(s, rnd):
    if len(s) > 6 and rnd.random() < RUIDO['typo']:
        k = rnd.randrange(1, len(s) - 1)
        return s[:k] + s[k + 1:]
    return s


def generar_fuentes(V, seed):
    """Devuelve el DataFrame de extracciones diarias. Cada fila = lo que una fuente muestra en una carga.
    Las fuentes SOLO muestran el estado actual (no el histórico) y se actualizan con retraso aleatorio."""
    rnd = random.Random(seed)
    nprng = np.random.default_rng(seed + 1)
    n = len(V['id'])
    mem = {s: nprng.random(n) < p for s, p in PROB_FUENTE.items()}
    # toda solicitud es procesada en el sistema académico (A) o en la hoja del área (C); la mesa de partes (B) es solo canal de entrada
    sin_seguimiento = ~(mem['A'] | mem['C'])
    elegir_a = nprng.random(n) < 0.55
    mem['A'] = mem['A'] | (sin_seguimiento & elegir_a)
    mem['C'] = mem['C'] | (sin_seguimiento & ~elegir_a)
    reg = V['reg'].tolist(); asig = V['asig'].tolist(); aten = V['aten'].tolist(); cie = V['cierre'].tolist()
    est = V['est'].tolist(); tipo = V['tipo'].tolist(); area = V['area'].tolist()
    permitidos = {'A': (1, 2, 3, 4), 'B': (1, 2), 'C': (2, 3, 4)}
    filas = []
    for i in range(n):
        hitos = {1: reg[i], 2: asig[i], 3: aten[i], 4: cie[i]}
        for src in ('A', 'B', 'C'):
            if not mem[src][i]:
                continue
            rec = f'{src}{i:06d}'
            cod = f'{2018 + est[i] % 8}{est[i]:05d}'
            if rnd.random() < RUIDO['est_vacio'][src]:
                cod = ''
            if src == 'A':
                tipo_raw, area_raw = tipo[i], AREAS[area[i]]
            else:
                tipo_raw = _typo(rnd.choice(VAR_TIPO[tipo[i]]), rnd)
                area_raw = rnd.choice(VAR_AREA[area[i]]) if src == 'C' else ''
            f_reg = reg[i]
            if src == 'B' and reg[i] < FIN and rnd.random() < RUIDO['B_reg_mas1']:
                f_reg = reg[i] + timedelta(days=1)
            fmt = {'A': 'iso', 'B': 'dmy'}.get(src) or rnd.choice(['dmy', 'dmy2', 'dmy', 'iso', 'dmy3'])
            f_reg_raw = '' if rnd.random() < RUIDO['fecha_vacia'][src] else _fmt(f_reg, fmt)
            con_f_aten = src == 'C' and rnd.random() < RUIDO['C_fecha_aten']
            # días en que cada estado se hace visible (con retraso de actualización, nunca retrocede)
            obs, prev = {}, None
            for k in permitidos[src]:
                if hitos[k] is None:
                    break
                p0 = 1.0 if src == 'A' or k == 1 else RUIDO['lag_p0'][src]
                od = hitos[k] + timedelta(days=0 if rnd.random() < p0 else 1)
                if prev is not None and od < prev:
                    od = prev
                if od > FIN:
                    break
                obs[k] = od; prev = od
            por_dia = {}
            for k, od in obs.items():
                por_dia[od] = max(por_dia.get(od, 0), k)
            for od, k in por_dia.items():
                est_raw = rnd.choice(VAR_ESTADO[src][k])
                f_aten_raw = _fmt(hitos[3], fmt) if (con_f_aten and k >= 3 and hitos[3] is not None) else ''
                filas.append((od, src, rec, cod, tipo_raw, est_raw, f_reg_raw, f_aten_raw, area_raw, i))
    ext = pd.DataFrame(filas, columns=['dia', 'src', 'rec', 'estudiante', 'tipo_raw', 'estado_raw',
                                       'fecha_reg_raw', 'fecha_aten_raw', 'area_raw', 'verdad_id'])
    return ext.sort_values(['dia', 'src', 'rec'], kind='stable').reset_index(drop=True)


# =====================================================================================
# 5. ETL  (reglas i-iv del paper + regla v: imputación de hitos omitidos)
# =====================================================================================
def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', s)).strip()


MAP_TIPO = {norm(v): c for c, vs in VAR_TIPO.items() for v in vs + [c]}
MAP_ESTADO = {norm(v): k for s in VAR_ESTADO.values() for k, vs in s.items() for v in vs}
MAP_AREA = {norm(v): i for i, vs in VAR_AREA.items() for v in vs + [AREAS[i]]}


def _std(txt, mapa):
    n = norm(txt)
    if n in mapa:
        return mapa[n]
    m = difflib.get_close_matches(n, list(mapa), n=1, cutoff=0.8)
    return mapa[m[0]] if m else None


std_tipo = lru_cache(maxsize=None)(lambda t: _std(t, MAP_TIPO))
std_estado = lru_cache(maxsize=None)(lambda t: _std(t, MAP_ESTADO))
std_area = lru_cache(maxsize=None)(lambda t: _std(t, MAP_AREA) if t else None)


@lru_cache(maxsize=None)
def parse_fecha(s):
    if not s:
        return None
    for f in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%y', '%d/%m/%y'):
        try:
            return datetime.strptime(s.strip(), f).date()
        except ValueError:
            pass
    return None


def _set_hito(f, k, fecha, tipo):
    """tipo 'E' (fecha explícita de la fuente) o 'I' (inferida por la fecha de carga)."""
    cur = f['h'][k]
    if cur is None or (f['ht'][k] == 'I' and tipo == 'E'):
        f['h'][k], f['ht'][k] = fecha, tipo
    elif f['ht'][k] == 'I' and tipo == 'I' and fecha < cur:
        f['h'][k] = fecha


def _actualizar(f, r, dia, k):
    a = std_area(r.area_raw)
    if a is not None:
        f['area'] = a
    fe = parse_fecha(r.fecha_aten_raw)
    if fe is not None and k >= 3:
        _set_hito(f, 3, fe, 'E')
    if k >= 2 and not (k == 3 and fe is not None):
        _set_hito(f, k, dia, 'I')
    f['kmax'] = max(f['kmax'], k)


def etl(ext, regla):
    """regla: 'paper' (clave natural exacta) o 'tolerante' (±1 día y fuentes distintas)."""
    facts, recmap, idx_exacto, idx_tol = [], {}, {}, defaultdict(list)
    bit = defaultdict(Counter)
    pseud = {}
    for r in ext.itertuples(index=False):
        L = bit[r.dia]
        L['filas_leidas'] += 1
        kr = (r.src, r.rec)
        if kr in recmap:                                           # fila de actualización de estado
            i = recmap[kr]
            if i is None:
                L['actualizaciones_descartadas'] += 1
                continue
            k = std_estado(r.estado_raw)
            if k is not None:
                _actualizar(facts[i], r, r.dia, k)
            L['actualizaciones'] += 1
            continue
        L['registros_fuente'] += 1                                 # primera vez que se ve este registro de fuente
        # (i) limpieza
        fr = parse_fecha(r.fecha_reg_raw)
        cod = (r.estudiante or '').strip()
        # (ii) estandarización
        tipo, k = std_tipo(r.tipo_raw), std_estado(r.estado_raw)
        if not cod or fr is None or tipo is None or k is None:
            recmap[kr] = None
            L['descartados'] += 1
            continue
        # (iv) seudonimización (HMAC-SHA256 con clave secreta)
        ps = pseud.get(cod)
        if ps is None:
            ps = pseud[cod] = hmac.new(HMAC_CLAVE, cod.encode(), hashlib.sha256).hexdigest()[:16]
        # (iii) deduplicación
        i = None
        if regla == 'paper':
            i = idx_exacto.get((ps, tipo, fr))
        else:
            for j in idx_tol[(ps, tipo)]:
                fj = facts[j]
                if abs((fr - fj['reg']).days) <= 1 and r.src not in fj['srcs']:
                    i = j
                    break
        if i is None:
            f = dict(est=ps, tipo=tipo, reg=fr, area=None, h={2: None, 3: None, 4: None}, ht={}, srcs={r.src},
                     verdad=[r.verdad_id], kmax=1)
            facts.append(f)
            i = len(facts) - 1
            idx_exacto[(ps, tipo, fr)] = i
            idx_tol[(ps, tipo)].append(i)
            L['cargados'] += 1
        else:
            f = facts[i]
            f['reg'] = min(f['reg'], fr)
            f['srcs'].add(r.src)
            f['verdad'].append(r.verdad_id)
            L['fusionados'] += 1
        recmap[kr] = i
        _actualizar(f, r, r.dia, k)
    bit_df = pd.DataFrame([{'dia_carga': d.isoformat(), **{c: int(L.get(c, 0)) for c in (
        'filas_leidas', 'registros_fuente', 'descartados', 'fusionados', 'cargados', 'actualizaciones',
        'actualizaciones_descartadas')}} for d, L in sorted(bit.items())])
    return facts, bit_df


def _normalizar_hitos(f, fin):
    """Regla (v): un hito omitido se imputa con el del hito posterior; hitos fuera de orden se ajustan."""
    h = dict(f['h'])
    imp = {2: False, 3: False, 4: False}
    if h[4] is not None:
        if h[3] is None: h[3], imp[3] = h[4], True
    if h[3] is not None:
        if h[2] is None: h[2], imp[2] = h[3], True
    if h[4] is not None:
        if h[3] is not None and h[3] > h[4]: h[3] = h[4]
        if h[2] is not None and h[2] > h[4]: h[2] = h[4]
    if h[3] is not None and h[2] is not None and h[2] > h[3]:
        h[2] = h[3]
    return h, imp


def hechos_desde_etl(facts, dims):
    nro, base_sk = dims['nro'], dims['base_sk']
    sla_de = dict(zip(dims['tipo'].sk_tipo, dims['tipo'].sla_dias))
    usuarios, rows, fechas, imps = {}, [], defaultdict(list), defaultdict(list)
    nro_fin = nro[FIN]
    for i, f in enumerate(facts, 1):
        h, imp = _normalizar_hitos(f, FIN)
        skt = sk_tipo_de(f['tipo'], f['reg'], base_sk)
        sla = sla_de[skt]
        usr = usuarios.setdefault(f['est'], len(usuarios) + 1)
        kf = lambda d: None if d is None else d.year * 10000 + d.month * 100 + d.day
        esp = None if h[2] is None else nro[h[2]] - nro[f['reg']]
        pro = None if (h[2] is None or h[3] is None) else nro[h[3]] - nro[h[2]]
        tot = None if h[3] is None else nro[h[3]] - nro[f['reg']]
        en_plazo = None if tot is None else int(tot <= sla)
        venc = 0 if h[3] is not None else int(nro_fin - nro[f['reg']] > sla)
        rows.append((i, skt, f['kmax'], (f['area'] if f['area'] is not None else 0) + 1, usr, kf(f['reg']),
                     kf(h[2]), kf(h[3]), kf(h[4]), esp, pro, tot, en_plazo, venc, 1))
        for k, nm in ((1, 'reg'), (2, 'asig'), (3, 'aten'), (4, 'cierre')):
            fechas[nm].append(f['reg'] if k == 1 else h[k])
        for k in (2, 3, 4):
            imps[k].append(imp[k])
    cols = ['sk_solicitud', 'sk_tipo', 'sk_estado', 'sk_area', 'sk_usuario', 'sk_fecha_registro', 'sk_fecha_asignacion',
            'sk_fecha_atencion', 'sk_fecha_cierre', 'dias_espera', 'dias_proceso', 'dias_total', 'en_plazo', 'vencida', 'cantidad']
    df = pd.DataFrame(rows, columns=cols)
    for c in cols[1:]:
        df[c] = df[c].astype('Int64')
    df['sk_solicitud'] = df['sk_solicitud'].astype('int64')
    dim_usuario = pd.DataFrame({'sk_usuario': list(usuarios.values()), 'id_pseudonimo': list(usuarios.keys())})
    fa = {k: np.array([np.datetime64(d, 'D') if d is not None else np.datetime64('NaT', 'D') for d in v]) for k, v in fechas.items()}
    return df, dim_usuario, fa, {k: np.array(v) for k, v in imps.items()}


def hechos_desde_verdad(V, dims):
    """Carga directa (sin ETL) para las escalas de E2: el esquema estrella perfecto a gran volumen."""
    n = len(V['id'])
    base = dims['base_sk']
    skt = np.array([base[c] for c in V['tipo']])
    for c, t in TIPOS.items():
        if 'sla_nuevo' in t:
            skt = np.where((V['tipo'] == c) & (V['reg'] >= np.datetime64(t['desde'], 'D')), base[c] + 1, skt)
    reg, asig, aten, cie = V['reg'], V['asig'], V['aten'], V['cierre']
    esp = np.full(n, -1); pro = np.full(n, -1); tot = np.full(n, -1)
    m2, m3 = ~np.isnat(asig), ~np.isnat(aten)
    esp[m2] = d_hab(reg[m2], asig[m2]); tot[m3] = d_hab(reg[m3], aten[m3]); pro[m3] = d_hab(asig[m3], aten[m3])
    est = np.where(~np.isnat(cie), 4, np.where(m3, 3, np.where(m2, 2, 1)))
    fin = np.datetime64(FIN, 'D')
    venc = np.where(m3, 0, (d_hab(reg, np.full(n, fin)) > V['sla']).astype(int))
    df = pd.DataFrame({'sk_solicitud': np.arange(1, n + 1), 'sk_tipo': skt, 'sk_estado': est, 'sk_area': V['area'] + 1,
                       'sk_usuario': V['est'] + 1, 'sk_fecha_registro': clave_fecha(reg),
                       'sk_fecha_asignacion': clave_fecha(asig), 'sk_fecha_atencion': clave_fecha(aten),
                       'sk_fecha_cierre': clave_fecha(cie),
                       'dias_espera': pd.Series(esp).where(esp >= 0).astype('Int64'),
                       'dias_proceso': pd.Series(pro).where(pro >= 0).astype('Int64'),
                       'dias_total': pd.Series(tot).where(tot >= 0).astype('Int64'),
                       'en_plazo': pd.Series(np.where(m3, (tot <= V['sla']).astype(int), -1)).where(m3).astype('Int64'),
                       'vencida': venc, 'cantidad': 1})
    usuarios = pd.DataFrame({'sk_usuario': np.arange(1, V['n_est'] + 1),
                             'id_pseudonimo': [hmac.new(HMAC_CLAVE, str(e).encode(), hashlib.sha256).hexdigest()[:16]
                                               for e in range(V['n_est'])]})
    return df, usuarios


# =====================================================================================
# 6. BASE DE DATOS (PostgreSQL o SQLite de respaldo)
# =====================================================================================
DDL = """
DROP TABLE IF EXISTS bitacora_carga;
DROP TABLE IF EXISTS hecho_solicitud;
DROP TABLE IF EXISTS dim_usuario;
DROP TABLE IF EXISTS dim_area;
DROP TABLE IF EXISTS dim_estado;
DROP TABLE IF EXISTS dim_tipo_solicitud;
DROP TABLE IF EXISTS dim_fecha;
CREATE TABLE dim_fecha (
  sk_fecha INTEGER PRIMARY KEY, fecha DATE NOT NULL, anio SMALLINT, mes SMALLINT, anio_mes INTEGER,
  dia_semana SMALLINT, es_habil SMALLINT NOT NULL, nro_habil INTEGER NOT NULL);
CREATE TABLE dim_tipo_solicitud (
  sk_tipo INTEGER PRIMARY KEY, cod_tipo VARCHAR(10) NOT NULL, nombre_tipo VARCHAR(60) NOT NULL, sla_dias SMALLINT NOT NULL,
  vigente_desde DATE NOT NULL, vigente_hasta DATE NOT NULL, es_vigente SMALLINT NOT NULL);
CREATE TABLE dim_estado (sk_estado INTEGER PRIMARY KEY, cod_estado SMALLINT, nombre_estado VARCHAR(30), es_final SMALLINT);
CREATE TABLE dim_area (sk_area INTEGER PRIMARY KEY, nombre_area VARCHAR(60) NOT NULL);
CREATE TABLE dim_usuario (sk_usuario INTEGER PRIMARY KEY, id_pseudonimo VARCHAR(32) NOT NULL);
CREATE TABLE hecho_solicitud (
  sk_solicitud INTEGER PRIMARY KEY, sk_tipo INTEGER NOT NULL, sk_estado INTEGER NOT NULL, sk_area INTEGER NOT NULL,
  sk_usuario INTEGER NOT NULL, sk_fecha_registro INTEGER NOT NULL, sk_fecha_asignacion INTEGER, sk_fecha_atencion INTEGER,
  sk_fecha_cierre INTEGER, dias_espera SMALLINT, dias_proceso SMALLINT, dias_total SMALLINT, en_plazo SMALLINT,
  vencida SMALLINT NOT NULL, cantidad SMALLINT NOT NULL);
CREATE TABLE bitacora_carga (
  dia_carga DATE, filas_leidas INTEGER, registros_fuente INTEGER, descartados INTEGER, fusionados INTEGER,
  cargados INTEGER, actualizaciones INTEGER, actualizaciones_descartadas INTEGER);
"""
INDICES = """
CREATE INDEX ix_h_reg ON hecho_solicitud (sk_fecha_registro);
CREATE INDEX ix_h_aten ON hecho_solicitud (sk_fecha_atencion);
CREATE INDEX ix_h_tipo ON hecho_solicitud (sk_tipo);
CREATE INDEX ix_h_area ON hecho_solicitud (sk_area);
"""


class Gestor:
    def __init__(self, args):
        self.a = args
        self.kind = args.db

    def conectar(self, esquema, crear=False):
        if self.kind == 'sqlite':
            import sqlite3
            os.makedirs(self.a.out, exist_ok=True)
            ruta = os.path.join(self.a.out, f'{esquema}.db')
            if crear and os.path.exists(ruta):
                os.remove(ruta)
            return sqlite3.connect(ruta)
        import psycopg2
        kw = dict(host=self.a.host, port=self.a.port, dbname=self.a.dbname, user=self.a.user, password=self.a.password)
        if crear:
            c0 = psycopg2.connect(**kw); c0.autocommit = True
            c0.cursor().execute(f'DROP SCHEMA IF EXISTS {esquema} CASCADE; CREATE SCHEMA {esquema};')
            c0.close()
        conn = psycopg2.connect(options=f'-c search_path={esquema}', **kw)
        conn.autocommit = True
        return conn

    def script(self, conn, sql):
        if self.kind == 'sqlite':
            conn.executescript(sql)
        else:
            conn.cursor().execute(sql)

    def cargar(self, conn, tabla, df):
        cols = ','.join(df.columns)
        if self.kind == 'sqlite':
            datos = df.astype(object).where(df.notna(), None).values.tolist()
            conn.executemany(f'INSERT INTO {tabla} ({cols}) VALUES ({",".join("?" * len(df.columns))})', datos)
            conn.commit()
        else:
            buf = io.StringIO()
            df.to_csv(buf, index=False, header=False, na_rep='')
            buf.seek(0)
            conn.cursor().copy_expert(f"COPY {tabla} ({cols}) FROM STDIN WITH (FORMAT csv, NULL '')", buf)

    def construir(self, esquema, dims, hechos, usuarios, bitacora=None):
        conn = self.conectar(esquema, crear=True)
        self.script(conn, DDL)
        for t, df in (('dim_fecha', dims['fecha']), ('dim_tipo_solicitud', dims['tipo']), ('dim_estado', dims['estado']),
                      ('dim_area', dims['area']), ('dim_usuario', usuarios), ('hecho_solicitud', hechos)):
            self.cargar(conn, t, df)
        if bitacora is not None and len(bitacora):
            self.cargar(conn, 'bitacora_carga', bitacora)
        self.script(conn, INDICES)
        if self.kind == 'sqlite':
            conn.execute('ANALYZE'); conn.commit()
        else:
            conn.cursor().execute('ANALYZE')
        return conn

    def consultar(self, conn, sql):
        cur = conn.cursor(); cur.execute(sql)
        cols = [d[0] for d in cur.description]; rows = cur.fetchall(); cur.close()
        df = pd.DataFrame(rows, columns=cols)
        for c in df.columns:
            if c.startswith('valor'):
                df[c] = pd.to_numeric(df[c], errors='coerce').astype(float)
        return df


# =====================================================================================
# 7. CONSULTAS SQL DE LOS 8 KPI  (cada KPI = una consulta; T = fecha de corte como aaaammdd)
# =====================================================================================
def sql_kpi(T):
    ven = (f"AND (h.sk_fecha_atencion IS NULL OR h.sk_fecha_atencion > {T}) AND h.sk_fecha_registro <= {T}")
    return {
        'K1': "SELECT f.anio_mes AS mes, t.cod_tipo AS tipo, COUNT(*) AS valor FROM hecho_solicitud h "
              "JOIN dim_fecha f ON f.sk_fecha = h.sk_fecha_registro JOIN dim_tipo_solicitud t ON t.sk_tipo = h.sk_tipo "
              "GROUP BY f.anio_mes, t.cod_tipo",
        'K2': f"SELECT CASE WHEN h.sk_fecha_cierre <= {T} THEN 4 WHEN h.sk_fecha_atencion <= {T} THEN 3 "
              f"WHEN h.sk_fecha_asignacion <= {T} THEN 2 ELSE 1 END AS estado, COUNT(*) AS valor "
              f"FROM hecho_solicitud h WHERE h.sk_fecha_registro <= {T} GROUP BY 1",
        'K3': f"SELECT t.cod_tipo AS tipo, COUNT(*) AS valor FROM hecho_solicitud h "
              f"JOIN dim_tipo_solicitud t ON t.sk_tipo = h.sk_tipo WHERE 1=1 {ven} GROUP BY t.cod_tipo",
        'K4': "SELECT f.anio_mes AS mes, t.cod_tipo AS tipo, AVG(h.dias_total * 1.0) AS valor FROM hecho_solicitud h "
              "JOIN dim_fecha f ON f.sk_fecha = h.sk_fecha_atencion JOIN dim_tipo_solicitud t ON t.sk_tipo = h.sk_tipo "
              "WHERE h.sk_fecha_atencion IS NOT NULL GROUP BY f.anio_mes, t.cod_tipo",
        'K5': "SELECT f.anio_mes AS mes, t.cod_tipo AS tipo, 100.0 * SUM(h.en_plazo) / COUNT(*) AS valor FROM hecho_solicitud h "
              "JOIN dim_fecha f ON f.sk_fecha = h.sk_fecha_atencion JOIN dim_tipo_solicitud t ON t.sk_tipo = h.sk_tipo "
              "WHERE h.sk_fecha_atencion IS NOT NULL GROUP BY f.anio_mes, t.cod_tipo",
        'K6': f"SELECT t.cod_tipo AS tipo, COUNT(*) AS valor FROM hecho_solicitud h "
              f"JOIN dim_fecha fr ON fr.sk_fecha = h.sk_fecha_registro JOIN dim_tipo_solicitud t ON t.sk_tipo = h.sk_tipo "
              f"WHERE 1=1 {ven} AND ((SELECT nro_habil FROM dim_fecha WHERE sk_fecha = {T}) - fr.nro_habil) > t.sla_dias "
              f"GROUP BY t.cod_tipo",
        'K7': f"SELECT a.nombre_area AS area, COUNT(*) AS valor FROM hecho_solicitud h "
              f"JOIN dim_area a ON a.sk_area = h.sk_area WHERE 1=1 {ven} GROUP BY a.nombre_area",
        'K8': "SELECT t.cod_tipo AS tipo, AVG(h.dias_espera * 1.0) AS valor, AVG(h.dias_proceso * 1.0) AS valor2 "
              "FROM hecho_solicitud h JOIN dim_tipo_solicitud t ON t.sk_tipo = h.sk_tipo GROUP BY t.cod_tipo",
    }


def cortes_mensuales():
    d = pd.date_range(INICIO, FIN, freq='ME')
    out = [x.date() for x in d]
    if out[-1] != FIN:
        out.append(FIN)
    return out


def kpis_modelo(gest, conn):
    """Ejecuta los 8 KPI sobre el esquema estrella. K2,K3,K6,K7 se evalúan en cada fin de mes."""
    res = {}
    cuts = cortes_mensuales()
    for k in ('K1', 'K4', 'K5', 'K8'):
        res[k] = gest.consultar(conn, sql_kpi(clave_int(FIN))[k])
    for k in ('K2', 'K3', 'K6', 'K7'):
        partes = []
        for c in cuts:
            df = gest.consultar(conn, sql_kpi(clave_int(c))[k])
            df.insert(0, 'corte', clave_int(c))
            partes.append(df)
        res[k] = pd.concat(partes, ignore_index=True)
    k8 = res['K8']
    res['K8'] = pd.concat([k8[['tipo', 'valor']].assign(etapa='espera'),
                           k8[['tipo', 'valor2']].rename(columns={'valor2': 'valor'}).assign(etapa='proceso')], ignore_index=True)
    return res


def clave_int(d):
    return d.year * 10000 + d.month * 100 + d.day


# =====================================================================================
# 8. ORÁCULO INDEPENDIENTE (pandas/numpy sobre la verdad; no usa SQL ni DIM_FECHA)
# =====================================================================================
def kpis_oraculo(V):
    reg, asig, aten, cie = V['reg'], V['asig'], V['aten'], V['cierre']
    tipo, area, sla = V['tipo'], np.array(AREAS)[V['area']], V['sla']
    res = {}
    res['K1'] = pd.DataFrame({'mes': ym(reg), 'tipo': tipo}).groupby(['mes', 'tipo']).size().rename('valor').reset_index()
    m3 = ~np.isnat(aten)
    dt = d_hab(reg[m3], aten[m3])
    base = pd.DataFrame({'mes': ym(aten[m3]), 'tipo': tipo[m3], 'dt': dt, 'ok': (dt <= sla[m3]).astype(float) * 100})
    res['K4'] = base.groupby(['mes', 'tipo']).dt.mean().rename('valor').reset_index()
    res['K5'] = base.groupby(['mes', 'tipo']).ok.mean().rename('valor').reset_index()
    m2 = ~np.isnat(asig)
    esp = pd.DataFrame({'tipo': tipo[m2], 'valor': d_hab(reg[m2], asig[m2])}).groupby('tipo').valor.mean().reset_index().assign(etapa='espera')
    pro = pd.DataFrame({'tipo': tipo[m3], 'valor': d_hab(asig[m3], aten[m3])}).groupby('tipo').valor.mean().reset_index().assign(etapa='proceso')
    res['K8'] = pd.concat([esp, pro], ignore_index=True)
    p2, p3, p6, p7 = [], [], [], []
    for c in cortes_mensuales():
        T = np.datetime64(c, 'D'); kc = clave_int(c)
        r = reg <= T
        est = np.where(~np.isnat(cie) & (cie <= T), 4, np.where(~np.isnat(aten) & (aten <= T), 3,
                       np.where(~np.isnat(asig) & (asig <= T), 2, 1)))
        p2.append(pd.Series(est[r]).value_counts().rename('valor').rename_axis('estado').reset_index().assign(corte=kc))
        pend = r & (np.isnat(aten) | (aten > T))
        p3.append(pd.Series(tipo[pend]).value_counts().rename('valor').rename_axis('tipo').reset_index().assign(corte=kc))
        venc = pend.copy()
        venc[pend] = d_hab(reg[pend], np.full(pend.sum(), T)) > sla[pend]
        p6.append(pd.Series(tipo[venc]).value_counts().rename('valor').rename_axis('tipo').reset_index().assign(corte=kc))
        p7.append(pd.Series(area[pend]).value_counts().rename('valor').rename_axis('area').reset_index().assign(corte=kc))
    res['K2'], res['K3'], res['K6'], res['K7'] = [pd.concat(p, ignore_index=True) for p in (p2, p3, p6, p7)]
    for k in res:
        res[k]['valor'] = res[k]['valor'].astype(float)
    return res


CLAVES = {'K1': ['mes', 'tipo'], 'K2': ['corte', 'estado'], 'K3': ['corte', 'tipo'], 'K4': ['mes', 'tipo'],
          'K5': ['mes', 'tipo'], 'K6': ['corte', 'tipo'], 'K7': ['corte', 'area'], 'K8': ['tipo', 'etapa']}


def exactitud_kpi(mod, ora):
    filas, det = [], []
    for k, claves in CLAVES.items():
        o = ora[k][claves + ['valor']].rename(columns={'valor': 'o'})
        m = mod[k][claves + ['valor']].rename(columns={'valor': 'm'})
        j = o.merge(m, on=claves, how='outer').fillna({'o': 0.0, 'm': 0.0})
        rel = np.where((j.o == 0) & (j.m == 0), 0.0, np.minimum(1.0, (j.m - j.o).abs() / np.maximum(j.o.abs(), 1e-9)))
        j['error_rel'] = rel
        j.insert(0, 'kpi', k)
        det.append(j)
        wape = float((j.m - j.o).abs().sum() / max(j.o.abs().sum(), 1e-9))
        filas.append(dict(kpi=k, celdas=len(j), exactitud_pct=100 * (1 - rel.mean()),
                          exactitud_wape_pct=max(0.0, 100 * (1 - wape)),
                          celdas_exactas_pct=100 * float((((j.m - j.o).abs() < 0.005)).mean())))
    tabla = pd.DataFrame(filas)
    return tabla, pd.concat(det, ignore_index=True)


# =====================================================================================
# 9. MÉTRICAS DE E1: duplicados, completitud y exactitud de hitos
# =====================================================================================
def _pares(s):
    return float((s * (s - 1) // 2).sum())


def metricas_e1(facts, bit, V, fa, imps, hechos):
    tot = bit[['registros_fuente', 'descartados', 'fusionados', 'cargados', 'actualizaciones']].sum()
    N, x, y, z = (int(tot[c]) for c in ('registros_fuente', 'descartados', 'fusionados', 'cargados'))
    pares = [(i, v) for i, f in enumerate(facts) for v in f['verdad']]
    pc = pd.DataFrame(pares, columns=['fact', 'real'])
    tp = _pares(pc.groupby(['fact', 'real']).size())
    pred = _pares(pc.groupby('fact').size()); real = _pares(pc.groupby('real').size())
    n_hechos_por_real = pc.drop_duplicates().groupby('real').size()
    r = dict(N=N, x_descartados=x, y_fusionados=y, z_unicas=z, conciliacion_ok=bool(N == x + y + z),
             solicitudes_reales=int(len(V['id'])), registros_fuente_conservados=int(len(pc)),
             solicitudes_reales_representadas=int(pc.real.nunique()),
             duplicados_no_detectados=int((n_hechos_por_real - 1).clip(lower=0).sum()),
             fusiones_erroneas=int(sum(len(set(f['verdad'])) - 1 for f in facts)),
             dedup_precision_pct=100 * tp / pred if pred else 100.0, dedup_recall_pct=100 * tp / real if real else 100.0,
             tasa_duplicados_eliminados_pct=100 * y / N)
    ids = np.array([f['verdad'][0] for f in facts])
    for nombre, mk, vk, ik in (('asignacion', 'asig', 'asig', 2), ('atencion', 'aten', 'aten', 3), ('cierre', 'cierre', 'cierre', 4)):
        tv, mv = V[vk][ids], fa[mk]
        debe, tiene = ~np.isnat(tv), ~np.isnat(mv)
        ambos = debe & tiene
        dif = np.abs((mv[ambos] - tv[ambos]).astype(int))
        r[f'completitud_{nombre}_pct'] = 100 * ambos.sum() / debe.sum()
        r[f'hito_{nombre}_exacto_pct'] = 100 * float((dif == 0).mean())
        r[f'hito_{nombre}_dentro_1dia_pct'] = 100 * float((dif <= 1).mean())
        r[f'hito_{nombre}_imputado_pct'] = 100 * float(imps[ik][debe].mean())
    r['pendientes_fantasma'] = int((~np.isnat(V['aten'][ids]) & np.isnat(fa['aten'])).sum())   # atendidas en la verdad, sin hito de atención en el modelo
    r['completitud_hitos_global_pct'] = float(np.mean([r[f'completitud_{n}_pct'] for n in ('asignacion', 'atencion', 'cierre')]))
    tv_a, mv_a = V['aten'][ids], fa['aten']
    ambos = ~np.isnat(tv_a) & ~np.isnat(mv_a)
    real_tot = d_hab(V['reg'][ids][ambos], tv_a[ambos])
    mod_tot = hechos['dias_total'].astype('float').values[ambos]
    r['dias_total_exacto_pct'] = 100 * float((real_tot == mod_tot).mean())
    real_ok = (real_tot <= V['sla'][ids][ambos]).astype(int)
    mod_ok = hechos['en_plazo'].astype('float').values[ambos]
    r['flag_en_plazo_discrepante_pct'] = 100 * float((real_ok != mod_ok).mean())
    r['exactitud_por_solicitud_pct'] = 100 * float(((real_tot == mod_tot) & (real_ok == mod_ok)).mean())   # días y flag en plazo correctos
    err_bus = (mod_tot - real_tot)
    r['error_dias_total_habiles'] = {str(int(k)): int(v) for k, v in pd.Series(err_bus).value_counts().items()}
    return r


def globales(hechos, V):
    """Valores globales (al corte final) del modelo frente a la verdad."""
    m = dict(K1=len(hechos), K3=int(hechos.sk_fecha_atencion.isna().sum()), K6=int(hechos.vencida.astype(int).sum()),
             K4=float(hechos.dias_total.dropna().astype(float).mean()), K5=100 * float(hechos.en_plazo.dropna().astype(float).mean()))
    m3 = ~np.isnat(V['aten']); dt = d_hab(V['reg'][m3], V['aten'][m3]); pend = ~m3
    ven = int((d_hab(V['reg'][pend], np.full(int(pend.sum()), np.datetime64(FIN, 'D'))) > V['sla'][pend]).sum())
    o = dict(K1=len(V['id']), K3=int(pend.sum()), K6=ven, K4=float(dt.mean()), K5=100 * float((dt <= V['sla'][m3]).mean()))
    return {k: dict(modelo=round(m[k], 3), verdad=round(o[k], 3), error_rel_pct=round(100 * abs(m[k] - o[k]) / o[k], 2)) for k in m}


def efecto_scd2(V):
    """CSLA de CERT: con el SLA vigente al registrar (SCD2) vs usando siempre el SLA actual (sin SCD2)."""
    m = (V['tipo'] == 'CERT') & ~np.isnat(V['aten']) & (V['reg'] < np.datetime64(TIPOS['CERT']['desde'], 'D'))
    d = d_hab(V['reg'][m], V['aten'][m])
    return dict(n=int(m.sum()), csla_con_scd2=100 * float((d <= TIPOS['CERT']['sla']).mean()),
                csla_sin_scd2=100 * float((d <= TIPOS['CERT']['sla_nuevo']).mean()))


# =====================================================================================
# 10. EXCEL DE VERIFICACIÓN MANUAL (E1) Y PAQUETE DE E3
# =====================================================================================
def excel_verificacion(path, facts, V, hechos, n=200, seed=7):
    from openpyxl import Workbook
    rng = np.random.default_rng(seed)
    ids = np.array([f['verdad'][0] for f in facts])
    ok = np.where(~np.isnat(V['aten'][ids]) & hechos['dias_total'].notna().values)[0]
    pick = rng.choice(ok, size=min(n, len(ok)), replace=False)
    wb = Workbook(); ws = wb.active; ws.title = 'Muestra'
    ws.append(['id_solicitud', 'tipo', 'fecha_registro', 'fecha_atencion', 'SLA_vigente', 'dias_habiles_MANUAL',
               'en_plazo_MANUAL', 'dias_total_MODELO', 'en_plazo_MODELO', 'coincide'])
    for r, j in enumerate(pick, 2):
        t = ids[j]
        ws.append([int(t), str(V['tipo'][t]), V['reg'][t].astype(datetime), V['aten'][t].astype(datetime), int(V['sla'][t]),
                   f'=IF(D{r}<=C{r},0,NETWORKDAYS(C{r}+1,D{r},Feriados!$A$2:$A$30))', f'=IF(F{r}<=E{r},1,0)',
                   int(hechos['dias_total'].iloc[j]), int(hechos['en_plazo'].iloc[j]), f'=IF(AND(F{r}=H{r},G{r}=I{r}),1,0)'])
        ws[f'C{r}'].number_format = ws[f'D{r}'].number_format = 'yyyy-mm-dd'
    f = len(pick) + 1
    ws['L1'], ws['M1'] = 'Resumen', 'Valor'
    resumen = [('n muestra', f'=COUNTA(A2:A{f})'), ('TPA manual (días hábiles)', f'=AVERAGE(F2:F{f})'),
               ('TPA modelo', f'=AVERAGE(H2:H{f})'), ('CSLA manual (%)', f'=100*AVERAGE(G2:G{f})'),
               ('CSLA modelo (%)', f'=100*AVERAGE(I2:I{f})'), ('Coincidencia solicitud a solicitud (%)', f'=100*AVERAGE(J2:J{f})')]
    for i, (a, b) in enumerate(resumen, 2):
        ws[f'L{i}'], ws[f'M{i}'] = a, b
    wf = wb.create_sheet('Feriados'); wf.append(['feriado'])
    for d in FERIADOS:
        wf.append([datetime.strptime(d, '%Y-%m-%d').date()]); wf.cell(wf.max_row, 1).number_format = 'yyyy-mm-dd'
    wb.calculation.fullCalcOnLoad = True
    wb.save(path)


def paquete_e3(out, ext, V, gest, conn):
    from openpyxl import Workbook
    carpeta = os.path.join(out, 'e3'); os.makedirs(carpeta, exist_ok=True)
    sql_txt = ['-- Reportes del procedimiento "con el modelo" (E3). Pegar en Metabase (pregunta SQL nativa) o en pgAdmin/DBeaver.\n']
    for nombre, ini, fin in PERIODOS_E3:
        corte = fin + timedelta(days=CORTE_E3_DIAS)
        ki, kf = clave_int(ini), clave_int(fin)
        kc = clave_int(corte)
        vreg = V['reg'][ext.verdad_id.values]
        mask = (vreg >= np.datetime64(ini, 'D')) & (vreg <= np.datetime64(fin, 'D')) & (ext.dia <= corte).values
        sub = ext[mask].sort_values('dia').groupby(['src', 'rec']).tail(1)
        wb = Workbook(); wb.remove(wb.active)
        cfg = {'Sistema_Academico': ('A', ['id_registro', 'cod_estudiante', 'tipo', 'estado', 'fecha_registro', 'area'],
                                     ['rec', 'estudiante', 'tipo_raw', 'estado_raw', 'fecha_reg_raw', 'area_raw']),
               'Mesa_Partes': ('B', ['nro_expediente', 'cod_estudiante', 'asunto', 'estado', 'fecha_recepcion'],
                               ['rec', 'estudiante', 'tipo_raw', 'estado_raw', 'fecha_reg_raw']),
               'Hojas_Area': ('C', ['registro', 'cod_estudiante', 'tramite', 'estado', 'fecha_registro', 'fecha_atencion', 'area'],
                              ['rec', 'estudiante', 'tipo_raw', 'estado_raw', 'fecha_reg_raw', 'fecha_aten_raw', 'area_raw'])}
        for hoja, (s, cab, cols) in cfg.items():
            ws = wb.create_sheet(hoja); ws.append(cab)
            for fila in sub[sub.src == s][cols].itertuples(index=False):
                ws.append(list(fila))
        wi = wb.create_sheet('Instrucciones', 0)
        for linea in [f'PERIODO {nombre}: solicitudes registradas del {ini} al {fin}. Corte de información: {corte}.',
                      'Elabore con Excel (sin ayuda de la base de datos) los reportes:',
                      'R1. Solicitudes PENDIENTES (sin atender) a la fecha de corte, por área.',
                      'R2. Por tipo de trámite: solicitudes atendidas, tiempo promedio de atención (días hábiles) y % de cumplimiento del SLA.',
                      'Considere: una misma solicitud puede aparecer en varias hojas (no cuente duplicados).',
                      'SLA (días hábiles): Constancia 3 | Certificado 10 (7 desde 01/07/2025) | Rectificación 5 | Convalidación 15 | Reclamo 10.',
                      'Días hábiles = lunes a viernes sin feriados (ver hoja Feriados). Anote hora de inicio y fin.']:
            wi.append([linea])
        wf = wb.create_sheet('Feriados'); wf.append(['feriado']); [wf.append([d]) for d in FERIADOS]
        wb.save(os.path.join(carpeta, f'base_manual_periodo_{nombre}.xlsx'))
        q1 = (f"SELECT a.nombre_area AS area, COUNT(*) AS pendientes FROM hecho_solicitud h JOIN dim_area a ON a.sk_area = h.sk_area "
              f"WHERE h.sk_fecha_registro BETWEEN {ki} AND {kf} AND (h.sk_fecha_atencion IS NULL OR h.sk_fecha_atencion > {kc}) "
              f"GROUP BY a.nombre_area ORDER BY 1")
        q2 = (f"SELECT t.nombre_tipo AS tipo, COUNT(*) AS atendidas, ROUND(AVG(h.dias_total * 1.0), 2) AS tpa_dias, "
              f"ROUND(100.0 * SUM(h.en_plazo) / COUNT(*), 1) AS pct_sla FROM hecho_solicitud h "
              f"JOIN dim_tipo_solicitud t ON t.sk_tipo = h.sk_tipo WHERE h.sk_fecha_registro BETWEEN {ki} AND {kf} "
              f"AND h.sk_fecha_atencion <= {kc} GROUP BY t.nombre_tipo ORDER BY 1")
        sql_txt += [f'\n-- ===== Periodo {nombre} (registradas {ini} a {fin}; corte {corte}) =====\n-- R1\n{q1};\n-- R2\n{q2};\n']
        # respuestas de referencia: oráculo (verdad) y modelo (SQL)
        T = np.datetime64(corte, 'D'); a, b = np.datetime64(ini, 'D'), np.datetime64(fin, 'D')
        r = (V['reg'] >= a) & (V['reg'] <= b)
        pend = r & (np.isnat(V['aten']) | (V['aten'] > T))
        ref1 = pd.Series(np.array(AREAS)[V['area'][pend]]).value_counts().rename('pendientes_verdad').rename_axis('area').sort_index()
        att = r & ~np.isnat(V['aten']) & (V['aten'] <= T)
        d = d_hab(V['reg'][att], V['aten'][att])
        ref2 = pd.DataFrame({'tipo': [TIPOS[c]['nombre'] for c in V['tipo'][att]], 'd': d, 'ok': d <= V['sla'][att]}).groupby('tipo').agg(
            atendidas_verdad=('d', 'size'), tpa_verdad=('d', 'mean'), pct_sla_verdad=('ok', lambda s: 100 * s.mean())).round(2)
        m1, m2 = gest.consultar(conn, q1).set_index('area'), gest.consultar(conn, q2).set_index('tipo')
        ref1.to_frame().join(m1).to_csv(os.path.join(carpeta, f'respuestas_correctas_R1_{nombre}.csv'))
        ref2.join(m2).to_csv(os.path.join(carpeta, f'respuestas_correctas_R2_{nombre}.csv'))
    with open(os.path.join(carpeta, 'reportes_modelo.sql'), 'w', encoding='utf-8') as fh:
        fh.write(''.join(sql_txt))
    filas = []
    for p in range(1, 9):
        g = 'G1' if p % 2 else 'G2'
        orden = [('manual', 'A'), ('modelo', 'B')] if g == 'G1' else [('modelo', 'A'), ('manual', 'B')]
        for o, (cond, per) in enumerate(orden, 1):
            for rep in ('R1', 'R2'):
                filas.append([f'P{p}', g, o, cond, per, rep, '', '', ''])
    pd.DataFrame(filas, columns=['participante', 'grupo', 'orden', 'condicion', 'periodo', 'reporte', 'minutos', 'correcto_1_0',
                                 'observaciones']).to_csv(os.path.join(carpeta, 'e3_tiempos.csv'), index=False)


# =====================================================================================
# 11. E2: TIEMPOS DE CONSULTA
# =====================================================================================
def esperar_conexion(gest, esquema, intentos=40):
    for _ in range(intentos):
        try:
            return gest.conectar(esquema)
        except Exception:
            time.sleep(1)
    raise RuntimeError('No se pudo reconectar a PostgreSQL tras el reinicio. Revise --reinicio.')


def medir(conn, sql):
    t0 = time.perf_counter()
    cur = conn.cursor(); cur.execute(sql); cur.fetchall(); cur.close()
    return time.perf_counter() - t0


def e2(gest, args, dims, escalas_conn):
    T = clave_int(FIN)
    consultas = {k: v for k, v in sql_kpi(T).items()}
    filas = []
    for escala, esquema in escalas_conn:
        conn = gest.conectar(esquema)
        for k, sql in consultas.items():
            medir(conn, sql)                                        # calentamiento (no se registra)
            for rep in range(args.reps):
                filas.append((escala, k, 'caliente', rep + 1, medir(conn, sql)))
            if gest.kind == 'postgres' and args.reps_fria > 0:
                for rep in range(args.reps_fria):
                    conn.close()
                    subprocess.run(args.reinicio, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    conn = esperar_conexion(gest, esquema)
                    filas.append((escala, k, 'fria', rep + 1, medir(conn, sql)))
            print(f'   E2 escala {escala}x {k} listo', flush=True)
        conn.close()
    df = pd.DataFrame(filas, columns=['escala', 'kpi', 'cache', 'rep', 'segundos'])
    res = df.groupby(['escala', 'kpi', 'cache']).segundos.agg(
        media='mean', mediana='median', p95=lambda s: s.quantile(0.95), maximo='max').reset_index()
    glob = df.groupby(['escala', 'cache']).segundos.agg(media='mean', p95=lambda s: s.quantile(0.95), maximo='max').reset_index()
    return df, res, glob


# =====================================================================================
# 12. PROGRAMA PRINCIPAL
# =====================================================================================
def conv(o):
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return float(o)
    if isinstance(o, (np.bool_,)): return bool(o)
    raise TypeError(type(o))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--db', choices=['postgres', 'sqlite'], default='postgres')
    ap.add_argument('--host', default='localhost'); ap.add_argument('--port', type=int, default=5433)
    ap.add_argument('--dbname', default='postgres'); ap.add_argument('--user', default='postgres')
    ap.add_argument('--password', default='postgres')
    ap.add_argument('--n', type=int, default=20000, help='solicitudes del escenario base (1x)')
    ap.add_argument('--escalas', default='1,10,100', help='escalas de volumen para E2')
    ap.add_argument('--reps', type=int, default=30, help='repeticiones con caché caliente')
    ap.add_argument('--reps-fria', type=int, default=30, dest='reps_fria', help='repeticiones con caché fría (reinicia PostgreSQL)')
    ap.add_argument('--reinicio', default='docker restart pg-solicitudes', help='comando que reinicia PostgreSQL')
    ap.add_argument('--sin-e2', action='store_true'); ap.add_argument('--out', default='resultados')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    gest = Gestor(args)
    t00 = time.time()
    print('1/6 Generando datos sintéticos...', flush=True)
    rng = np.random.default_rng(SEED)
    V = generar_verdad(args.n, rng)
    ext = generar_fuentes(V, SEED)
    ext.drop(columns=['verdad_id']).to_csv(os.path.join(args.out, 'extracciones_diarias_muestra.csv'), index=False) if len(ext) < 2_000_000 else None
    dims = construir_dims()
    print(f'    solicitudes reales={args.n:,} | filas de extracción diaria={len(ext):,}', flush=True)

    res = {'parametros': dict(seed=SEED, n=args.n, periodo=[str(INICIO), str(FIN)], prob_fuente=PROB_FUENTE, ruido=RUIDO,
                              prob_reasignada=PROB_REASIGNADA, prob_gemelas=PROB_GEMELAS)}
    ora = kpis_oraculo(V)
    print('2/6 Control: carga perfecta (sin ruido) para validar las consultas SQL...', flush=True)
    hp, up = hechos_desde_verdad(V, dims)
    cp = gest.construir('sim_x1_perfecta', dims, hp, up)
    tp_, _ = exactitud_kpi(kpis_modelo(gest, cp), ora)
    cp.close()
    res['control_carga_perfecta'] = {'exactitud_global_pct': float(tp_.exactitud_pct.mean()),
                                     'por_kpi': {r.kpi: round(r.exactitud_pct, 3) for r in tp_.itertuples()}}
    for regla in ('paper', 'tolerante'):
        print(f'2/6 ETL (regla de deduplicación: {regla})...', flush=True)
        facts, bit = etl(ext, regla)
        hechos, usuarios, fa, imps = hechos_desde_etl(facts, dims)
        esquema = 'sim_x1' if regla == 'paper' else 'sim_x1_tol'
        conn = gest.construir(esquema, dims, hechos, usuarios, bit)
        print(f'3/6 E1 ({regla}): KPI en SQL vs oráculo...', flush=True)
        mod = kpis_modelo(gest, conn)
        tabla, det = exactitud_kpi(mod, ora)
        met = metricas_e1(facts, bit, V, fa, imps, hechos)
        met['exactitud_kpi_global_pct'] = float(tabla.exactitud_pct.mean())
        met['exactitud_kpi_por_kpi'] = {r.kpi: round(r.exactitud_pct, 3) for r in tabla.itertuples()}
        met['celdas_exactas_por_kpi'] = {r.kpi: round(r.celdas_exactas_pct, 2) for r in tabla.itertuples()}
        met['exactitud_wape_global_pct'] = float(tabla.exactitud_wape_pct.mean())
        met['exactitud_wape_por_kpi'] = {r.kpi: round(r.exactitud_wape_pct, 3) for r in tabla.itertuples()}
        met['globales'] = globales(hechos, V)
        res[f'e1_{regla}'] = met
        tabla.to_csv(os.path.join(args.out, f'e1_exactitud_kpi_{regla}.csv'), index=False)
        det.to_csv(os.path.join(args.out, f'e1_detalle_celdas_{regla}.csv'), index=False)
        bit.to_csv(os.path.join(args.out, f'bitacora_carga_{regla}.csv'), index=False)
        if regla == 'paper':
            excel_verificacion(os.path.join(args.out, 'verificacion_manual_E1.xlsx'), facts, V, hechos)
            print('4/6 Paquete de E3...', flush=True)
            paquete_e3(args.out, ext, V, gest, conn)
        conn.close()
    res['efecto_scd2_CERT'] = efecto_scd2(V)

    if not args.sin_e2:
        print('5/6 E2 (esto puede tardar; cada repetición en frío reinicia PostgreSQL)...', flush=True)
        escalas = [int(x) for x in args.escalas.split(',')]
        conns = [(1, 'sim_x1')]
        for esc in [e for e in escalas if e != 1]:
            print(f'   Cargando escala {esc}x ({args.n * esc:,} solicitudes)...', flush=True)
            Ve = generar_verdad(args.n * esc, np.random.default_rng(SEED + esc))
            h, u = hechos_desde_verdad(Ve, dims)
            gest.construir(f'sim_x{esc}', dims, h, u).close()
            del Ve, h, u
            conns.append((esc, f'sim_x{esc}'))
        df, resumen, glob = e2(gest, args, dims, conns)
        df.to_csv(os.path.join(args.out, 'e2_tiempos_crudos.csv'), index=False)
        resumen.to_csv(os.path.join(args.out, 'e2_resumen_por_kpi.csv'), index=False)
        glob.to_csv(os.path.join(args.out, 'e2_resumen_global.csv'), index=False)
        res['e2_global'] = glob.to_dict('records')
        if args.db == 'sqlite':
            res['e2_aviso'] = 'SQLite: solo para probar el script; NO usar estos tiempos en el paper.'

    # entorno
    env = [f'python={platform.python_version()}', f'so={platform.platform()}', f'cpu_logicas_host={os.cpu_count()}',
           f'pandas={pd.__version__}', f'numpy={np.__version__}', f'db={args.db}']
    try:
        c = gest.conectar('sim_x1')
        if args.db == 'postgres':
            env += [gest.consultar(c, 'SELECT version() AS v').v[0], 'shared_buffers=' + gest.consultar(c, 'SHOW shared_buffers').iloc[0, 0]]
        c.close()
    except Exception as e:
        env.append(f'(no se pudo leer la versión de la BD: {e})')
    open(os.path.join(args.out, 'entorno.txt'), 'w', encoding='utf-8').write('\n'.join(env))
    res['entorno'] = env
    res['segundos_totales'] = round(time.time() - t00, 1)
    json.dump(res, open(os.path.join(args.out, 'resultados.json'), 'w', encoding='utf-8'), indent=2, default=conv, ensure_ascii=False)
    escribir_resumen(res, args.out)
    print(f'\nListo en {res["segundos_totales"]} s. Envíame el archivo  {os.path.join(args.out, "resumen_para_paper.txt")}')


def escribir_resumen(res, out):
    L = ['=== RESUMEN PARA EL PAPER (copiar y pegar este archivo completo) ===', '']
    L.append('PARAMETROS: ' + json.dumps(res['parametros'], default=conv, ensure_ascii=False))
    for regla, titulo in (('paper', 'REGLA DEL PAPER (clave natural exacta)'), ('tolerante', 'REGLA MEJORADA (+-1 dia y fuentes distintas)')):
        e = res[f'e1_{regla}']
        L += ['', f'--- E1 | {titulo} ---',
              f"N={e['N']:,} | x(descartados)={e['x_descartados']:,} | y(fusionados)={e['y_fusionados']:,} | z(unicas)={e['z_unicas']:,} | N=x+y+z: {e['conciliacion_ok']}",
              f"Solicitudes reales={e['solicitudes_reales']:,} | representadas={e['solicitudes_reales_representadas']:,} | duplicados no detectados={e['duplicados_no_detectados']:,} | fusiones erroneas={e['fusiones_erroneas']:,}",
              f"Dedup precision={e['dedup_precision_pct']:.2f}% | recall={e['dedup_recall_pct']:.2f}% | tasa duplicados eliminados={e['tasa_duplicados_eliminados_pct']:.2f}%",
              f"Exactitud KPI (1 - error relativo medio por celda) global={e['exactitud_kpi_global_pct']:.2f}% | por KPI={e['exactitud_kpi_por_kpi']}",
              f"Exactitud KPI (1 - WAPE) global={e['exactitud_wape_global_pct']:.2f}% | por KPI={e['exactitud_wape_por_kpi']}",
              f"Celdas exactas (%) por KPI={e['celdas_exactas_por_kpi']}",
              f"Completitud hitos: asignacion={e['completitud_asignacion_pct']:.2f}% atencion={e['completitud_atencion_pct']:.2f}% cierre={e['completitud_cierre_pct']:.2f}% global={e['completitud_hitos_global_pct']:.2f}%",
              f"Hitos imputados (%): asignacion={e['hito_asignacion_imputado_pct']:.2f} atencion={e['hito_atencion_imputado_pct']:.2f} cierre={e['hito_cierre_imputado_pct']:.2f}",
              f"EXACTITUD POR SOLICITUD (dias_total y flag en_plazo correctos, solicitudes atendidas)={e['exactitud_por_solicitud_pct']:.2f}% | Fecha de atencion exacta={e['hito_atencion_exacto_pct']:.2f}% | dentro de 1 dia={e['hito_atencion_dentro_1dia_pct']:.2f}% | dias_total exacto={e['dias_total_exacto_pct']:.2f}% | flag en_plazo discrepante={e['flag_en_plazo_discrepante_pct']:.2f}%",
              f"Error en dias_total (modelo-verdad, dias habiles): {e['error_dias_total_habiles']}",
              f"Pendientes fantasma (atendidas en la verdad, sin hito de atencion en el modelo)={e['pendientes_fantasma']:,}",
              f"Valores globales al corte final (modelo vs verdad): {e['globales']}"]
    c = res['control_carga_perfecta']
    L += ['', f"--- CONTROL: carga perfecta sin ruido (valida SQL y calendario) --- exactitud global={c['exactitud_global_pct']:.2f}% | {c['por_kpi']}"]
    s = res['efecto_scd2_CERT']
    L += ['', f"--- SCD2 (Certificado, solicitudes antes del cambio de SLA, n={s['n']}) --- CSLA con SCD2={s['csla_con_scd2']:.2f}% | sin SCD2={s['csla_sin_scd2']:.2f}%"]
    if 'e2_global' in res:
        L += ['', '--- E2 | tiempo de respuesta por escala y cache (segundos) ---']
        for g in res['e2_global']:
            L.append(f"escala {g['escala']}x | {g['cache']}: media={g['media']:.4f} p95={g['p95']:.4f} max={g['maximo']:.4f}")
        if 'e2_aviso' in res: L.append(res['e2_aviso'])
    L += ['', '--- ENTORNO ---'] + res['entorno'] + ['', f"Tiempo total de la simulacion: {res['segundos_totales']} s"]
    open(os.path.join(out, 'resumen_para_paper.txt'), 'w', encoding='utf-8').write('\n'.join(L))


if __name__ == '__main__':
    main()
