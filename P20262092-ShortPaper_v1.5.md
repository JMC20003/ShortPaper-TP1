# Modelo dimensional para monitorear la atención de solicitudes académicas en institutos peruanos de educación superior 

*Note: Sub-titles are not captured in Xplore and should not be used 

|Joseph Vega Hoyos|||
|---|---|---|
|_Facultad de Ingeniería de Sistemas_|Josue Moreira Campos|Rubén Oscar Cerda García|
|_UPC_|<br>_Facultad de Ingeniería de Sistemas_|_Facultad de Ingeniería de Sistemas_|
|Lima, Perú|<br>_UPC_|<br>_UPC_|
|0009-0001-3138-265X|Lima, Perú|Lima, Perú|
||0009-0000-9877-9777|0000-0003-2232-9969|



**_Abstract_ —This electronic document is a “live” template and already defines the components of your paper [title, text, heads, etc.] in its style sheet.** **_*CRITICAL:  Do Not Use Symbols, Special Characters, Footnotes, or Math in Paper Title or Abstract_ . (** _Abstract_ **)** 

**_Keywords—component, formatting, style, styling, insert (_** _key words_ **_)_** 

## I. INTRODUCCIÓN 

Las instituciones de educación superior atienden un volumen creciente de solicitudes académicas —constancias, certificados, rectificaciones de matrícula, convalidaciones y reclamos— cuyo procesamiento debe monitorearse para garantizar tiempos de respuesta y calidad de servicio. Sin embargo, en los institutos privados de educación superior del Perú este proceso se sigue controlando con reportes elaborados manualmente y con datos dispersos entre sistemas académicos, correos electrónicos y hojas de cálculo mantenidas por separado en cada área administrativa. Como consecuencia, la institución no puede responder con un criterio único preguntas operativas básicas: cuántas solicitudes están pendientes, cuánto demora realmente cada tipo de trámite, qué área concentra la carga de trabajo o en qué punto del flujo se acumulan los casos. El resultado es un proceso sin indicadores clave de desempeño (KPI) consolidados y sin trazabilidad, en el que las decisiones se sustentan en información parcial o desactualizada. 

El monitoreo de este proceso no es un asunto meramente administrativo. Las demoras en la atención de solicitudes académicas afectan directamente la satisfacción del estudiante, la calidad percibida del servicio educativo y la capacidad de la institución para asignar a su personal administrativo. La evidencia reciente muestra que la disponibilidad, la vigencia y la completitud de la información en los tableros analíticos incrementan significativamente la calidad de las decisiones organizacionales [1], y que las instituciones de educación superior vienen adoptando Business Intelligence (BI) para monitorear sus procesos [2], [3]. No obstante, los institutos privados operan bajo restricciones de presupuesto, infraestructura y madurez de datos que vuelven inviables las plataformas comerciales de BI, por lo que quedan excluidos de esos beneficios. Atender esta brecha contribuye además al Objetivo de Desarrollo Sostenible 4, Educación de Calidad, al perfeccionar la administración educativa mediante el uso de tecnologías de la información. 

Una solución ingenua consistiría en conectar una herramienta de visualización directamente al sistema académico institucional. Este enfoque falla por cuatro razones. Primero, la información de una misma solicitud se encuentra distribuida en al menos tres fuentes heterogéneas con formatos distintos, sin llaves comunes y con registros duplicados, por lo que una misma solicitud puede contabilizarse varias veces. Segundo, no existe una definición estandarizada de las medidas: el tiempo de atención, la solicitud pendiente o la solicitud vencida se calculan de forma distinta en cada área y, en consecuencia, las cifras obtenidas no coinciden entre sí. Tercero, los sistemas transaccionales almacenan el estado actual de la solicitud, pero no el histórico de sus cambios de estado, lo que hace imposible calcular tiempos de atención o detectar cuellos de botella sin un modelo de hechos histórico explícito. Cuarto, los datos contienen información personal de los estudiantes, por lo que toda consolidación debe incorporar mecanismos de anonimización y seudonimización exigidos por la Ley N.° 29733. 

