SET search_path TO sim_x1;
SELECT t.nombre_tipo AS tipo, COUNT(*) AS atendidas, 
       ROUND(AVG(h.dias_total * 1.0), 2) AS tpa_dias, 
       ROUND(100.0 * SUM(h.en_plazo) / COUNT(*), 1) AS pct_sla 
FROM hecho_solicitud h 
JOIN dim_tipo_solicitud t ON t.sk_tipo = h.sk_tipo 
WHERE h.sk_fecha_registro BETWEEN 20250915 AND 20250921 
  AND h.sk_fecha_atencion <= 20251005 
GROUP BY t.nombre_tipo 
ORDER BY 1;
