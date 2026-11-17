-- Reportes del procedimiento "con el modelo" (E3). Pegar en Metabase (pregunta SQL nativa) o en pgAdmin/DBeaver.

-- ===== Periodo A (registradas 2025-09-15 a 2025-09-21; corte 2025-10-05) =====
-- R1
SELECT a.nombre_area AS area, COUNT(*) AS pendientes FROM hecho_solicitud h JOIN dim_area a ON a.sk_area = h.sk_area WHERE h.sk_fecha_registro BETWEEN 20250915 AND 20250921 AND (h.sk_fecha_atencion IS NULL OR h.sk_fecha_atencion > 20251005) GROUP BY a.nombre_area ORDER BY 1;
-- R2
SELECT t.nombre_tipo AS tipo, COUNT(*) AS atendidas, ROUND(AVG(h.dias_total * 1.0), 2) AS tpa_dias, ROUND(100.0 * SUM(h.en_plazo) / COUNT(*), 1) AS pct_sla FROM hecho_solicitud h JOIN dim_tipo_solicitud t ON t.sk_tipo = h.sk_tipo WHERE h.sk_fecha_registro BETWEEN 20250915 AND 20250921 AND h.sk_fecha_atencion <= 20251005 GROUP BY t.nombre_tipo ORDER BY 1;

-- ===== Periodo B (registradas 2025-10-13 a 2025-10-19; corte 2025-11-02) =====
-- R1
SELECT a.nombre_area AS area, COUNT(*) AS pendientes FROM hecho_solicitud h JOIN dim_area a ON a.sk_area = h.sk_area WHERE h.sk_fecha_registro BETWEEN 20251013 AND 20251019 AND (h.sk_fecha_atencion IS NULL OR h.sk_fecha_atencion > 20251102) GROUP BY a.nombre_area ORDER BY 1;
-- R2
SELECT t.nombre_tipo AS tipo, COUNT(*) AS atendidas, ROUND(AVG(h.dias_total * 1.0), 2) AS tpa_dias, ROUND(100.0 * SUM(h.en_plazo) / COUNT(*), 1) AS pct_sla FROM hecho_solicitud h JOIN dim_tipo_solicitud t ON t.sk_tipo = h.sk_tipo WHERE h.sk_fecha_registro BETWEEN 20251013 AND 20251019 AND h.sk_fecha_atencion <= 20251102 GROUP BY t.nombre_tipo ORDER BY 1;