Las soluciones existentes abordan problemas adyacentes. Sequeira et al. [3] validan una arquitectura BI por capas que integra ingestión, un almacén de datos empresarial y tableros en una universidad europea, pero se apoya en un stack comercial (Azure Synapse Analytics y Power BI) y en un nivel de madurez tecnológica que no es representativo de los institutos peruanos. Sorour y Atkins [2] proponen un tablero de monitoreo de calidad para educación superior, aunque su contribución permanece en el plano conceptual, sin validación empírica. Hjelle et al. [1] aportan evidencia experimental sólida sobre el efecto de la visualización en la calidad de las decisiones, pero mediante maquetas simuladas y no sobre un proceso institucional real. En América Latina, Valencia Castillo et al. [4], Pincay Ponce et al. [5] y Rivera-Baena et al. [6] despliegan tableros que monitorean el rendimiento académico y la deserción, no los trámites administrativos. En consecuencia, ninguno de estos trabajos aborda los indicadores operativos de la atención de solicitudes académicas —tiempo de atención, trazabilidad de estados, cumplimiento de SLA y cuellos de botella— ni el contexto de bajos recursos de los institutos privados. Nuestro trabajo se diferencia en tres aspectos: modela el propio proceso de solicitudes mediante un modelo dimensional cuya tabla de hechos preserva el histórico de hitos de cada solicitud; acompaña el modelo con un diccionario de indicadores que fija una definición formal única para cada medida; y valida el modelo con datos reales del proceso y con el personal administrativo que lo opera. 

XXX-X-XXXX-XXXX-X/XX/$XX.00 ©20XX IEEE 

Nuestro enfoque se centra en el diseño de un modelo dimensional para el proceso de solicitudes académicas. Primero caracterizamos las fuentes de datos del proceso para determinar el grano del modelo y las reglas de correspondencia entre fuentes. Luego diseñamos un esquema estrella cuya tabla de hechos de instantánea acumulativa registra una fila por solicitud con la fecha de cada hito del flujo de atención, y cuyas dimensiones describen el tipo de solicitud, el estado, la fecha, el área responsable y el usuario seudonimizado. Sobre este modelo definimos un diccionario de ocho KPI que fija una única fórmula para cada medida. El modelo se valida con los registros históricos de un instituto peruano: se contrastan los indicadores que produce con un cálculo manual verificado, se mide el tiempo de respuesta de las consultas analíticas y se compara el tiempo de preparación de reportes frente al proceso manual previo. Nuestro enfoque presenta limitaciones: el modelo se actualiza mediante cargas diarias, por lo que los indicadores tienen una latencia de hasta 24 horas y no se admite monitoreo en tiempo real; el alcance analítico es descriptivo y de diagnóstico, sin modelos predictivos ni de aprendizaje automático; y la validación se realiza con una sola institución, lo que restringe la generalización de los resultados. 

## Nuestras principales contribuciones son las siguientes: 

- Proponemos un modelo dimensional replicable para el monitoreo de la atención de solicitudes académicas en institutos de educación superior, basado en una tabla de hechos de instantánea acumulativa que conserva la fecha de cada hito del flujo y en una dimensión de cambio lento que preserva el plazo SLA vigente en cada periodo. 

- Definimos un diccionario de ocho indicadores con fórmula, unidad y dimensiones de análisis explícitas, que estandariza entre áreas medidas como el tiempo de atención, el cumplimiento del SLA y las solicitudes vencidas. 

- Aportamos evidencia empírica sobre la exactitud de los indicadores calculados a partir del modelo frente al cálculo manual y sobre la reducción del tiempo de preparación de reportes, un aspecto escasamente documentado en el contexto peruano. 

El artículo se organiza como sigue. La sección Trabajos Relacionados revisa la literatura sobre Business Intelligence, modelado dimensional y tableros analíticos en educación superior. La sección Contribución Principal describe primero los conceptos preliminares y luego el modelo dimensional propuesto y su diccionario de indicadores. La sección Experimentos reporta el protocolo experimental, los resultados y su discusión. Finalmente, la sección Conclusiones y Perspectivas presenta las conclusiones y el trabajo futuro. 

## II. TRABAJOS RELACIONADOS 

Sequeira et al. [3] abordan la fragmentación de la información en las instituciones de educación superior (IES), donde los sistemas legados aislados, una gobernanza de datos débil y las limitadas competencias analíticas del personal impiden una toma de decisiones basada en evidencia. Su aporte es un marco de implementación de BI en seis fases (alineamiento estratégico, elicitación de requerimientos, gobernanza y calidad de datos, diseño de arquitectura y selección tecnológica, desarrollo de tableros, y evaluación con mejora continua) fundamentado en Design Science Research. Como instrumentos emplearon una revisión sistemática de 72 estudios, 24 entrevistas semiestructuradas con directivos, 

decanos y responsables de TI, sesiones de revisión con expertos y cuestionarios estandarizados de usabilidad; el marco se validó en un piloto en la Universidade de Trás-osMontes e Alto Douro (Portugal) con una arquitectura de cuatro capas (ingesta, almacén operacional, Data Warehouse empresarial y capa analítica) construida sobre Azure Synapse Analytics y Power BI. Los resultados reportan una reducción del 40 % en el tiempo de preparación de reportes frente al proceso manual, una exactitud de datos superior al 98 %, tiempos de consulta menores a dos segundos y una satisfacción promedio mayor a 4.5 sobre 5. Nuestro trabajo toma estas métricas como referencia de validación, pero se centra en el modelado dimensional de un proceso operativo concreto: la atención de solicitudes académicas. 

