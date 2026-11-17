SET search_path TO sim_x1;
SELECT a.nombre_area AS area, COUNT(*) AS pendientes 
FROM hecho_solicitud h 
JOIN dim_area a ON a.sk_area = h.sk_area 
WHERE h.sk_fecha_registro BETWEEN 20250915 AND 20250921 
  AND (h.sk_fecha_atencion IS NULL OR h.sk_fecha_atencion > 20251005) 
GROUP BY a.nombre_area 
ORDER BY 1;