Wahid et al. [7] tratan el problema de gestionar datos de convenios de colaboración de distinta naturaleza en la Universitas Amikom Purwokerto (Indonesia), cuya dispersión dificultaba cumplir con los requisitos de reporte de la acreditación BAN-PT y del sistema KERMA. Su aporte es el diseño e implementación de un Data Warehouse con esquema estrella orientado al reporte administrativo, compuesto por una tabla de hechos de colaboraciones y las dimensiones de socio, actividad, documento, fecha y beneficio. Como instrumentos utilizaron Pentaho Data Integration para el proceso ETL, con énfasis en la integridad y calidad de los datos y con verificaciones de integridad y completitud posteriores a la carga, y Tableau para construir reportes, tableros interactivos y cubos OLAP. Los resultados, reportados de forma cualitativa, evidencian mejoras en la accesibilidad de los datos, en la eficiencia del reporte y en la calidad de la información, así como una reducción del esfuerzo administrativo; no obstante, el estudio no presenta métricas cuantitativas ni una evaluación formal con usuarios. Nuestra propuesta adopta el mismo patrón de modelado dimensional, pero lo aplica a las solicitudes académicas mediante una tabla de hechos de instantánea acumulativa que conserva los hitos del proceso, añade un diccionario de indicadores que estandariza cada medida y cuantifica la exactitud de esos indicadores y su efecto en la preparación de reportes. 

Sorour y Atkins [2] abordan el reto de monitorear el aseguramiento de la calidad en las IES cuando los datos provienen de grandes volúmenes y de fuentes heterogéneas, incluidas las redes sociales, en el contexto de los KPI obligatorios que exige la agencia nacional de acreditación de Arabia Saudita (NCAAA). Su aporte es el marco HF-HEQ-BI, que organiza 42 factores de adopción de BI en cinco pilares (tecnológico, organizacional, entorno, negocio y social), junto con un prototipo de tablero para el monitoreo de indicadores de calidad. Como instrumentos emplearon una revisión de literatura, entrevistas semiestructuradas con diez expertos, comunidades de práctica con especialistas en aseguramiento de la calidad de Arabia Saudita y el Reino Unido, Microsoft Power BI y la API de Twitter para el análisis de sentimiento. Como resultado, el prototipo presenta los KPI de cumplimiento, indicadores propios de la institución y el sentimiento en redes sociales, con navegación drill-down por facultad o departamento y acceso restringido según el rol del usuario; sin embargo, no fue evaluado con usuarios finales en una operación real. Nuestro trabajo comparte el enfoque de monitoreo basado en KPI, pero define los indicadores operativos del proceso de solicitudes sobre un modelo dimensional y los valida empíricamente. 

Hjelle et al. [1] parten de que, pese a la amplia adopción de la analítica, aún se conoce poco sobre cómo los tableros influyen en quienes toman decisiones y mediante qué 

mecanismos mejoran la decisión. Su aporte es un modelo que explica cómo las dimensiones de calidad de la información de un tablero (formato, vigencia, completitud y exactitud) inciden en la calidad de la decisión a través de la satisfacción con la información y de la complejidad percibida de la tarea. Como instrumentos diseñaron un experimento basado en escenarios con tableros simulados construidos en Figma y Tableau, aplicado a 524 participantes reclutados en Amazon Mechanical Turk, con escalas Likert de cinco puntos y un análisis PLS-SEM en SmartPLS. Los resultados respaldan nueve de sus diez hipótesis: el formato, la vigencia y la completitud incrementan la satisfacción con la información (β = 0.402, 0.311 y 0.341; p < 0.001), mientras que la exactitud no mostró un efecto significativo sobre ella, y el modelo explica el 47.7 % de la varianza de la calidad de la decisión. Estos hallazgos sustentan que nuestro modelo priorice la completitud de los hitos y la exactitud de los indicadores, dimensiones que se evalúan en la sección Experimentos; a diferencia de dicho estudio, nuestra evaluación se realiza sobre datos reales del proceso. 

Eyupoglu et al. [8] abordan el problema más cercano al nuestro: la atención de grandes volúmenes de solicitudes administrativas de estudiantes, que en las universidades se traduce en tiempos de respuesta lentos, orientación inconsistente y acceso desigual a la información. Su aporte es un sistema de soporte a decisiones con humano en el circuito (human-in-the-loop) que clasifica y enruta las consultas y genera borradores de respuesta que el personal revisa antes de su envío. Como instrumentos utilizaron un conjunto de 135 359 interacciones reales entre estudiantes y personal recopiladas durante 15 años, un clasificador basado en representaciones BERT y regresión logística con aprendizaje activo y SMOTE, el modelo LLaMA 2 7B ajustado con LoRA para la generación de respuestas y una API RESTful integrada al sistema de información estudiantil; el sistema se desplegó y evaluó en el portal de información de una universidad en operación. Los resultados muestran una exactitud de clasificación del 95.88 %, una aceptación del personal del 82.21 %, una reducción del 30.8 % en el tiempo de resolución, una disminución del 32.6 % en las derivaciones erróneas y un aumento de la satisfacción de 3.6 a 4.9 sobre 5. Mientras que este trabajo automatiza la resolución de cada solicitud individual, el nuestro se centra en el modelado analítico del proceso para su monitoreo agregado mediante indicadores descriptivos, sin componentes de aprendizaje automático. 

## III. CONTRIBUCIÓN PRINCIPAL 

Esta sección presenta la contribución principal del trabajo. Primero, en Contexto y Conceptos Preliminares, se definen los conceptos y las hipótesis que orientan la propuesta; luego, en Modelo Propuesto, se describen la caracterización de las fuentes, el esquema estrella, sus reglas de carga y el diccionario de indicadores. 

## _A. Contexto y Conceptos Preliminares_ 

El seguimiento de la atención de solicitudes académicas combina conceptos de gestión de procesos, de Business Intelligence y de protección de datos personales. A continuación se definen los que se emplean a lo largo del artículo. 

**_Solicitud académica_** _._ Trámite, requerimiento o consulta que un estudiante presenta ante la institución y que sigue un flujo de atención con estados, plazos y áreas responsables. Este tipo de requerimientos administrativos constituye un dominio de alto volumen en las instituciones de educación superior [8]. 

_Business Intelligence._ Conjunto de tecnologías, procesos y herramientas que integran datos de múltiples fuentes y los transforman en información para apoyar la toma de decisiones basada en evidencia [11]. 

_Data Warehouse._ Repositorio centralizado, integrado e histórico que almacena datos provenientes de diversas fuentes y que está optimizado para consultas analíticas, no para el procesamiento transaccional [9]. 

_Proceso ETL._ Secuencia de extracción de datos desde los sistemas fuente, transformación (limpieza, estandarización, deduplicación e integración) y carga en el Data Warehouse [9]. 

_Modelo dimensional._ Técnica de diseño que organiza los datos en tablas de hechos, que contienen las medidas numéricas del proceso a un nivel de detalle (grano) definido, y en tablas de dimensiones, que aportan el contexto descriptivo para filtrar y agrupar esas medidas. Cuando las dimensiones se conectan directamente con una tabla de hechos central, el modelo recibe el nombre de esquema estrella [9]. 

_Tabla de hechos de instantánea acumulativa._ Tabla de hechos cuyo grano es una fila por cada instancia de un proceso con inicio y fin definidos; la fila contiene una clave de fecha por cada hito del proceso y se actualiza a medida que la instancia avanza [9]. 

_Indicador clave de desempeño, KPI._ Métrica cuantificable, con fórmula y periodicidad definidas, que permite evaluar el desempeño de un proceso frente a sus objetivos. Su uso para monitorear y optimizar procesos educativos está documentado en la literatura [12]. 

_Acuerdo de nivel de servicio, SLA._ Plazo máximo, expresado en días hábiles, que la institución establece para atender cada tipo de solicitud académica. 

_Seudonimización y anonimización._ La seudonimización reemplaza los identificadores directos de una persona por códigos sustitutos que permiten mantener la trazabilidad operativa sin exponer su identidad; la anonimización elimina o transforma esos identificadores de modo que la persona no pueda ser reconocida en los reportes agregados. Ambos mecanismos responden a las exigencias de la Ley N.° 29733, Ley de Protección de Datos Personales [13]. 

El desarrollo analítico se organiza según CRISP-DM [10], adaptado a proyectos de BI: la comprensión del negocio y de los datos corresponde a la caracterización del proceso y de sus fuentes; la preparación de los datos, a las reglas de carga del modelo; el modelado, al diseño dimensional y al diccionario de KPI; y la evaluación, a la validación descrita en la sección Experimentos. 

A partir de estos conceptos se formulan dos hipótesis. _H1:_ la consolidación de las fuentes en un modelo dimensional con indicadores estandarizados reduce en al menos 30 % el tiempo de preparación de los reportes de seguimiento respecto del procedimiento manual. _H2:_ los KPI calculados a partir del modelo dimensional coinciden con el cálculo manual verificado sobre una muestra de solicitudes, con una exactitud de al menos 98 %. 

## _B. Modelo Propuesto_ 

El modelo propuesto se construye en cuatro pasos: la caracterización de las fuentes de datos del proceso, el diseño del esquema estrella, la definición de las reglas de carga que preservan su grano y la definición del diccionario de indicadores. El modelo se implementa en PostgreSQL, un 

gestor de base de datos de código abierto, por lo que no requiere licencias de plataformas comerciales de BI. 

## _1) Caracterización de las fuentes de datos_ 

El primer paso consiste en identificar dónde se registra cada solicitud y con qué estructura. Mediante el análisis documental del proceso y entrevistas semiestructuradas con el personal que lo opera se caracterizan al menos tres fuentes: el sistema académico institucional, los registros de correo electrónico y mesa de partes, y las hojas de cálculo que cada área mantiene por separado. Para cada fuente se documentan su estructura, formato, frecuencia de actualización y volumen estimado, así como los campos que permiten reconstruir la historia de una solicitud: identificador, tipo de trámite, fechas de cada estado y área responsable. Este inventario determina el grano del modelo y las reglas de correspondencia entre fuentes que se aplican en su carga. 

## _2) Modelo dimensional_ 

La Fig. 1 presenta el esquema estrella del modelo. La tabla HECHO_SOLICITUD es una instantánea acumulativa (véase Contexto y Conceptos Preliminares) con grano de una fila por solicitud; contiene una clave por cada dimensión y cuatro claves de fecha que corresponden a los hitos de registro, asignación, atención y cierre. De este modo, DIM_FECHA cumple varios roles y, al indicar si cada día es hábil, permite medir los plazos en días hábiles. Las medidas almacenadas son los días transcurridos entre hitos (espera hasta la asignación, tiempo en proceso y tiempo total de     atención), dos indicadores binarios (en plazo y vencida) y un contador. Las cinco dimensiones describen el tipo de solicitud, el estado actual, el área responsable, la fecha y el usuario seudonimizado. DIM_TIPO_SOLICITUD se gestiona como dimensión de cambio lento de tipo 2, de modo que cada solicitud se evalúa contra el plazo SLA vigente en la fecha en que fue registrada. Este diseño resuelve el tercer problema identificado en la Introducción: aunque los sistemas fuente solo conservan el estado actual, la tabla de hechos preserva las fechas de todos los hitos. 



<!-- Start of picture text -->
0 sud<br>vigplan sladesdeis hasta oypeal<br>HIECHO_SOLICITUD<br>Ske (PK sche, faa (0<br>sda abil<br>kauario PX)<br>ro pograna<br><!-- End of picture text -->

Fig. 1. Esquema estrella del modelo dimensional de solicitudes académicas. 

## _3) Reglas de carga del modelo_ 



<!-- Start of picture text -->
Sistema Correo y _ Hojas de Bitécora<br>académico mesa de partes cAlculo por area de carga<br>(@ Limpieza u<br>Descarta restos sin denificadoro sin [ataprt eaasy<br>fecha de registro; normaliza fechas y texto<br>(ii) Estandarizacion H<br>Asigna tip de trmite estado y rea a i<br>os catélogos tinicos de las dimensiones A<br>(iii) Deduplicacion u<br>fas<br>‘fecha de regio na fila por slid<br>(iv) Seudonimizacion H<br>Sustituye cédigo y datos personales por un H<br>hash con sal, almacenado en DIM_USUARIO A<br>Inferencia de hitos H<br>Sia fuente no regia a fecha del cambio, :<br>Carga en el esquema estrella<br>fils<br><!-- End of picture text -->

Fig. 2. Flujo de la carga diaria del modelo y su bitácora de carga. 

La Fig. 2 resume el flujo con el que se actualiza el modelo: una carga diaria en modo batch que aplica cuatro reglas para garantizar su grano y su consistencia: (i) limpieza, que descarta los registros sin identificador o sin fecha de registro y normaliza los formatos de fecha y texto; (ii) estandarización, que asigna los valores libres de tipo de trámite, estado y área a los catálogos únicos que conforman las dimensiones, acordados con los usuarios; (iii) deduplicación, que reconoce una misma solicitud presente en varias fuentes mediante una clave natural compuesta por el código del estudiante, el tipo de trámite y la fecha de registro, y conserva una sola fila en HECHO_SOLICITUD que reúne los hitos de todas las fuentes; y (iv) seudonimización, que sustituye el código y los datos personales del estudiante por un identificador generado con una función hash con sal, el cual se almacena en DIM_USUARIO. Cuando una fuente no registra la fecha de un cambio de estado, la fecha del hito se infiere comparando el estado observado en dos cargas diarias consecutivas. Cada carga registra el número de filas leídas, descartadas, fusionadas y cargadas, información que se utiliza en la evaluación de la fidelidad del modelo (E1) descrita en la sección Experimentos. 

## _4) Diccionario de indicadores_ 

Sobre el modelo dimensional se define un diccionario de ocho KPI (Tabla I), cada uno con su fórmula, su unidad y las dimensiones por las que puede analizarse. <mark>El diccionario resuelve el segundo problema identificado en la Introducción</mark> , porque fija una única definición de cada medida para todas las áreas. Sea A el conjunto de solicitudes atendidas en el periodo, P el conjunto de solicitudes pendientes a la fecha de corte t, s(i) el plazo SLA del tipo de la solicitud i y d(x, y) el número de días hábiles entre dos fechas. Los tres indicadores centrales se calculan como: 

TPA = (1 / |A|) · Σ i∈A  d(r(i), a(i)) (1) 

CSLA = |{ i  A : d(r(i), a(i)) ≤ s(i) }| / |A| × 100∈ 



V = |{ i  P : d(r(i), t) > s(i) }|∈ (3) 

donde r(i) y a(i) son las fechas de registro y de atención de la solicitud i, TPA es el tiempo promedio de atención, CSLA el porcentaje de cumplimiento del SLA y V el número de solicitudes vencidas. 

||TABLA I.<br><br>|DICCIONARIO DE INDICADORES(K<br>|PI)<br>|
|---|---|---|---|
|**Cód.**|**Indicador**|**Definición**|**Unidad**|
|K1|Volumen de<br>solicitudes|Solicitudes registradas en el<br>periodo, por tipo de trámite|solicitudes|
|K2|Solicitudes por<br>estado|Solicitudes en cada estado a la<br>fecha de corte|solicitudes|
|K3|Solicitudes<br>pendientes|Solicitudes sin estado final a la<br>fecha de corte (|P|)|solicitudes|
|K4|Tiempo promedio<br>de atención|Ecuación (1)|días hábiles|
|K5|Cumplimiento de<br>SLA|Ecuación (2)|%|
|K6|Solicitudes<br>vencidas|Ecuación (3)|solicitudes|
|K7|Carga por área|Solicitudes pendientes<br>asignadas a cada área|solicitudes|
|||Promedio de días entre hitos||
|K8|Tiempo por etapa|consecutivos; identifica cuellos<br>de botella|días hábiles|



## IV. EXPERIMENTOS 

Esta sección describe el protocolo con el que se evalúa el modelo propuesto, reporta los resultados obtenidos y los discute frente a los trabajos relacionados. 

## _A. Protocolo Experimental_ 

## _1) Configuración del entorno_ 

El modelo se implementa en PostgreSQL <mark>[versión]</mark> , en un servidor de demostración con 2 vCPU, 4 GB de RAM y 200 GB de almacenamiento SSD. Los scripts de creación del esquema estrella, de carga y de cálculo de los indicadores están disponibles en <mark>[URL del repositorio]</mark> . 

## _2) Datos_ 

Se utilizan los registros históricos de solicitudes académicas de un instituto privado de educación superior de <mark>[ciudad]</mark> , correspondientes al periodo <mark>[mes/año a mes/año]</mark> . Los datos provienen de las tres fuentes caracterizadas en Caracterización de las fuentes de datos y suman 1200 registros antes de la carga. Los datos se seudonimizan antes de salir de la institución y su uso se autoriza mediante <mark>[acuerdo o consentimiento institucional]</mark> , en cumplimiento de la Ley N.° 29733 [13]. 

## _3) Diseño de la evaluación_ 

La evaluación comprende tres experimentos, resumidos en la Tabla II, orientados a verificar la fidelidad del modelo, el rendimiento de las consultas analíticas sobre él y su efecto en la preparación de reportes. 

_E1. Fidelidad del modelo (H2)._ Se contrasta el número de solicitudes cargadas en el Data Warehouse con el conteo verificado manualmente en cada fuente para una muestra de <mark>[n]</mark> solicitudes, y se calculan la tasa de duplicados eliminados, la completitud de los hitos y la exactitud de los KPI frente al cálculo manual. 

_E2. Rendimiento de las consultas._ Se mide el tiempo de respuesta de las consultas que calculan los KPI de la Tabla I 

sobre el esquema estrella en 30 repeticiones, con caché fría y caliente. El umbral es de menos de 2 s, establecido en los requerimientos no funcionales. 

_E3. Eficiencia en la preparación de reportes (H1)._ Al menos cinco usuarios administrativos preparan <mark>[m]</mark> reportes de seguimiento habituales, primero con el procedimiento manual vigente (línea base) y luego a partir de los indicadores calculados sobre el modelo; para reducir el efecto de aprendizaje, cada condición utiliza datos de un periodo distinto. Se compara el tiempo medio por reporte y se calcula la reducción porcentual; H1 se considera confirmada si la reducción es de al menos 30 %. 

### TABLA II. DISEÑO DE LA EVALUACIÓN 

|**Exp.**|**Métrica**|**Instrumento**|**Meta**|
|---|---|---|---|
|E1|Exactitud de KPI,<br>duplicados eliminados y<br>completitud de hitos|Consultas de control y<br>cálculo manual sobre<br>una muestra|Exactitud ≥<br>98 %|
|E2|Tiempo de respuesta de<br>las consultas de KPI|Registro de tiempos en<br>30 repeticiones|< 2 s|
|E3|Reducción del tiempo de<br>preparación de reportes|Cronometraje antes y<br>después|≥ 30 %|



## _B. Resultados_ 

La Tabla III resume los resultados de los tres experimentos. 

_Fidelidad del modelo (E1)._ De los 1200 registros extraídos de las tres fuentes, la carga descartó 0 por datos incompletos y fusionó 200 duplicados, con lo que se obtuvieron 1000 solicitudes únicas en la tabla de hechos. La conciliación con la muestra verificada manualmente arrojó una exactitud de <mark>[x]</mark> % en los KPI y una completitud de hitos de 70 %. 

_Rendimiento (E2)._ El tiempo medio de respuesta de las consultas fue de <mark>[x]</mark> s con caché fría y de <mark>[x]</mark> s con caché caliente. 

_Eficiencia (E3)._ El tiempo medio de preparación de un reporte pasó de <mark>[x]</mark> min con el procedimiento manual a <mark>[x]</mark> min a partir del modelo, lo que representa una reducción de <mark>[x]</mark> %. 

### TABLA III. RESULTADOS DE LA EVALUACIÓN 

|**Exp.**|**Métrica**|**Meta**|**Resultado**|
|---|---|---|---|
|E1|Exactitud de los KPI|≥ 98 %|[   ]|
|E1|Duplicados eliminados|—|200 (16,7 %)|
|E2|Respuesta media de consultas|<2 s|[   ]|
|E3|Reducción del tiempo de<br>reportes|≥ 30 %|[   ]|



## _C. Discusión_ 

Los resultados de E3 <mark>[confirman / no confirman]</mark> la hipótesis H1: la reducción de <mark>[x]</mark> % en el tiempo de preparación de reportes <mark>[supera / no alcanza]</mark> la meta de 30 % y es <mark>[comparable / inferior / superior]</mark> al 40 % que reportan Sequeira et al. [3] con una plataforma comercial. Del mismo modo, la exactitud de <mark>[x]</mark> % de los KPI obtenida en E1 <mark>[supera / no alcanza]</mark> el umbral planteado en H2 y se ubica <mark>[por encima / por debajo]</mark> de la exactitud superior al 98 % reportada en [3]. <mark>[Interpretar aquí la causa principal de las diferencias observadas.]</mark> 

A diferencia de Wahid et al. [7] y de Sorour y Atkins [2], cuyos resultados son cualitativos o se limitan a un prototipo, esta evaluación cuantifica la fidelidad del modelo y su efecto en la preparación de reportes con datos reales. En cuanto al proceso de solicitudes, Eyupoglu et al. [8] reducen el tiempo de resolución en 30.8 % automatizando la respuesta a cada solicitud. Ambos enfoques son complementarios: el modelo 

aquí propuesto permite ubicar en qué área y en qué etapa se generan las demoras (indicador K8), información que un sistema centrado en la resolución individual no ofrece. 

Los resultados deben interpretarse considerando tres limitaciones. La validación se realizó en una sola institución y con un número reducido de usuarios, lo que restringe su generalización; la latencia de hasta 24 horas de la carga diaria impide el monitoreo en tiempo real; y la inferencia de las fechas de hito a partir de cargas diarias introduce un error de hasta un día en los tiempos de atención cuando la fuente no registra la fecha del cambio de estado. 

## V. CONCLUSIONES Y PERSPECTIVAS 

## _A. Conclusiones_ 

En este trabajo se propuso un modelo dimensional para monitorear la atención de solicitudes académicas en institutos de educación superior peruanos, un proceso que se controla con reportes manuales y datos dispersos. El modelo consolida tres fuentes heterogéneas bajo un grano único de una fila por solicitud, mediante reglas de limpieza, estandarización, deduplicación y seudonimización; emplea una tabla de hechos de instantánea acumulativa que conserva los hitos de cada solicitud y una dimensión de cambio lento que preserva el plazo SLA vigente; y sustenta un diccionario de ocho KPI con una definición única para todas las áreas. 

La evaluación mostró una exactitud de <mark>[x]</mark> % en los KPI calculados a partir del modelo frente al cálculo manual y una reducción de <mark>[x]</mark> % en el tiempo de preparación de reportes, por lo que las hipótesis H1 y H2 <mark>[se confirman / se confirman parcialmente]</mark> . Estos resultados indican que un instituto con recursos limitados puede obtener indicadores consolidados y trazables de su proceso de solicitudes a partir de un modelo dimensional implementado con software de código abierto, sin recurrir a plataformas comerciales de BI. 

Un segundo hallazgo es que la utilidad de los indicadores depende de la calidad con que se carga el modelo: <mark>[resumir lo observado en E1, por ejemplo, qué problemas de datos fueron más frecuentes y qué hitos presentaron menor completitud]</mark> . 

## _B. Perspectivas_ 

Como trabajo futuro se plantean tres líneas. Primero, validar el modelo en varias instituciones para evaluar su replicabilidad y construir una línea base comparable del proceso en el sector. Segundo, reducir la latencia de los indicadores mediante la captura de cambios de datos (CDC), de modo que la tabla de hechos se actualice casi en tiempo real. Tercero, extender el modelo hacia la predicción del 

incumplimiento de plazos y la clasificación automática de solicitudes, en la línea de los sistemas con humano en el circuito propuestos por Eyupoglu et al. [8]. 

## REFERENCIAS 

- [1] S. Hjelle, P. Mikalef, N. Altwaijry, and V. Parida, “Organizational decision making and analytics: An experimental study on dashboard visualizations,” _Information & Management_ , vol. 61, no. 6, Art. no. 104011, 2024, doi: 10.1016/j.im.2024.104011. 

- [2] A. Sorour and A. S. Atkins, “Big data challenge for monitoring quality in higher education institutions using business intelligence dashboards,” _Journal of Electronic Science and Technology_ , vol. 22, no. 1, Art. no. 100233, 2024, doi: 10.1016/j.jnlest.2024.100233. 

- [3] R. Sequeira, A. Reis, F. Branco, and P. Alves, “From roadmap to ecosystem: A comprehensive framework for implementing business intelligence in higher education institutions,” _Systems_ , vol. 13, no. 11, Art. no. 1032, 2025, doi: 10.3390/systems13111032. 

- [4] N. Valencia Castillo, E. H. Collahuazo Romero, N. S. Panta Vilela, A. Malave, and G. Soledispa, “Evaluación del rendimiento académico, utilizando herramientas de business intelligence: un enfoque basado en datos,” _LATAM Revista Latinoamericana de Ciencias Sociales y Humanidades_ , vol. 5, no. 6, pp. 1249–1265, 2024, doi: 10.56712/latam.v5i6.3080. 

- [5] F. B. Pincay Ponce, O. S. Baque Pinargote, C. R. Caicedo Plúa, and J. P. Paladines Morán, “Dashboard para el control y seguimiento académico de los estudiantes en la educación superior,” _Revista Científica de Innovación Educativa y Sociedad Actual ALCON_ , vol. 4, no. 5, pp. 1–13, 2024, doi: 10.62305/alcon.v4i5.272. 

- [6] O. D. Rivera-Baena, C. E. Patiño-Rodríguez, O. C. Úsuga-Manco, and F. Hernández-Barajas, “ADHE: A tool to characterize higher education dropout phenomenon,” _Revista Facultad de Ingeniería Universidad de Antioquia_ , no. 111, pp. 64–75, 2024, doi: 10.17533/udea.redin.20230519. 

- [7] A. M. Wahid, L. Afuan, and F. S. Utomo, “Enhancing collaboration data management through data warehouse design: Meeting BAN-PT accreditation and KERMA reporting requirements in higher education,” _Jurnal Teknik Informatika (JUTIF)_ , vol. 5, no. 6, pp. 1517 –1527, 2024, doi: 10.52436/1.jutif.2024.5.6.1747. 

- [8] A. Eyupoglu, K. Jazayeri, and E. Çelebi, “Knowledge-driven humanin-the-loop decision support for student services using active learning and large language models,” _Applied Sciences_ , vol. 16, no. 4, Art. no. 1802, 2026, doi: 10.3390/app16041802. 

- [9] R. Kimball and M. Ross, _The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling_ , 3rd ed. Indianapolis, IN, USA: Wiley, 2013. 

- [10] P. Chapman et al., “CRISP-DM 1.0: Step-by-step data mining guide,” SPSS Inc., 2000. 

- [11] T. H. Davenport, J. G. Harris, and R. Morison, _Analytics at Work: Smarter Decisions, Better Results_ . Boston, MA, USA: Harvard Business Press, 2010. 

- [12] S. Val and A. Quintas, “Key performance indicators for optimizing academic performance and course design in online educational platforms,” _Cogent Education_ , vol. 12, no. 1, Art. no. 2529420, 2025, doi: 10.1080/2331186X.2025.2529420. 

- [13] Congreso de la República del Perú, “Ley N.° 29733, Ley de Protección de Datos Personales,” _Diario Oficial El Peruano_ , Lima, Perú, 2011. 

