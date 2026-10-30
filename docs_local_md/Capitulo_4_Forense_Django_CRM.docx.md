Universidad Peruana Cayetano Heredia

Facultad de Ingeniería Informática

Temas Avanzados de Seguridad Informática

# **Análisis forense digital para la reconstrucción de incidentes simulados en Django CRM mediante preparación y preservación de evidencias**

Integrantes

Camilo Sebastián Silva Cuzqui

Jose Nilson Cueva Ramos

Bruno Paolo Gavidia Crovetto

Leily Marlith Llanos Angeles

Profesor

Lider Jen Cotrina Castañeda

Lima, Perú

4 de octubre de 2026

# **Contenido**

Introducción

Capítulo I. Problemática y planificación

Capítulo II. Marco teórico científico

Capítulo III. Diseño metodológico y arquitectura

Capítulo IV. Implementación y gestión del proyecto

Referencias

# **Introducción**

Este proyecto propone preparar Django-CRM para investigar modificaciones y eliminaciones indebidas de registros de clientes en un laboratorio con datos ficticios. El sistema conservará eventos con contexto de cuenta, tiempo, origen, correlación y estados anterior y posterior. Tras simular el incidente, se adquirirán registros persistentes de Django, Docker y MySQL, se calculará SHA-256, se documentará la cadena de custodia y se analizarán copias verificadas para construir una línea de tiempo y un informe forense.

La evaluación comparará el mismo guion de operaciones en una instalación original y en otra instrumentada, con estados iniciales equivalentes. La fuente principal serán los eventos de auditoría incorporados a la aplicación; las demás fuentes servirán para contraste según su disponibilidad. La adquisición de memoria RAM queda fuera del procedimiento experimental; LiME se presenta únicamente como referencia en el marco teórico.

# **Capítulo I. Problemática y planificación**

## **1.1 Contexto**

Los sistemas de información permiten que usuarios autenticados consulten, registren, modifiquen y eliminen datos como parte de sus actividades habituales. En un sistema de gestión de clientes, estas operaciones afectan información de contacto y otros datos utilizados por la organización. Cuando ocurre una alteración indebida o una eliminación, conocer únicamente el estado final de la base de datos no permite explicar de forma completa qué sucedió, qué información existía antes ni cómo se relacionan las acciones realizadas durante una sesión.

La disponibilidad de registros para investigar incidentes constituye una dificultad observada en entornos reales. El Sophos Active Adversary Report 2025, elaborado a partir de 413 casos atendidos durante 2024 por sus equipos de respuesta a incidentes y de detección y respuesta gestionadas, identificó que faltaban registros en el 47 % de los casos analizados. El informe señala que la falta de registros disponibles limita la capacidad de los investigadores para determinar las causas de los ataques (Shier et al., 2025). Aunque estos resultados corresponden a los casos estudiados por Sophos y no específicamente a sistemas CRM, evidencian la importancia de disponer de registros que permitan examinar lo ocurrido después de un incidente.

El análisis forense digital aborda esta necesidad mediante la identificación, adquisición, preservación, examen, análisis y documentación de evidencias. Su propósito es reconstruir los hechos a partir de información verificable y explicar el fundamento y las limitaciones de los hallazgos. La auditoría y la trazabilidad aportan registros de actividad; la preparación forense permite disponer de evidencias útiles antes de un incidente. Estos mecanismos apoyan la investigación posterior, pero la captura de eventos por sí sola no constituye un análisis forense completo.

En este sentido, la guía Best practices for event logging and threat detection, publicada por el Australian Signals Directorate’s Australian Cyber Security Centre en colaboración con CISA, FBI, NSA y otros organismos, advierte que los periodos predeterminados de conservación de registros suelen ser insuficientes para apoyar las investigaciones de incidentes. Asimismo, recomienda que los eventos incluyan, cuando corresponda, marcas de tiempo precisas, identificadores de usuario, direcciones IP e identificadores de sesión o transacción, junto con medidas para proteger su integridad (ASD’s ACSC et al., 2024). Estas recomendaciones respaldan la necesidad de planificar tanto el contenido de los registros como su conservación y disponibilidad para el análisis posterior.

El proyecto utilizará Django-CRM, disponible en el repositorio https\://github.com/ChakerChourouk/Django-CRM, como escenario experimental. Esta aplicación de código abierto permite autenticar usuarios y gestionar registros de clientes mediante una interfaz web, un panel administrativo y una API. Para el laboratorio se empleará su despliegue local con Docker y MySQL. El sistema cuenta con mensajes básicos de actividad y con el historial propio del panel de Django; sin embargo, estas fuentes no equivalen a un historial integrado de todas las operaciones ni conservan por sí solas los valores anteriores y posteriores de cada cambio realizado desde la interfaz principal.

La simulación se desarrollará con cuentas y clientes ficticios en un entorno controlado. Se representará el caso de un empleado que, utilizando una cuenta con permisos operativos, modifica datos de contacto sin una solicitud que lo justifique, realiza cambios sucesivos y elimina otro registro sin autorización del negocio. Dado que la aplicación permite estas acciones a usuarios autenticados, el incidente corresponderá al uso indebido de permisos legítimos. Las reglas del escenario permitirán distinguir las operaciones esperadas de aquellas consideradas indebidas; no se asumirá que toda modificación constituye un incidente.

Sobre este escenario se incorporarán mecanismos de preparación forense para capturar y conservar el contexto de los eventos relevantes. Posteriormente se aplicará un procedimiento de adquisición y preservación de evidencias, verificación de integridad mediante SHA-256, documentación de la cadena de custodia, correlación y construcción de una línea de tiempo. El análisis se realizará sobre copias de trabajo y concluirá con un informe que vincule los hallazgos con sus evidencias. Así, la aplicación y su despliegue servirán como soporte del experimento, mientras que el aporte principal será aplicar y evaluar un proceso de análisis forense digital para reconstruir los incidentes simulados.

## **1.2 Descripción del problema**

El problema central es la insuficiencia de evidencia contextualizada y preservada para reconstruir de manera repetible determinados incidentes en Django-CRM. En la interfaz principal, los mensajes de actividad identifican algunas operaciones y la cuenta que las ejecuta, pero no conservan el contenido completo anterior y posterior de cada registro. Una modificación sustituye los valores almacenados y una eliminación retira el registro de la base de datos operativa. El historial del panel administrativo corresponde a acciones efectuadas desde ese panel y no representa por sí mismo toda la actividad de la interfaz web o de la API. Estas limitaciones dificultan determinar qué campos cambiaron, recuperar el estado previo y relacionar las acciones con una sesión, un origen de red y una secuencia temporal.

Además de capturar la información faltante, se requiere un procedimiento definido para adquirirla, preservar sus originales, registrar su manejo y justificar las conclusiones del análisis. Para estudiar esta necesidad se comparará un mismo escenario con los registros originales del CRM y con los mecanismos de preparación forense incorporados, partiendo de datos iniciales equivalentes. Se recogerán la cuenta, fecha y hora, dirección IP, identificador de correlación de sesión, acción, registro afectado y estados anterior y posterior cuando corresponda. Las evidencias se examinarán sobre copias y se correlacionarán en una línea de tiempo para determinar qué acciones pueden reconstruirse y cuáles siguen sin respaldo suficiente. Los hashes permitirán verificar cambios respecto de la evidencia adquirida, sin demostrar por sí solos la veracidad de su contenido; asimismo, identificar una cuenta no bastará para atribuir la acción a una persona. El resultado se documentará en un informe forense con evidencias, hallazgos y limitaciones.

### **Análisis de causa raíz mediante cinco porqués**

Para precisar la causa del problema se aplica la técnica de los cinco porqués al escenario de modificación y eliminación indebida de registros de clientes:

1. **¿Por qué resulta difícil reconstruir una modificación o eliminación indebida de un cliente?** Porque el sistema sobrescribe los valores al modificar y retira el registro al eliminar, de modo que queda principalmente el estado final.  
2. **¿Por qué los registros existentes no permiten completar esa reconstrucción?** Porque los mensajes de actividad no guardan los valores anteriores y posteriores ni contexto como IP y sesión; el historial administrativo cubre las acciones del panel de Django.  
3. **¿Por qué disponer de mensajes de actividad e historial administrativo no resuelve el problema?** Porque estas fuentes son parciales y dispersas y no ofrecen por sí solas una secuencia correlacionada para todas las vías de operación.  
4. **¿Por qué la recolección de eventos necesita un procedimiento forense?** Porque los registros pueden alterarse, perderse o interpretarse erróneamente. Su adquisición, verificación de integridad, custodia y examen sobre copias deben quedar documentados.  
5. **¿Cuál es la causa raíz?** Django-CRM no fue concebido para capturar de forma sistemática todo el contexto requerido ni dispone de un procedimiento definido para adquirir, preservar y analizar sus registros como evidencia.

## **1.3 Objetivos del proyecto**

### **1.3.1 Objetivo general**

Aplicar un proceso de análisis forense digital, apoyado en mecanismos de preparación forense, para reconstruir de manera verificable y repetible incidentes de modificación y eliminación indebida de registros de clientes en Django-CRM dentro de un entorno controlado.

### **1.3.2 Objetivos específicos**

OE1: Configurar el entorno experimental y el escenario del incidente. Desplegar Django-CRM con Docker y MySQL, cargarlo con cuentas y clientes ficticios, y definir reglas que distingan las operaciones legítimas de las indebidas.

OE2: Implementar la preparación forense. Incorporar mecanismos que capturen y conserven el contexto de las operaciones realizadas desde la interfaz web, el panel administrativo y la API: cuenta, fecha y hora, dirección IP, identificador de correlación de sesión, acción, registro afectado y estados anterior y posterior.

OE3: Establecer el procedimiento de adquisición y preservación. Definir cómo se adquieren las evidencias, cómo se verifica su integridad mediante SHA-256 y cómo se documenta su cadena de custodia.

OE4: Analizar y reconstruir los hechos. Examinar y correlacionar las evidencias sobre copias de trabajo para construir una línea de tiempo de los incidentes, y documentar los hallazgos, sus evidencias y sus limitaciones en un informe forense.

OE5: Evaluar la capacidad de reconstrucción. Comparar qué acciones pueden reconstruirse con los registros originales del CRM y cuáles con los mecanismos incorporados, partiendo de datos iniciales equivalentes.

## **1.4 Justificación**

### **Técnica**

La justificación técnica del proyecto responde a que los sistemas de información, en su configuración original, sobreescriben los valores durante una modificación y retiran la información al eliminar un registro, dejando únicamente el estado final en la base de datos. En el caso específico de Django-CRM, los mensajes de actividad y el historial del panel administrativo son insuficientes porque no conservan el estado anterior y posterior de los registros, ni capturan datos de contexto técnico fundamentales como la dirección IP o el identificador de sesión. Por ello, resulta necesario incorporar mecanismos de preparación forense que capturen sistemáticamente esta información faltante. Además, es imperativo establecer un procedimiento estructurado para la adquisición y preservación de estas evidencias mediante copias de trabajo y validación criptográfica con algoritmos SHA-256, operando dentro de un entorno controlado desplegado con Docker y MySQL.

### **Operativa**

A nivel operativo, las organizaciones dependen de los sistemas de gestión para registrar, modificar y consultar información de contacto como parte de sus actividades diarias habituales. Cuando un usuario emplea sus permisos operativos legítimos para alterar o eliminar datos sin autorización, los registros nativos no permiten a la administración reconstruir de manera confiable la secuencia de eventos que componen el incidente. La implementación de este proyecto proporciona a la organización una capacidad operativa para auditar y correlacionar la actividad de los usuarios a nivel de sesión. Esto permite separar las operaciones esperadas del negocio de aquellas consideradas indebidas mediante reglas claras, facilitando una investigación interna repetible y la generación de una línea de tiempo verificable.

### **Socioeconómica**

En el aspecto socioeconómico, la información y gestión de clientes alojada en el CRM representa un activo crítico para las operaciones de cualquier organización. La alteración indebida o eliminación de estos registros sin justificación puede generar un impacto negativo directo en el negocio. Al implementar mecanismos de preparación forense, la organización puede disponer de evidencias útiles antes de que ocurra un incidente y fundamentar sus investigaciones en un informe con cadena de custodia sólida. Esto permite proteger los activos digitales de la empresa ante amenazas internas y favorece decisiones basadas en hechos documentados después de un incidente.

## **1.5 Alcances y limitaciones**

### **1.5.1 Alcances**

* El escenario experimental utilizará la aplicación web de código abierto Django-CRM, obtenida desde su repositorio oficial en GitHub.

* El despliegue tecnológico de la aplicación y la base de datos se realizará en un entorno local controlado empleando contenedores de Docker y MySQL.

* Se incorporarán mecanismos de preparación forense que capturarán sistemáticamente la cuenta, fecha, hora, dirección IP, correlación de sesión y los estados anterior y posterior de los registros.

* El monitoreo y recolección de evidencias abarcará las acciones ejecutadas desde la interfaz web principal, el panel administrativo y la API del sistema.

* El proyecto desarrollará un procedimiento forense integral que incluirá la adquisición de datos, verificación de integridad con SHA-256, documentación de la cadena de custodia y análisis estructurado sobre copias de trabajo.

La adquisición experimental se concentrará en eventos de auditoría de Django-CRM, el historial del administrador cuando corresponda, los registros disponibles de Docker y una exportación lógica de MySQL. El registro binario de MySQL se empleará como contraste sólo si se habilita previamente y se conserva durante la prueba. Se construirá una línea de tiempo y se comparará la reconstrucción del sistema original con la del sistema instrumentado.

### **1.5.2 Limitaciones**

* La simulación del incidente se restringirá a un entorno completamente controlado con cuentas y clientes ficticios, sin operar sobre datos comerciales reales ni entornos en producción.

* La identificación de una cuenta de usuario específica en los registros del sistema no será evidencia suficiente por sí sola para atribuir la acción física de manera concluyente a una persona.

* Los algoritmos de hash utilizados certificarán que no existieron cambios respecto a la evidencia original adquirida, pero no demostrarán por sí solos la veracidad o exactitud del contenido de la base de datos.

* El análisis no asumirá que toda modificación dentro del CRM es un incidente malicioso; dependerá estrictamente de las reglas del escenario definidas para distinguir las acciones esperadas de las indebidas.

* La evaluación y resultados se limitarán a comparar la capacidad de reconstrucción entre los registros nativos originales del CRM y los nuevos mecanismos forenses incorporados, a partir de estados de datos iniciales equivalentes.

  No se adquirirán ni analizarán imágenes de RAM. LiME y las demás herramientas de memoria se mencionan solo en el marco teórico. Tampoco se plantea adquirir una imagen bit a bit del disco, examinar redo logs de InnoDB ni probar un almacén WORM o un esquema de registro criptográficamente resistente a la manipulación. El hash verifica la integridad desde la adquisición, no la autenticidad previa del dato. Las operaciones por SQL directo ajenas a los flujos instrumentados quedan fuera de la cobertura de usuario y sesión.

## **1.6 Cronograma de trabajo e hitos**

| Periodo | Actividad | Hito |
| :---- | :---- | :---- |
| Semana 1 | Despliegue de Django-CRM y MySQL; datos ficticios, guion de incidentes y línea base. | Entorno reproducible y matriz de eventos esperados. |
| Semana 2 | Instrumentación de las rutas web, admin y API; captura de before/after, contexto y pruebas de cobertura. | Eventos de auditoría y pruebas por vía de acceso. |
| Semana 3 | Ejecución de escenarios; adquisición de registros y exportación de datos; SHA-256, custodia y copias. | Paquete de evidencias con manifiesto. |
| Semana 4 | Correlación, línea de tiempo, cálculo de métricas, comparación e informe. | Matriz comparativa e informe forense. |

# **Capítulo II. Marco teórico científico**

Se revisaron cinco investigaciones publicadas entre 2022 y 2025, tres internacionales y dos peruanas. Su conjunto muestra que los registros de un sistema pueden resultar insuficientes para reconstruir un incidente cuando no fueron diseñados para una investigación.

## **2.1 Antecedentes**

### **2.1.1 Antecedentes internacionales**

Azahari y Balzarotti (2024) quisieron saber hasta qué punto sirven los registros de las aplicaciones en una investigación forense. En el artículo On the inadequacy of open-source application logs for digital forensics revisaron el código fuente de 60 aplicaciones de escritorio de código abierto y evaluaron sus mensajes de registro frente a cinco tareas: armar líneas de tiempo, correlacionar eventos, separar acciones, detectar uso indebido y detectar ataques. Los resultados no fueron buenos. En 29 aplicaciones los registros no tenían marca de tiempo, y 23 no guardaban identificadores para relacionar actividades nuevas.

El mayor acierto del estudio está en su método, porque analiza el código y no la documentación, y así muestra lo que de verdad se registra. También traduce las necesidades del investigador a campos concretos que un registro debería tener. Su alcance, en cambio, se queda en el diagnóstico. Las aplicaciones evaluadas son de escritorio y no sistemas web con varios usuarios, y el trabajo no implementa ni prueba ninguna mejora. La presente propuesta parte de ese diagnóstico y da el paso siguiente. Incorpora los campos que faltan en una aplicación web concreta y comprueba si con ellos se puede reconstruir un incidente.

El trabajo de Olegård, Axelsson y Li (2025), When is logging sufficient?, enfoca la pregunta desde el otro lado. No revisa registros existentes, sino que discute qué debería registrarse. Para los autores, un sistema está preparado para una investigación sólo respecto de un conjunto de preguntas forenses que se pueden anticipar, y lo que más suele faltar en los registros es la relación causal entre eventos. Su propuesta, los gretel numbers, son identificadores que enlazan cada evento con el que lo provocó, incluso entre aplicaciones distintas.

El prototipo se construyó con Nginx en dos contenedores Docker y un módulo eBPF, y se probó con 10 000 solicitudes repetidas diez veces, con el mecanismo activo y sin él. El tiempo de CPU aumentó, aunque el impacto sobre la duración total fue reducido; la memoria asignada subió aproximadamente un 8 % y los registros crecieron entre 2 y 2,5 veces. Los propios autores reconocen que la prueba se limitó a un servidor web y que no incluyó un almacenamiento que protegiera los registros. De este estudio se toman dos ideas. Una es definir los campos a partir de preguntas concretas sobre quién, qué, cuándo y desde dónde. La otra es su diseño comparativo, que aquí se repite al contrastar los registros originales de Django-CRM con los incorporados. La diferencia está en el nivel de trabajo, ya que este proyecto registra operaciones de negocio sobre clientes y no llamadas al sistema operativo. Además, suma la preservación y la cadena de custodia que el prototipo dejó fuera.

Desde la ingeniería de software, Daubner, Buhnova y Pitner (2024) entrevistaron a especialistas en análisis forense digital para entender cómo debería comportarse un sistema preparado para una investigación. El artículo, Forensic experts' view of forensic-ready software systems: A qualitative study, identificó dos frenos para adoptar este tipo de sistemas. Quienes participan en su desarrollo persiguen objetivos distintos, y los ingenieros de software suelen tener poca formación forense.

Lo valioso del estudio es que escucha a quienes después usan la evidencia, algo poco frecuente en una literatura dominada por propuestas técnicas. Su resultado son necesidades y criterios, no un sistema construido, así que no permite saber si esos criterios bastan en la práctica. Este proyecto los lleva a un caso real y mide qué se consigue con ellos.

### **2.1.2 Antecedentes nacionales**

En el Perú, Farfán Chiun (2024) evaluó en su tesis de maestría ISO 27037:2012 para mejorar el análisis informático forense en la División de Investigación de Delitos de Alta Tecnología de la Policía Nacional del Perú, Lima 2022, presentada en la Universidad Nacional Federico Villarreal, el efecto de esa norma sobre el trabajo forense de la unidad. El punto de partida era un problema conocido allí, porque las incidencias informáticas no se registraban bien en computadoras y servidores. Con un diseño experimental de preprueba y posprueba comparó el trabajo antes y después de adoptar la norma. Después de la adopción bajaron las horas dedicadas al análisis, aumentó la cantidad de datos extraídos de dispositivos móviles y crecieron los casos resueltos.

Su acierto principal es haber medido el efecto de la norma con indicadores operativos en una institución real del país. Esos indicadores, sin embargo, miden eficiencia y no la calidad con que se reconstruye un hecho, y el estudio se centró en dispositivos móviles incautados. El presente trabajo también toma ISO/IEC 27037 como referencia para su procedimiento, pero la aplica a otro tipo de evidencia, los registros de una aplicación web, y evalúa si los hechos pueden reconstruirse.

Mayta Avalos, Rosales Castilla y Gines Colana (2022), de la Universidad Nacional Jorge Basadre Grohmann de Tacna, publicaron en la revista Innovación y Software el artículo Trazabilidad de operaciones en base de datos para mitigar riesgos en los procesos de auditoría. Allí propusieron un modelo de auditoría para seguir las operaciones de una base de datos Oracle y lo probaron en un laboratorio con el esquema de ejemplo HR. La auditoría propia del motor anotaba el usuario, la sesión, el equipo de origen, la operación y la hora, pero no el valor que tenía un dato antes de cambiar. Para conservarlo, los autores añadieron disparadores (triggers) que copiaban cada inserción, actualización y eliminación en una tabla de auditoría, junto con el usuario, la dirección IP y el programa usado.

De todos los trabajos revisados, este es el más cercano a la propuesta, porque detecta el mismo vacío. Acierta al combinar dos fuentes y al guardar el estado anterior del dato. Tiene también límites claros. El estudio implementa y demuestra el modelo en un laboratorio con el esquema HR de Oracle, aunque no realiza una evaluación cuantitativa o comparativa de su desempeño, y los disparadores quedan en manos del administrador de la base de datos, que es quien los crea y quien podría desactivarlos. Tampoco se ocupa de preservar los registros ni de la cadena de custodia. La propuesta actual captura el estado anterior desde la aplicación, donde se conoce la sesión del usuario, y luego somete esos registros a un procedimiento forense completo.

### **2.1.3 Síntesis de los antecedentes**

Azahari y Balzarotti identifican campos faltantes en los registros; Olegård et al. proponen correlación causal y una evaluación comparativa; Daubner et al. recogen criterios de especialistas. Farfán Chiun estudia la aplicación operativa de ISO/IEC 27037 en el Perú y Mayta Avalos et al. conservan valores previos con disparadores de base de datos. La presente propuesta reúne captura de contexto de operaciones web con adquisición, custodia y evaluación de la reconstrucción, sin afirmar que los estudios anteriores carezcan por completo de evaluación.

## **2.2 Bases teóricas**

Las bases teóricas explican el análisis forense digital, la preservación y cadena de custodia, las fuentes persistentes de evidencia y la preparación forense en una aplicación Django. La memoria RAM se describe como técnica general y no forma parte de la ejecución del proyecto.

### **2.2.1 Fundamentos del análisis forense digital**

#### ***2.2.1.1 Análisis forense digital y sus fases***

El NIST define el análisis forense digital como la aplicación de la ciencia a la identificación, recolección, examen y análisis de datos, preservando la integridad de la información y manteniendo una cadena de custodia estricta (Kent et al., 2006). La guía SP 800-86 divide el trabajo en cuatro fases. En la recolección se identifican, etiquetan y adquieren las fuentes de datos. El examen procesa lo recolectado para extraer lo que interesa al caso, y el análisis interpreta esos resultados con métodos que se puedan justificar, hasta responder las preguntas que dieron origen a la investigación. El reporte cierra el proceso. Describe lo que se hizo y con qué herramientas, y propone mejoras.

En este proyecto cada fase tiene un correlato claro. La recolección y el examen se aplican a los registros capturados en Django-CRM y a la base de datos. El análisis produce la línea de tiempo de los incidentes, y el reporte toma la forma del informe forense.

#### ***2.2.1.2 Evidencia digital y sus principios***

Se llama evidencia digital a la información almacenada o transmitida en forma digital que puede servir como prueba. Es frágil, porque un manejo descuidado la altera o la destruye sin dejar rastro visible. La norma ISO/IEC 27037:2012 da directrices para cuatro actividades sobre la evidencia potencial, que son su identificación, recolección, adquisición y preservación (ISO/IEC, 2012).

La misma norma fija tres principios. Una evidencia es relevante cuando ayuda a probar o descartar un hecho investigado, confiable cuando es lo que dice ser y suficiente cuando permite examinar bien los elementos del caso. Para el manejo de la evidencia exige además auditabilidad, justificabilidad y, según las circunstancias, repetibilidad o reproducibilidad. Un procedimiento es repetible si da los mismos resultados con el mismo método, las mismas herramientas y las mismas condiciones. Es reproducible si los resultados se mantienen aunque cambien las herramientas o las condiciones. En estos criterios se apoya el procedimiento repetible que plantea el Capítulo I.

#### ***2.2.1.3 Reconstrucción de eventos y línea de tiempo***

Reconstruir un evento es determinar qué ocurrió a partir de los rastros que dejó. Gladyshev y Patel (2004) formalizaron esta tarea modelando el sistema como una máquina de estados finitos. A partir del estado final y de la evidencia disponible se infieren las secuencias de eventos que pudieron producirlo. La línea de tiempo ordena esos eventos de forma cronológica y permite recorrer el incidente de principio a fin (Azahari & Balzarotti, 2024). Rowlingson (2004) recomienda usarla también al presentar el caso, porque la evidencia digital suele ser difícil de entender para quien no es especialista.

Ordenar los eventos solo por su hora tiene un riesgo. Si los relojes de los equipos no están sincronizados, la secuencia resultante puede ser falsa (Olegård et al., 2025). Por eso el proyecto guarda, junto con la marca de tiempo, un identificador de correlación de sesión que agrupa las acciones hechas en una misma sesión.

### **2.2.2 Preservación de la evidencia y cadena de custodia**

#### ***2.2.2.1 Metodologías de preservación***

Preservar la evidencia es protegerla de cambios, pérdidas o destrucción durante todo el proceso. ISO/IEC 27037 pide manipular lo menos posible el original, documentar cualquier cambio que se produzca y adquirir la evidencia de la forma menos intrusiva posible (ISO/IEC, 2012). En la práctica esto significa trabajar siempre sobre copias verificadas y guardar el original sin tocarlo.

Rowlingson (2004) añade el lado organizativo. Propone una política de almacenamiento seguro que garantice la autenticidad de los datos y permita demostrar su integridad cada vez que se usan, se trasladan o se combinan con evidencia nueva. Entre sus medidas están controlar con rigor el acceso de los administradores, cifrar los archivos de evidencia y sus transferencias, y mantener varias copias en lugares distintos. Considera que los registros locales son demasiado vulnerables y recomienda enviarlos también a un servidor remoto, ya que si las dos versiones dejan de coincidir queda expuesto el intento de alterarlas.

#### ***2.2.2.2 Cadena de custodia***

La cadena de custodia es el registro documentado de quién tuvo la evidencia, cuándo, para qué y qué pasó con ella en cada traslado. Sirve para demostrar que lo que se analiza es lo mismo que se adquirió. Rowlingson (2004) la compara con las bolsas de evidencia del mundo físico, que quien las retira firma al recibirlas y vuelve a firmar al devolverlas con el contenido intacto. En todo momento la evidencia debe estar en un estado que delate cualquier manipulación.

ISO/IEC 27037 incluye requisitos mínimos de documentación para cada transferencia de evidencia. ISO/IEC 27043, por su parte, trata la preservación de la cadena de custodia como un proceso concurrente que acompaña a toda la investigación (ISO/IEC, 2012, 2015). En este proyecto cada adquisición, copia y entrega quedará anotada con su fecha, el responsable, el propósito y el hash calculado en ese momento.

#### ***2.2.2.3 Integridad mediante SHA-256***

Una función hash criptográfica convierte datos de cualquier tamaño en un resumen de longitud fija. SHA-256, definido en el estándar FIPS 180-4, produce un resumen de 256 bits (National Institute of Standards and Technology \[NIST\], 2015). Cualquier cambio en los datos produce, con una probabilidad altísima, un resumen distinto, así que basta comparar dos resúmenes para saber si un archivo cambió.

En el trabajo forense el hash se calcula al adquirir la evidencia y se vuelve a calcular antes de cada examen. Si los dos valores coinciden, la evidencia no se modificó desde la adquisición. El proyecto reconoce un límite de esta técnica, porque el hash prueba integridad y no veracidad. Un registro que contenía información falsa desde su origen conserva su hash intacto.

#### ***2.2.2.4 Protección de los registros***

La protección contra manipulación mejora el valor de un registro como evidencia. Schneier y Kelsey (1999) propusieron un esquema criptográfico para registros de auditoría en el que, aunque un atacante tome el control del sistema, no puede leer ni modificar sin ser detectado las entradas escritas antes de ese momento. Rowlingson (2004) menciona también los medios de escritura única (WORM), que impiden reescribir lo ya almacenado. Estas técnicas son referencias conceptuales; el proyecto verificará la integridad de los archivos adquiridos con SHA-256 y documentará su custodia, sin implementar WORM ni un esquema criptográfico de registro resistente a la manipulación.

### **2.2.3 Técnicas y fuentes de adquisición**

#### ***2.2.3.1 Orden de volatilidad***

No toda la evidencia dura lo mismo. El RFC 3227 recomienda recolectarla desde lo más volátil hasta lo más estable (Brezinski & Killalea, 2002). El orden empieza por los registros y la caché del procesador. Siguen la tabla de enrutamiento, la caché ARP, la tabla de procesos, las estadísticas del núcleo y la memoria. Más abajo están los sistemas de archivos temporales, el disco, los registros remotos y los datos de monitoreo, y al final la configuración física, la topología de la red y los medios de archivo.

En este laboratorio se adquirirán los registros persistentes antes de detener o eliminar los contenedores, especialmente los que podrían perderse con la rotación o la eliminación. El criterio de volatilidad se conserva como referencia general, pero el procedimiento experimental no incluye captura de memoria.

#### ***2.2.3.2 Adquisición de memoria RAM como referencia teórica***

La memoria RAM guarda información que nunca llega al disco, como los procesos en ejecución, las conexiones de red abiertas, el historial de comandos y parte de los datos que las aplicaciones manejan en ese instante. Ligh et al. (2014) advierten que esta memoria suele pasarse por alto, o destruirse, durante la respuesta a un incidente, y dedican buena parte de su obra a explicar cómo adquirirla sin restarle valor forense.

LiME (Linux Memory Extractor) es un módulo de kernel usado para adquirir memoria de Linux (504ensics Labs, s. f.). Los contenedores Docker comparten el kernel del anfitrión: ejecutar una herramienta de este tipo en un contenedor privilegiado actuaría sobre ese kernel. Esta técnica se incluye solo para situar la adquisición de memoria en el marco teórico. El proyecto no ejecutará LiME ni realizará adquisiciones o análisis de imágenes de RAM.

#### ***2.2.3.3 Sistemas de archivos y contenedores***

La mayor parte de la evidencia digital termina en un sistema de archivos, la estructura con la que el sistema operativo organiza los datos en el disco. Carrier (2005) propone estudiarlo en cinco categorías de datos. La categoría del sistema de archivos describe su estructura general, y la de contenido abarca los bloques donde están los datos. En la de metadatos se describe cada archivo, con su tamaño, sus permisos y sus marcas de tiempo. La categoría de nombres vincula esos metadatos con el nombre que ve el usuario, y la de aplicación reúne funciones adicionales, como el registro por diario (journaling).

Esa división explica por qué a veces se puede recuperar un archivo borrado. Al eliminarlo, el sistema suele liberar su nombre y sus metadatos, pero el contenido sigue en el disco hasta que otro archivo ocupa ese espacio.

Docker distingue la capa de escritura del contenedor y los volúmenes persistentes (Docker Inc., s. f.). En este proyecto se exportarán los registros accesibles y una copia lógica coherente de la base de datos; se registrarán la configuración y el momento de adquisición. No se hará una imagen de la capa de escritura ni una copia bit a bit del volumen.

#### ***2.2.3.4 Fuentes de evidencia en MySQL***

El registro binario de MySQL conserva eventos de cambio cuando está habilitado; no registra consultas de solo lectura (Oracle, s. f.). Frühwirt et al. (2013) describen técnicas de reconstrucción desde redo logs de InnoDB. Aquí el registro binario se utilizará para contraste si se encuentra activado durante la prueba, y el análisis de redo logs se mantiene como referencia teórica.

Para el escenario de este proyecto, estas fuentes presentan un límite. Muestran qué cambió en la base de datos, pero no qué usuario de la aplicación lo hizo, desde qué dirección IP ni en qué sesión, porque Django suele conectarse a MySQL con una sola cuenta de servicio. Por esa razón el proyecto las usa para contrastar y no como evidencia principal.

### **2.2.4 Preparación forense y registro de actividad**

#### ***2.2.4.1 Preparación forense***

La preparación forense (forensic readiness) es la capacidad de una organización para aprovechar al máximo la evidencia digital y, a la vez, reducir el costo de una investigación (Rowlingson, 2004). El autor plantea diez pasos, y los cuatro primeros se aplican directamente en este proyecto. Consisten en definir los escenarios del negocio que requieren evidencia, identificar las fuentes disponibles, determinar qué hace falta recolectar y asegurar la capacidad de reunir esa evidencia de forma segura y legalmente admisible. Rowlingson insiste en que la evidencia debe mostrar no solo qué ocurrió, sino también cómo, cuándo y quién lo hizo. También señala que la preparación tiene especial valor cuando el riesgo viene de personas internas en las que la organización ya confía.

ISO/IEC 27043:2015 organiza la investigación de incidentes en cinco clases de procesos, que son los de preparación, inicialización, adquisición, investigación y los concurrentes (ISO/IEC, 2015). La preparación va primero y ocurre antes de cualquier incidente. En el campo del software, Pasquale et al. (2018) hablan de sistemas preparados para la investigación forense (forensic-ready software systems), capaces de apoyar una posible investigación digital, y advierten que las metodologías de ingeniería de software apenas consideran este requisito. El proyecto sigue ese enfoque al incorporar en Django-CRM la captura de los datos que una investigación va a necesitar.

#### ***2.2.4.2 Registros de auditoría y trazabilidad***

Un registro (log) es la anotación de un evento ocurrido en un sistema o en una red. La guía NIST SP 800-92 entiende la gestión de registros como el proceso de generarlos, transmitirlos, almacenarlos, analizarlos y eliminarlos (Kent & Souppaya, 2006). Los registros de auditoría documentan lo que hacen los usuarios, y la trazabilidad es la propiedad que permite seguir esas acciones hasta su origen.

Auditoría y trazabilidad aportan datos, pero no son un análisis forense. Para que esos datos lleguen a ser evidencia hay que adquirirlos, preservarlos y analizarlos con un procedimiento definido.

#### ***2.2.4.3 Amenaza interna y uso indebido de privilegios***

Una amenaza interna proviene de alguien que mantiene una relación de confianza con la organización, como un empleado. Verizon (2026) llama uso indebido al empleo de recursos o privilegios que la organización confió al usuario, y registra la participación de actores internos en el 12 % de las brechas que analizó. Estos casos cuestan detectarlos porque el responsable no rompe ningún control técnico y trabaja con permisos que el sistema da por válidos.

De aquí sale un límite que el proyecto respeta. Un registro identifica la cuenta que ejecutó una acción, pero no prueba quién estaba frente al equipo. Atribuir un hecho a una persona exige evidencia adicional, y por eso este trabajo distingue entre identificar una cuenta y atribuir un hecho.

#### ***2.2.4.4 Registro de actividad en Django***

Django, el framework sobre el que está construido Django-CRM, trae un registro de acciones para su panel administrativo. El modelo LogEntry guarda la fecha y hora de la acción, el usuario, el tipo de objeto, su identificador, una representación textual del objeto de hasta 200 caracteres, el tipo de acción (adición, modificación o eliminación) y un mensaje de cambio (Django Software Foundation, s. f.-a). No guarda la dirección IP ni los valores anteriores y posteriores de los campos. Además, solo se genera cuando la operación se hace desde el panel administrativo, así que las acciones de la interfaz web principal y de la API quedan fuera.

Django ofrece señales que pueden ejecutar código antes o después de guardar o eliminar un modelo (Django Software Foundation, s. f.-b). Permiten observar operaciones que pasan por esos mecanismos, incluidas las iniciadas desde diferentes interfaces, siempre que dichas interfaces utilicen esos métodos. La atribución de IP y sesión requiere recoger además el contexto de la solicitud.

Las señales por sí solas no garantizan cobertura completa. Una actualización masiva con QuerySet.update() se ejecuta directamente en SQL, no llama al método save() de los modelos y, por lo tanto, no emite las señales pre\_save ni post\_save (Django Software Foundation, s. f.-c). SQL directo ajeno a Django tampoco emite esas señales. Por ello la propuesta instrumentará los flujos de escritura de la interfaz web, el admin y la API y comprobará su cobertura mediante pruebas; las escrituras fuera de esos flujos quedan expresamente fuera del alcance.

## **2.3 Definiciones de términos básicos**

* **Actor interno.** Persona con una relación de confianza con la organización, como un empleado, que tiene acceso legítimo a sus sistemas.

* **Adquisición.** Obtención de una copia de la evidencia desde su fuente, hecha de modo que se pueda comprobar que corresponde al original.

* **Atribución.** Vinculación de una acción con la persona que la realizó. Saber qué cuenta ejecutó una operación no basta para atribuirla.

* **Auditoría.** Revisión de los registros de actividad de un sistema para comprobar qué se hizo y si se respetaron las reglas establecidas.

* **Cadena de custodia.** Registro documentado de quién tuvo la evidencia, cuándo, con qué fin y qué ocurrió con ella en cada etapa.

* **Capa de escritura del contenedor.** Capa que Docker coloca sobre las capas de solo lectura de una imagen y donde se guardan los cambios del contenedor. Se pierde cuando el contenedor se elimina.

* **Copia de trabajo.** Duplicado verificado de la evidencia sobre el que se hacen el examen y el análisis, para que el original quede intacto.

* **Correlación de eventos.** Relación entre eventos registrados en fuentes o momentos distintos que pertenecen a una misma actividad.

* **Estado anterior y posterior.** Valores que tenía un registro antes de una operación y los que tiene después. Al compararlos se ve qué campos cambiaron.

* **Evidencia digital.** Información almacenada o transmitida en forma digital que puede servir como prueba de un hecho.

* **Hash.** Resumen de longitud fija que una función criptográfica calcula a partir de unos datos. Si los datos cambian, el resumen cambia.

* **Identificador de correlación de sesión.** Valor asignado a una sesión de usuario que se guarda con cada evento para agrupar lo hecho en esa sesión.

* **Incidente de seguridad.** Evento que compromete o pone en riesgo la información. En este proyecto, una operación que contradice las reglas del escenario.

* **Integridad.** Propiedad de la información de mantenerse sin alteraciones no autorizadas desde un momento determinado.

* **Línea de tiempo.** Orden cronológico de los eventos relacionados con un incidente, que permite reconstruir cómo ocurrió.

* **No repudio.** Propiedad que requiere evidencias suficientes para dificultar negar una acción; los registros de cuenta y sesión por sí solos no prueban la identidad física del operador.

* **Orden de volatilidad.** Criterio que manda recolectar primero la evidencia que desaparece antes, como la memoria, y después la más estable, como el disco.

* **Preparación forense.** Capacidad de una organización o de un sistema para reunir y conservar, antes de un incidente, la evidencia que una investigación necesitará.

* **Preservación.** Medidas que protegen la evidencia de cambios, pérdidas o destrucción a lo largo de todo el proceso.

* **Registro (log).** Anotación de un evento ocurrido en un sistema, con datos como la fecha y hora, la cuenta y la acción realizada.

* **Registro binario.** Archivo de MySQL que guarda los eventos que modifican la base de datos.

* **Sesión.** Periodo en el que un usuario autenticado interactúa con la aplicación, desde que inicia hasta que cierra o expira.

* **SHA-256.** Función hash del estándar FIPS 180-4 que produce un resumen de 256 bits. En el proyecto se usa para verificar la integridad de la evidencia.

* **Sistema de archivos.** Estructura que usa el sistema operativo para organizar y localizar los datos en un medio de almacenamiento.

* **Token de autenticación.** Valor que el sistema entrega a un usuario después de verificar su identidad y que este presenta en cada solicitud posterior. En una aplicación web puede ser una cookie de sesión o un token enviado a la API.

* **Trazabilidad.** Propiedad que permite seguir una acción o un dato hasta su origen.

* **Uso indebido de privilegios.** Empleo de permisos o recursos otorgados por la organización para fines que no están autorizados.

# **CAPITULO III: DISEÑO METODOLOGICO Y ARQUITECTURA**

## **Descripción de la solución tecnológica planteada**

La solución tecnológica propuesta consiste en el despliegue de la aplicación de código abierto Django-CRM en un entorno local y controlado, operando sobre contenedores de Docker y una base de datos MySQL. Funcional y lógicamente, el sistema incorpora mecanismos de "preparación forense" diseñados para capturar la actividad generada a través de la interfaz web, el panel administrativo y la API. Estos mecanismos resuelven las deficiencias del sistema original al recolectar de forma estructurada el contexto completo de cada operación, lo cual incluye la cuenta, fecha y hora, dirección IP, identificador de correlación de sesión, la acción realizada, el registro afectado y los valores exactos de los estados anterior y posterior a los cambios.

* ### **Arquitectura Tecnológica y de Ciberseguridad**

![][image1]  
El diagrama expone el ciclo de vida de los datos durante la simulación y el análisis forense, estructurado en cinco fases secuenciales:

* **1\. Entorno de Generación y Simulación:** Representa el origen de los eventos, donde los usuarios ejecutan peticiones hacia la interfaz web, el panel administrativo o la API de Django-CRM, sistema que se encuentra alojado junto a su base de datos MySQL dentro de un entorno virtualizado con Docker.  
* **2\. Preparación Forense (Captura):** Ilustra el momento en que las operaciones son interceptadas por los mecanismos incorporados al sistema para extraer y registrar sistemáticamente el contexto del evento, incluyendo la cuenta, fecha, IP, sesión y las copias exactas del registro antes y después del cambio.  
* **3\. Adquisición y Preservación:** Muestra la extracción de los registros generados aplicando un procedimiento forense estándar, seguido del cálculo de hashes SHA-256 para certificar criptográficamente que la evidencia recolectada no ha sido alterada.  
* **4\. Gestión y Análisis:** Detalla la fase de investigación, en la cual se generan copias de trabajo para examinar los datos sin alterar los originales, manteniendo estricto control de la cadena de custodia y correlacionando los indicadores de sesión y tiempo para reconstruir los incidentes en una línea temporal verificable.  
* **5\. Resultados:** Concluye el proceso con la elaboración de un informe forense formal, el cual consolida los hallazgos demostrables y expone las limitaciones intrínsecas del análisis efectuado.

### **Frameworks de Seguridad y/o Estándares Aplicados**

La solución y sus procedimientos se fundamentan en los siguientes estándares y guías técnicas internacionales referenciadas en el proyecto:

* **ISO/IEC 27037:2012:** Estándar internacional enfocado en las directrices para la identificación, recolección, adquisición y preservación de evidencia digital.  
* **NIST Special Publication 800-86:** Guía técnica elaborada por el Instituto Nacional de Estándares y Tecnología (NIST) para integrar técnicas forenses en los procesos de respuesta a incidentes

### **Indicadores y Métricas de Evaluación**

Para validar si el sistema cumplió sus metas dentro de la gestión forense, se establecen los siguientes indicadores:

* Integridad de Hashes (Gestión Forense): Se evaluará el aseguramiento criptográfico de la evidencia verificando que los hashes SHA-256 de las copias de trabajo coincidan con la evidencia originalmente adquirida, garantizando la cadena de custodia.  
* Capacidad de reconstrucción (Métrica comparativa): Se medirá la efectividad del sistema comparando qué acciones (modificaciones y eliminaciones) pueden reconstruirse completamente usando los mecanismos forenses incorporados frente a las acciones que pueden reconstruirse solo con los registros originales del CRM.  
* Correlación de eventos: Indicador cualitativo que valida la capacidad de construir una línea de tiempo verificable y repetible sobre copias de trabajo a partir de los atributos de sesión y tiempo recolectados.

# **CAPÍTULO IV: IMPLEMENTACIÓN Y GESTIÓN DEL PROYECTO**

El presente capítulo documenta la construcción e integración del laboratorio de análisis forense sobre Django-CRM y del procedimiento de investigación asociado. La implementación se estructuró en torno a los componentes técnicos, las fuentes de evidencia, el control de integridad, la cadena de custodia y las actividades de reconstrucción. La guía NIST SP 800-86 se adoptó como eje del procedimiento, complementada con las directrices de identificación, adquisición y preservación de ISO/IEC 27037:2012. La comprobación empírica del funcionamiento y los resultados comparativos se reservaron para el capítulo V.

NIST SP 800-86 se utilizó como guía de buenas prácticas para integrar técnicas forenses en la respuesta a incidentes, no como una norma certificable ni como garantía de admisibilidad judicial. Por esta razón, la alineación metodológica se materializó mediante actividades, controles y artefactos trazables asociados a sus recomendaciones, cuya ejecución y eficacia se sometieron a criterios de validación definidos para el capítulo V (Kent et al., 2006, secs. 2, 3 y 7).

## **4.1 Construcción e Implementación Técnica**

### **4.1.1 Línea base del repositorio y delimitación del trabajo**

Se tomó como base de desarrollo el repositorio https\://github.com/ChakerChourouk/Django-CRM, rama main, en el último commit identificado durante la revisión del 29 de octubre de 2026: 5f80cd1 («docs: add screenshots, Railway deployment section, and live demo link to README»). Este punto de partida se estableció como referencia de versión del laboratorio; el procedimiento de reproducibilidad incorporó git rev-parse HEAD, el registro del SHA completo y el inventario de las herramientas. La identificación de componentes se fundamentó en la revisión estática del repositorio.

En el código de partida se identificaron el modelo website.models.Record, con datos de identidad y contacto; las vistas web website/views.py (add\_record, update\_record y delete\_record); el RecordViewSet de Django REST Framework ubicado en website/api\_views.py; el RecordAdmin de website/admin.py; y los servicios web y db (MySQL 8.0) definidos en docker-compose.yml. Las vistas web emitían mensajes INFO para las operaciones CRUD, la API utilizaba un ModelViewSet sin historial completo de cambios y el panel administrativo disponía del historial estándar de Django. Esta revisión permitió delimitar la carencia que se abordó: un registro persistente y correlacionado con estados anterior y posterior, común a web, administración y API (ChakerChourouk, s. f.).

| Componente real | Estado de partida observado | Integración documentada en el desarrollo |
| :---- | :---- | :---- |
| website/models.py | Record: nombre, correo, teléfono, dirección, ciudad, estado, código postal y timestamps. | Se incorporó AuditEvent en el módulo de auditoría, con migración y política de acceso diferenciada. |
| website/views.py | CRUD web basado en formularios; mensajes INFO con cuenta e ID. | Se centralizaron CREATE/UPDATE/DELETE en un servicio transaccional con trazabilidad. |
| website/api\_views.py | RecordViewSet(ModelViewSet), IsAuthenticated. | Se adaptaron perform\_create, perform\_update y perform\_destroy para utilizar el servicio común. |
| website/admin.py | RecordAdmin con filtros, búsqueda y edición normal. | Se cubrieron save\_model, delete\_model y delete\_queryset, incluida la acción masiva. |
| dcrm/settings/base.py | SessionMiddleware, AuthenticationMiddleware, zona UTC y logging en consola. | Se incorporó middleware de contexto, registro estructurado y retención documentada. |
| docker-compose.yml | web+db, MySQL con volumen mysql\_data; puertos 8000 y 3306 publicados. | Se prepararon perfiles aislados, exposición restringida de MySQL y rotación controlada de logs. |

La implementación se delimitó a las escrituras de Record realizadas por los flujos instrumentados de la interfaz web, el panel de administración y la API. Se mantuvieron fuera del alcance las consultas SQL directas, las llamadas a QuerySet.update() ajenas al servicio, la adquisición de RAM, las imágenes bit a bit, los redo logs, WORM y los demás mecanismos excluidos por los capítulos I y II. El binlog, cuando estuvo previsto como fuente disponible, se trató únicamente como contraste secundario y no como evidencia primaria.

### **4.1.2 Entornos simulados y control de reproducibilidad**

Se estructuraron dos despliegues aislados sobre la misma versión de Django-CRM, con imágenes, esquema y carga ficticia inicial equivalentes: el entorno A, conservado como línea base sin la auditoría incorporada, y el entorno B, preparado con la instrumentación forense. Cada despliegue quedó definido con un proyecto Docker Compose y un volumen MySQL independiente, sin compartir bases de datos en ejecución. Los snapshots iniciales y el guion de acciones se organizaron como referencias experimentales separadas de las evidencias adquiridas.

1\. Se incorporó al procedimiento de reproducibilidad la clonación del repositorio, la fijación del commit de partida y la creación de una rama propia; se estableció el registro del SHA completo, las versiones de Docker/Compose, el anfitrión y las imágenes utilizadas.

2\. Se preparó la configuración de laboratorio a partir de .env.example, con secretos ficticios nuevos y exclusión de credenciales del repositorio; se adoptaron DEBUG=False para evaluación, contraseñas no predeterminadas, perfiles separados y acceso restringido a localhost o a la red interna.

3\. Se diseñaron redes aisladas para los servicios y se restringió la exposición de MySQL, evitando publicar el puerto 3306 en todas las interfaces. Se conservó mysql\_data y se separaron los privilegios de la cuenta de despliegue de los de ejecución de la aplicación.

4\. Se definió una carga reproducible de cuentas y clientes ficticios con identificadores estables. El guion documentado incluyó operaciones normales, cambios sin justificación, modificaciones sucesivas y eliminación, junto con una tabla de verdad independiente de la base operativa.

5\. Se estableció UTC como referencia temporal para la aplicación y los reportes; el procedimiento incorporó sincronización del anfitrión y documentación de hora, zona, offset y posibles desviaciones en cada exportación.

6\. Se preparó un protocolo de ejecución equivalente para A y B, con restauración del snapshot inicial, comparación de orden, identificadores, cuentas y condiciones de acceso, y conservación separada de los productos de cada repetición. La aplicación y medición de este guion se dejó definida para la validación experimental.

git clone https\://github.com/ChakerChourouk/Django-CRM.git  
cd Django-CRM  
git checkout 5f80cd1  
git rev-parse HEAD     \# Guardar SHA completo en acta  
cp .env.example .env \# Configurar SOLO secretos ficticios locales  
docker compose up \--build \-d  
docker compose exec web python manage.py migrate

El bloque anterior reúne los comandos de referencia utilizados para estructurar el despliegue reproducible desde la versión identificada. La configuración adicional, el sembrado de datos y la instrumentación quedaron detallados dentro de la solución. También se incorporó una restricción operativa: no ejecutar docker compose down \-v ni eliminar contenedores o volúmenes con registros pendientes antes del cierre de la adquisición de cada caso.

### **4.1.3 Arquitectura de trazabilidad forense y modelo de evento**

Se definió e integró la arquitectura del módulo website/forensics/, compuesto por middleware.py para el contexto de solicitud, models.py o el modelo equivalente AuditEvent, services.py para las operaciones transaccionales, export.py para las exportaciones controladas y tests/ para las comprobaciones de cobertura. Las escrituras de los tres canales se centralizaron en una capa única de servicio. Las señales de Django se consideraron únicamente complementarias, porque ciertas escrituras no llaman a save() y las operaciones masivas requieren tratamiento específico.

| Campo de AuditEvent | Propósito y regla de captura |
| :---- | :---- |
| event\_id / case\_tag | UUID único de evento; case\_tag vincula la ejecución del laboratorio, no sustituye ID de evidencia. |
| occurred\_at\_utc | Timestamp aware en UTC, generado en servidor y ordenable. |
| actor\_id / actor\_username | ID y nombre de cuenta autenticada; la cuenta no demuestra identidad física. |
| session\_correlation\_id | UUID aleatorio de sesión controlado en servidor; jamás guardar sessionid/cookie en claro. |
| request\_id / channel | UUID por solicitud y canal web, admin o api; method y route si aportan contexto. |
| src\_ip / user\_agent | IP obtenida de REMOTE\_ADDR; confiar en X-Forwarded-For solo bajo proxy expresamente confiable; UA acotado. |
| action / record\_id / outcome | CREATE, UPDATE o DELETE, ID de cliente, success/failure y causa controlada si corresponde. |
| before\_json / after\_json | Estado de campos permitidos anterior/posterior; CREATE before=null; DELETE after=null. |
| changed\_fields / committed | Campos efectivamente modificados; no registrar eventos de éxito para transacciones revertidas. |

Se estableció una lista positiva de campos de Record para crear snapshots JSON normalizados: nombre, apellido, correo, teléfono, dirección, ciudad, estado, código postal, created\_at y updated\_at. Se excluyeron contraseñas, cookies, identificadores de sesión en claro, encabezados Authorization, secretos y cargas ajenas a la investigación. Los snapshots se destinaron a almacenamiento restringido de laboratorio. La IP se trató como dato contextual y no como identificación concluyente de una persona.

Se implementó como regla de escritura el uso de transaction.atomic() sobre MySQL/InnoDB. El servicio obtuvo el estado anterior mediante lectura bloqueante cuando correspondía (select\_for\_update para actualización o borrado), aplicó el cambio validado, capturó el estado posterior y persistió AuditEvent dentro de la misma transacción. Ante fallos de auditoría se adoptó la reversión de la operación de negocio («fallar cerrado»). Se diferenciaron los intentos rechazados de las modificaciones confirmadas; un intento no se clasificó como cambio exitoso.

LÓGICA DEL SERVICIO TRANSACCIONAL (pseudocódigo simplificado):  
with transaction.atomic():  
    anterior \= snapshot(Record.objects.select\_for\_update().get(pk=id))  
    aplicar\_cambio\_validado(record, datos)  
    record.save()  
    posterior \= snapshot(record)  
    AuditEvent.objects.create(  
        event\_id=uuid4(), actor=request.user, action="UPDATE",  
        record\_id=record.pk, before\_json=anterior,  
        after\_json=posterior, session\_correlation\_id=context.session\_id,  
        request\_id=context.request\_id, occurred\_at\_utc=timezone.now(),  
        channel=context.channel, src\_ip=context.remote\_addr  
    )  
\# Si cualquiera de las dos escrituras falla, la transacción se revierte.

La representación anterior sintetiza la lógica transaccional adoptada; se presenta como pseudocódigo y no como transcripción literal del archivo fuente. Para CREATE se definió after con before nulo; para DELETE se conservó before antes de retirar el objeto, con after nulo. Los cambios sin diferencia de campos quedaron clasificados como no-op o excluidos de la métrica de modificaciones mediante una regla explícita y previa a la validación.

Se identificaron y adaptaron los puntos de escritura de la interfaz web (add\_record, update\_record y delete\_record), de DRF (perform\_create, perform\_update y perform\_destroy) y del administrador (save\_model, delete\_model y delete\_queryset). Para el borrado masivo se incorporó una vía auditada o la deshabilitación de la acción estándar cuando no pudiera garantizarse su cobertura. Se integró el tratamiento de formularios inválidos y de permisos para impedir rutas CRUD de los tres canales que eludieran el servicio centralizado.

Los eventos se destinaron a una tabla diferenciada de los registros de clientes. Se definió una cuenta de ejecución del CRM sin permisos UPDATE ni DELETE sobre AuditEvent y una cuenta distinta para migraciones. Esta separación se incorporó como protección frente a modificaciones accidentales, sin atribuir inmutabilidad frente a administradores de MySQL o del anfitrión. La verificación de integridad desde la adquisición se sustentó en hashes, manifiestos y custodia.

### **4.1.4 Registro operativo y preservación preventiva**

Se incorporó el registro operativo de Django/Gunicorn y Docker como fuente complementaria de AuditEvent, con marcas temporales, identificación de solicitudes, rutas, acciones y resultados, evitando exponer secretos. Se configuró la emisión por stdout/stderr para su conservación por Docker y se definió una política de rotación documentada antes de cada simulación. Se estableció la adquisición previa a cualquier sobrescritura, pues la rotación no implica retención ilimitada. El estado de autenticación/sesiones y el historial administrativo se incluyeron como posibles fuentes secundarias.

Se habilitó en la arquitectura un directorio de evidencias del anfitrión, externo al repositorio y a los volúmenes Docker, con acceso limitado al custodio. Cada caso se organizó en originales adquiridos, manifiestos, cadena de custodia y copias de trabajo. Los originales quedaron sujetos a conservación sin modificaciones operativas posteriores a su adquisición, con la salvedad de que los permisos del sistema de archivos no equivalen a un almacenamiento WORM. Se prohibió incluir dumps, cookies y archivos .env en el repositorio.

### **4.1.5 Preparación del caso y matriz de fuentes**

Se definió la apertura de cada incidente mediante un identificador único, una ficha de autorización y alcance (activos, responsables, intervalo temporal y restricciones), un guion aprobado y una comprobación de almacenamiento disponible. La separación entre simulación e investigación quedó documentada para evitar que las acciones del operador del escenario contaminaran las del analista. Se asignaron funciones de adquisición y custodia diferenciadas cuando la dotación lo permitió; en los demás casos se incorporó la declaración explícita de funciones compartidas en el acta.

| Fuente / prioridad | Método de adquisición establecido | Uso en la reconstrucción |
| :---- | :---- | :---- |
| F1. AuditEvent, alta | Se estableció la exportación íntegra de AuditEvent junto con el volcado SQL coherente, incluido esquema y marcas temporales. | Secuencia principal: cuenta, canal, sesión, ID y before/after. |
| F2. Logs web/Docker, alta | Se incorporó docker compose logs \--timestamps antes de cualquier parada, eliminación o rotación de contenedores. | Corroborar solicitudes, errores, rutas y momento de ejecución. |
| F3. Exportación MySQL, alta | Se adoptó mysqldump \--single-transaction para InnoDB, con registro de inicio, fin y condiciones de consistencia. | Estado persistente de clientes, auditoría, autenticación y admin. |
| F4. LogEntry admin, media | Se incorporó su extracción desde la copia de MySQL obtenida para el caso. | Validación cruzada de eventos realizados en /admin/. |
| F5. Metadatos técnicos, media | Se definió la captura de SHA de Git, versiones Docker, IDs de contenedores, UTC y red sanitizada. | Reproducibilidad e interpretación de origen y secuencia. |
| F6. Binlog MySQL, condicional | Se consideró únicamente cuando estuviera habilitado antes del incidente y cubriera su intervalo. | Contraste técnico de cambios SQL; sin identidad humana. |
| Fuera de alcance | Se delimitaron explícitamente como fuentes excluidas del procedimiento experimental. | Declarar ausencia y no atribuir conclusiones a esas fuentes. |

### **4.1.6 Procedimiento forense operacional basado en NIST SP 800-86**

Se adoptó el ciclo de NIST SP 800-86 (sec. 3), organizado en cuatro fases: recolección (collection), examen (examination), análisis (analysis) y reporte (reporting). La preparación y la cadena de custodia se integraron como controles transversales. Para cada fase se definieron operaciones documentables, entradas, artefactos y condiciones de aceptación, así como el retorno desde el análisis al examen cuando surgieran nuevas hipótesis. Las intervenciones sobre los sistemas activos quedaron sujetas al registro de su justificación e impacto.

#### ***4.1.6.1 Preparación, autorización e identificación de fuentes***

P1. Se estableció la apertura formal del caso con ID, hora UTC, solicitante, autorización académica, objetivo, alcance, responsables, estado inicial y preguntas forenses: qué cambió, qué cuenta intervino, cuándo, por cuál canal y con qué respaldo.

P2. Se incorporó el inventario de contenedores, volúmenes, tablas y fuentes de logs. Se estableció la priorización de F1-F3 por relevancia y riesgo de rotación, postergando cualquier parada o limpieza hasta completar su adquisición.

P3. Se definió una bitácora de decisiones de contención e impacto. En el laboratorio, el procedimiento estableció detener nuevas acciones del guion una vez declarado el incidente y conservar los contenedores para extraer los registros, sin asumir que un apagado previo carecería de efectos.

P4. Se designó dentro del procedimiento al custodio y la ubicación de originales, junto con la documentación de herramientas y versiones. Se incluyó una regla de no modificar retroactivamente fuentes para generar logs inexistentes; cualquier control activado después del incidente se etiqueta como posterior.

#### ***4.1.6.2 Fase 1: Recolección/adquisición y verificación de integridad***

C1. Se estandarizó el etiquetado único de cada fuente (por ejemplo, E-C01-F1), asociado a ruta, contenedor, volumen, operador, hora UTC, periodo cubierto, método, comando y errores de adquisición.

C2. Se incorporó la extracción temprana de logs persistentes antes de reiniciar o eliminar contenedores, con prohibición expresa de truncar, rotar o borrar registros durante la recolección. Los metadatos del despliegue se obtuvieron mediante comandos controlados que excluyen secretos de configuración.

C3. Se adoptó la exportación lógica coherente de tablas InnoDB mediante mysqldump y se definió el registro del inicio y fin, salida estándar/error y código de retorno. Se consideró que las escrituras concurrentes no convierten el volcado en imagen física instantánea; por ello, el procedimiento estableció cerrar las escrituras simuladas antes de adquirir el estado final.

C4. Se integró el cálculo inmediato de SHA-256 para cada archivo cerrado, la creación de un manifiesto de rutas relativas y hashes, el registro del tamaño y la detección de ficheros vacíos cuando no correspondieran. Estos datos se vincularon al acta de adquisición y a la cadena de custodia.

C5. Se estableció el resguardo de originales con acceso restringido y la generación de copias de trabajo, verificando sus hashes antes del examen y después de cada transferencia. El procedimiento incluyó inmovilizar las evidencias discrepantes, documentar el incidente y no declarar integridad ante una verificación fallida.

COMANDOS DE ADQUISICIÓN INTEGRADOS EN EL PROCEDIMIENTO (ejemplo Linux):  
CASE="\$HOME/forensic\_cases/CASE-001"; umask 077  
mkdir \-p "\$CASE"/{original,trabajo,custodia}  
docker compose logs \--no-color \--timestamps web db   \> "\$CASE/original/docker\_web\_db.log"  
docker compose ps \--all \> "\$CASE/original/compose\_ps.txt"  
git rev-parse HEAD \> "\$CASE/original/git\_commit.txt"  
\# Usar únicamente tras cerrar operaciones de la simulación:  
docker compose exec \-T db sh \-c 'MYSQL\_PWD="\$MYSQL\_ROOT\_PASSWORD" \\  
  mysqldump \-uroot \--single-transaction \--quick \--routines \--triggers \\  
  \--databases "\$MYSQL\_DATABASE"' \> "\$CASE/original/mysql.sql"  
\# Comprobar código de salida, contenido y stderr por separado.  
(cd "\$CASE/original" && find . \-type f \-print0 \| sort \-z \| \\  
  xargs \-0 sha256sum) \> "\$CASE/custodia/manifest.sha256"  
cp \-a "\$CASE/original/." "\$CASE/trabajo/"  
(cd "\$CASE/trabajo" && sha256sum \-c ../custodia/manifest.sha256)

El bloque anterior documenta los comandos establecidos para la adquisición controlada; se presenta como ejemplo parametrizable del procedimiento y no como evidencia de que un caso haya sido ejecutado. Se definió su encapsulación con manejo estricto de errores, verificación de espacio libre, códigos de retorno, stderr y rechazo de volcados incompletos. MYSQL\_PWD aparece dentro del contenedor únicamente como mecanismo ilustrativo; se estableció proteger secretos, permisos y trazas para impedir su incorporación accidental al expediente. Los manifiestos quedaron sujetos al mismo control de acceso y custodia que las evidencias (Kent et al., 2006, secs. 3.1.1–3.1.2).

#### ***4.1.6.3 Fase 2: Examen forense de copias verificadas***

E1. Se incorporó como condición de inicio la verificación SHA-256 y el registro de analista, herramienta, versión, hora y archivo de entrada. Se definió inmovilizar archivos que no superen la comprobación y recuperar una copia válida o declarar la limitación.

E2. Se diseñó un espacio aislado de análisis mediante la restauración de mysql.sql en una base temporal independiente del caso original. La extracción contempló AuditEvent, Record, sesiones pertinentes y django\_admin\_log.

E3. Se implementó la normalización de fecha/hora a UTC y de los campos actor\_id, record\_id, event\_id, request\_id, session\_correlation\_id y canal. Se conservaron los valores temporales de origen y su offset, junto con el registro de huecos, desviaciones, errores de parseo y duplicados.

E4. Se estructuró el filtrado por intervalo, cuenta y registros afectados. El examen comparó before\_json y after\_json campo a campo y vinculó eventos de la aplicación con logs Django/Docker e historial administrativo, con un indicador de ausencia de contraste cuando correspondiera.

E5. Se definió la generación de derivados reproducibles (events\_normalizados.csv, cambios\_por\_registro.csv e inconsistencias.txt) a partir de copias de trabajo, manteniendo el algoritmo de extracción y hashes específicos. Los derivados se clasificaron de manera distinta de los originales, que no debían transformarse durante el examen.

#### ***4.1.6.4 Fase 3: Análisis, hipótesis y reconstrucción cronológica***

A1. Se estructuró una matriz de preguntas forenses con respaldo mínimo por hallazgo: cuenta registrada, acción confirmada, campo afectado, valores previo y posterior, canal y periodo de ocurrencia.

A2. Se definió la correlación de fuentes mediante event\_id, record\_id, session\_correlation\_id y request\_id. La línea de tiempo se ordenó por occurred\_at\_utc y, cuando fue necesario, por secuencias documentadas de la fuente; los desfases horarios quedaron señalados en lugar de inferir una precisión inexistente.

A3. Se incorporó una comparación por operación entre los eventos del entorno B, el guion independiente («verdad de terreno») y las fuentes secundarias. La misma matriz de preguntas se aplicó al entorno A para medir atributos reconstruibles, en vez de limitar el contraste a un recuento bruto de logs.

A4. Se integró la evaluación de hipótesis alternativas: cambio legítimo, error operativo, sesión compartida, automatización vía API o reloj desincronizado. La calificación de una operación como indebida se vinculó a reglas predefinidas de negocio y no a la mera presencia de UPDATE o DELETE.

A5. Se estableció una escala de respaldo para conclusiones: confirmada con contraste, sustentada en una sola fuente, indeterminada o contradicha. También se documentaron los límites de atribución (cuenta ≠ persona), integridad (hash ≠ veracidad) y cobertura (SQL directo fuera del alcance).

#### ***4.1.6.5 Fase 4: Reporte, revisión y cierre de caso***

R1. Se diseñó el informe por caso con identificación y autorización, alcance, fuentes e IDs, herramientas y comandos, inventario de hashes, custodia, metodología, cronología, hallazgos, hipótesis alternativas y respuesta a cada pregunta forense.

R2. Se incorporaron al formato tablas before/after, referencias cruzadas a la evidencia original y anexos de manifiestos, transferencias, bitácoras y scripts. Se separaron de forma explícita hechos observados, inferencias y preguntas abiertas.

R3. Se definieron apartados de mejora sobre permisos, registros, protección de auditoría, retención y sincronización horaria, además de una revisión por un segundo integrante antes del cierre del expediente.

R4. Se estandarizó el cierre mediante índice, última verificación de hashes, ubicación de originales, custodio, fecha, versión del informe y pendientes. Se estableció la conservación de evidencias hasta una decisión de retención debidamente documentada.

### **4.1.7 Cadena de custodia, trazabilidad y estructura del expediente**

La cadena de custodia se integró desde la primera adquisición y se extendió a almacenamiento, transferencia, creación de copias, examen, análisis y entrega. Se estableció un identificador de evidencia asociado al caso (CASE-001/E-001), sin sustituir con él la verificación criptográfica ni el registro de origen y posesión. La ficha adoptada contiene ID del caso/evidencia, descripción, procedencia, ruta, formato, tamaño, SHA-256, hora UTC, adquirente, receptor, motivo del traspaso, estado, ubicación y constancias de entrega-recepción.

| Momento / acción | Registro obligatorio de custodia | Control de aceptación |
| :---- | :---- | :---- |
| Adquisición | ID, fuente, operador, herramienta, fecha, ubicación, tamaño, SHA-256. | Archivo completo; errores declarados; hash registrado. |
| Resguardo | Custodio, ruta restringida, permisos, fecha y estado del original. | Solo acceso autorizado; inventario vigente. |
| Copia / transferencia | Origen/destino, emisor/receptor, motivo, fecha/hora, nuevo SHA-256. | Coincidencia de hash con el manifiesto. |
| Examen y análisis | Analista, copia usada, herramientas/versiones, actividad y resultado. | Trabajo sobre copias; derivaciones identificadas. |
| Entrega / cierre | Informe, inventario final, custodio y última verificación. | Paquete reproducible con límites y pendientes. |

Se organizó la estructura de expedientes fuera del árbol Git en CASE-001/original/ (adquisiciones), CASE-001/trabajo/ (copias verificadas), CASE-001/custodia/ (manifiestos y actas), CASE-001/analisis/ (CSV y línea de tiempo) y CASE-001/reporte/ (informe). Se incorporaron controles de acceso y respaldo para los hashes y registros de custodia. Cada copia derivada o reexportación recibió un identificador diferenciado y quedó sujeta a cálculo de hash propio.

### **4.1.8 Criterios de aceptación y matriz de alineación con NIST SP 800-86**

Se elaboró la matriz de alineación metodológica con NIST SP 800-86 para relacionar cada actividad con su control y evidencia exigida, evitando equiparar el cálculo de SHA-256 con el cumplimiento integral. La arquitectura y el procedimiento incorporaron estos requisitos verificables; la comprobación de su ejecución, los resultados numéricos y las no conformidades se establecieron como parte de la validación del capítulo V.

| Referencia NIST SP 800-86 | Aplicación técnica documentada | Evidencia de verificación |
| :---- | :---- | :---- |
| §2.4–2.5 Política y roles | Se definieron la autorización, las responsabilidades, el alcance y la política de manejo de información. | Acta de caso y matriz de roles aprobadas. |
| §3.1.1 Fuentes | Se identificaron y priorizaron las fuentes de evidencia según relevancia y volatilidad. | Inventario F1-F6 y plan de adquisición. |
| §3.1.2 Recolección | Se incorporaron adquisición, SHA-256 y custodia de originales al procedimiento. | Logs, dump, SHA-256, acta y trazabilidad. |
| §3.1.3 Respuesta/contención | Se documentó la toma de decisiones de aislamiento y su efecto sobre las fuentes. | Registro de decisiones y efectos. |
| §3.2 Examen | Se establecieron análisis sobre copias y generación de derivados rastreables. | Bitácora, CSV derivados y hashes. |
| §3.3 Análisis | Se integraron correlación de fuentes, hipótesis alternativas y cronología. | Línea de tiempo con IDs y justificación. |
| §3.4 Reporte | Se estructuraron informes con método, limitaciones, hallazgos y recomendaciones. | Informe completo y revisión por pares. |
| §7 y §8 Aplicaciones y fuentes | Se integró el contraste de eventos de aplicación con logs y datos de MySQL. | Matriz de vínculos web/admin/API/MySQL. |

Se definieron cinco puertas de control de la implementación: G1, reproducibilidad del laboratorio y datos ficticios; G2, cobertura CREATE/UPDATE/DELETE en web, administración y API, incluido borrado masivo; G3, persistencia correcta de before/after y ausencia de eventos de éxito en transacciones revertidas; G4, adquisición con SHA-256 y custodia verificable; y G5, trazabilidad de la línea de tiempo e informe hacia los originales. El procedimiento de aceptación estableció registrar una no conformidad y repetir la prueba cuando no se satisfaga alguna puerta, sin declarar validación operativa anticipadamente.

Se preparó un protocolo de validación compuesto por pruebas positivas y negativas de cada canal, concurrencia y rollback, captura de IP y sesión con y sin proxy, prohibición de UPDATE/DELETE sobre AuditEvent desde el rol de ejecución, borrado administrativo masivo, detección de alteración de un byte mediante sha256sum \-c y reconstrucción independiente por un segundo analista. La tabla de verdad del guion se mantuvo conceptualmente separada de las evidencias para evitar sesgos en el examen.

## **4.2 Análisis de Alternativas de Solución (Evaluación TRELO)**

Se realizó la evaluación de tres alternativas mediante TRELO: Técnico, Riesgo, Económico, Legal y Organizacional. Se adoptó una escala de 1 a 5, donde 1 representó la condición menos favorable y 5 la más favorable; en el criterio Riesgo, 5 representó menor probabilidad de fracaso tecnológico. Antes de puntuar se fijaron los pesos: Técnico 30 %, Riesgo 25 %, Económico 15 %, Legal 15 % y Organizacional 15 %. Los puntajes reflejaron una valoración razonada del equipo y no resultados experimentales.

| Alternativa | Descripción / principal limitación |
| :---- | :---- |
| A. Logs nativos \+ procedimiento | Conservar mensajes INFO/admin y hacer adquisición; no reconstruye sistemáticamente before/after ni une API/web/admin. |
| B. Auditoría de aplicación \+ procedimiento NIST (elegida) | Instrumentar servicio transaccional, contexto de sesión, evidencia persistente, adquisición y correlación; exige desarrollo y pruebas. |
| C. Triggers/binlog MySQL \+ procedimiento | Observa modificaciones a nivel BD, pero no conoce por sí mismo cuenta/solicitud del CRM y encarece correlación. |

| Criterio (peso) | A | B | C |
| :---- | :---- | :---- | :---- |
| Técnico (30 %) | 2 | 5 | 3 |
| Riesgo (25 %) | 1 | 4 | 3 |
| Económico (15 %) | 5 | 4 | 3 |
| Legal (15 %) | 4 | 4 | 4 |
| Organizacional (15 %) | 4 | 4 | 2 |
| Total ponderado (máx. 5\) | 2,80 | 4,30 | 3,00 |

Se seleccionó la alternativa B porque respondía al objetivo de reconstruir las modificaciones y eliminaciones de cada cliente conservando vínculos de cuenta, canal y sesión, a diferencia de los registros nativos o del binlog por separado. Se mantuvo la distinción entre auditoría y control de acceso para limitar la exposición de datos. La evaluación económica consideró software de código abierto y equipos existentes, pero no asignó cifras monetarias ni un ROSI calculado sin datos sobre horas invertidas, frecuencia de incidentes y pérdidas evitadas. Se dejó documentada la fórmula ROSI \= (pérdida anual esperada evitada – costo anual del control) / costo anual del control para un cálculo posterior sustentado.

En el componente legal y organizacional se optó por datos ficticios y autorización académica para el laboratorio. Se dejó establecido que una futura utilización de datos personales reales exigiría evaluar la Ley peruana N.º 29733 y su reglamentación vigente, además de políticas de retención, acceso y autorizaciones, antes de recopilar o divulgar evidencias. El uso de NIST SP 800-86 no se consideró sustituto de esa evaluación legal.

## **4.3 Plan de Gestión de los Riesgos**

Se elaboró una matriz de riesgos que integró amenazas al desarrollo técnico y a la integridad y credibilidad del expediente. Se utilizó una escala de Probabilidad (P) e Impacto (I) de 1 a 5 y un índice de severidad P × I, con niveles bajo (1–5), medio (6–11), alto (12–19) y crítico (20–25). Para cada riesgo se asignó un responsable, una mitigación y una meta de exposición residual. La eficacia residual se reservó a las pruebas y no se dio por demostrada solo por haber diseñado el control.

| Riesgo (P × I) | Nivel inicial | Medidas de mitigación incorporadas al plan | Responsable / residual meta |
| :---- | :---- | :---- | :---- |
| R1. Ruta CRUD sin auditar (4×5=20) | Crítico | Se estableció servicio único y cobertura de web/admin/API, incluida eliminación masiva; bloqueo de integración ante fallos. | Líder backend / medio |
| R2. Eventos inconsistentes o perdidos (3×5=15) | Alto | Se diseñó la transacción conjunta y el rollback ante fallos; se definieron pruebas de concurrencia, duplicados y no-op. | Backend+QA / bajo |
| R3. Rotación o pérdida de logs (4×4=16) | Alto | Se documentó retención previa, adquisición antes de detener servicios e identificación de faltantes. | Infra+custodio / medio |
| R4. Manipulación de evidencias (3×5=15) | Alto | Se integraron original restringido, hash inmediato, manifiesto y custodia durante las transferencias. | Custodio / bajo |
| R5. Identificación errónea de actor/IP (3×4=12) | Alto | Se incorporó la distinción cuenta/persona, proxy confiable, UUID de sesión y correlación de fuentes. | Analista / medio |
| R6. Desfase horario (3×4=12) | Alto | Se adoptaron UTC, sincronización, registro de offsets y comprobación del orden temporal. | Infra+analista / bajo |
| R7. Datos sensibles o secretos en dump (3×4=12) | Alto | Se delimitaron datos ficticios, permisos mínimos, exclusión de tokens y protección de evidencias fuera de Git. | Custodio+backend / bajo |
| R8. Comparación A/B no equivalente (3×4=12) | Alto | Se adoptaron semillas y snapshots iniciales fijos, guion equivalente y registro de desviaciones. | QA+analista / bajo |
| R9. Exceso de afirmaciones forenses (3×4=12) | Alto | Se exigió separar hechos e inferencias, considerar hipótesis y revisar los informes independientemente. | Líder forense / bajo |

Se incorporaron cuatro hitos de seguimiento de riesgos: antes de la simulación, al completar la instrumentación, después de la adquisición y antes de emitir el informe. Se estableció un mecanismo de escalamiento que ordena detener la evaluación del caso ante operaciones confirmadas sin auditoría, hashes discrepantes o pérdida de originales, abrir incidencia, preservar lo disponible y declarar el límite. El cierre de cada incidencia quedó condicionado a documentar el control y repetir la verificación, sin alterar silenciosamente los archivos adquiridos.

## **4.4 Aseguramiento de la entrega de valor**

La entrega de valor se estructuró alrededor de una capacidad técnica de reconstrucción trazable de modificaciones y eliminaciones indebidas en un CRM de laboratorio. Esta capacidad se concretó en la instrumentación documentada, los procedimientos de adquisición, la custodia y las reglas de correlación, vinculados a los indicadores definidos en el capítulo III. La eficacia, el ahorro y la cobertura real no se presentaron como hechos demostrados antes de las pruebas del capítulo V.

| Objetivo vinculado | Entregable tangible | Criterio de aceptación / evidencia |
| :---- | :---- | :---- |
| OE1. Entorno | Dos despliegues aislados, seed ficticio y guion de operaciones. | SHA de commit, inventario, baseline y datos iniciales equivalentes. |
| OE2. Preparación forense | Módulo AuditEvent, middleware y servicio web/admin/API. | Evento completo por operación confirmada, con before/after y correlación. |
| OE3. Preservación | Procedimiento, archivos adquiridos, manifiesto SHA-256 y cadena de custodia. | Verificación consistente y registro de cada transferencia. |
| OE4. Reconstrucción | Dataset examinado, línea de tiempo e informe por incidente. | Cada conclusión enlaza evidencias con ID, fuente y limitación. |
| OE5. Comparación | Matriz A/B y métricas obtenidas del mismo guion. | Diferencia medible en operaciones reconstruibles sin inventar resultados. |

Se definieron para el capítulo V cinco métricas operativas: (i) cobertura de auditoría \= operaciones CRUD confirmadas con evento completo / operaciones CRUD confirmadas esperadas × 100; (ii) reconstrucción completa \= operaciones con actor, tiempo, canal, ID y before/after aplicables / operaciones del guion × 100, por separado en A y B; (iii) integridad de copias \= archivos con verificación SHA-256 coincidente / archivos examinados × 100; (iv) trazabilidad de custodia \= transferencias documentadas / transferencias realizadas × 100; y (v) tiempo de adquisición y de análisis por caso, obtenido de marcas registradas. Se fijaron como metas técnicas el 100 % de cobertura de operaciones del guion, el 100 % de integridad de copias examinadas y el 100 % de transferencias documentadas, sin anticipar ni modificar los valores que se midan.

Se identificaron como beneficios intangibles la mejora de transparencia de la auditoría, la delimitación de evidencias disponibles y la posibilidad de transferir un procedimiento repetible entre investigadores. También se registraron costos potenciales de desarrollo, almacenamiento, escritura de AuditEvent y capacitación. El balance de costos y beneficios se dejó sujeto a evaluación empírica, sin presentar un retorno económico todavía no medido.

Se consolidó una estructura de entregables para el capítulo IV integrada por: (1) repositorio en una rama propia con commit trazable, (2) configuración y dataset reproducibles, (3) módulo de auditoría y pruebas definidas, (4) procedimiento de adquisición ejecutable, (5) expediente con manifiestos y actas de custodia, y (6) formato de informe y matriz de comparación. La aceptación metodológica se vinculó a las puertas G1–G5 y al registro de no conformidades. Los resultados observados, las desviaciones y la discusión experimental se reservaron de forma expresa al capítulo V.

# **Referencias**

504ensics Labs. (s. f.). LiME: Linux Memory Extractor \[Software\]. GitHub. https\://github.com/504ensicsLabs/LiME

Azahari, A., & Balzarotti, D. (2024). On the inadequacy of open-source application logs for digital forensics. Forensic Science International: Digital Investigation, 49, Artículo 301750\. https\://doi.org/10.1016/j.fsidi.2024.301750

Brezinski, D., & Killalea, T. (2002). Guidelines for evidence collection and archiving (RFC 3227). Internet Engineering Task Force. https\://doi.org/10.17487/RFC3227

Carrier, B. (2005). File system forensic analysis. Addison-Wesley.

ChakerChourouk. (s. f.). Django-CRM \[Repositorio de código\]. GitHub. https\://github.com/ChakerChourouk/Django-CRM

Daubner, L., Buhnova, B., & Pitner, T. (2024). Forensic experts' view of forensic-ready software systems: A qualitative study. Journal of Software: Evolution and Process, 36(5), Artículo e2598. https\://doi.org/10.1002/smr.2598

Django Software Foundation. (s. f.-a). Source code for django.contrib.admin.models. Django Documentation. https\://docs.djangoproject.com/en/5.0/\_modules/django/contrib/admin/models/

Django Software Foundation. (s. f.-b). Signals. Django Documentation. https\://docs.djangoproject.com/en/stable/topics/signals/

Django Software Foundation. (s. f.-c). QuerySet API reference: update(). Django Documentation. https\://docs.djangoproject.com/en/5.2/ref/models/querysets/\#update

Docker Inc. (s. f.). Storage drivers. Docker Docs. https\://docs.docker.com/engine/storage/drivers/

Farfán Chiun, J. E. (2024). ISO 27037:2012 para mejorar el análisis informático forense en la División de Investigación de Delitos de Alta Tecnología de la Policía Nacional del Perú, Lima 2022 \[Tesis de maestría, Universidad Nacional Federico Villarreal\]. Repositorio Institucional UNFV. https\://hdl.handle.net/20.500.13084/9138

Frühwirt, P., Kieseberg, P., Schrittwieser, S., Huber, M., & Weippl, E. (2013). InnoDB database forensics: Enhanced reconstruction of data manipulation queries from redo logs. Information Security Technical Report, 17(4), 227–238. https\://www\.sciencedirect.com/science/article/abs/pii/S1363412713000137

Gladyshev, P., & Patel, A. (2004). Finite state machine approach to digital event reconstruction. Digital Investigation, 1(2), 130–149. https\://doi.org/10.1016/j.diin.2004.03.001

International Organization for Standardization & International Electrotechnical Commission. (2012). Information technology — Security techniques — Guidelines for identification, collection, acquisition and preservation of digital evidence (ISO/IEC 27037:2012). ISO.

International Organization for Standardization & International Electrotechnical Commission. (2015). Information technology — Security techniques — Incident investigation principles and processes (ISO/IEC 27043:2015). ISO.

Kent, K., & Souppaya, M. (2006). Guide to computer security log management (NIST Special Publication 800-92). National Institute of Standards and Technology. https\://doi.org/10.6028/NIST.SP.800-92

Kent, K., Chevalier, S., Grance, T., & Dang, H. (2006). Guide to integrating forensic techniques into incident response (NIST Special Publication 800-86). National Institute of Standards and Technology. https\://doi.org/10.6028/NIST.SP.800-86

Ligh, M. H., Case, A., Levy, J., & Walters, A. (2014). The art of memory forensics: Detecting malware and threats in Windows, Linux, and Mac memory. Wiley.

Mayta Avalos, C., Rosales Castilla, F., & Gines Colana, M. (2022). Trazabilidad de operaciones en base de datos para mitigar riesgos en los procesos de auditoría. Innovación y Software, 3(2), 40–51. https\://doi.org/10.48168/innosoft.s9.a58

National Institute of Standards and Technology. (2015). Secure Hash Standard (SHS) (FIPS PUB 180-4). https\://doi.org/10.6028/NIST.FIPS.180-4

Olegård, J., Axelsson, S., & Li, Y. (2025). When is logging sufficient? Tracking event causality for improved forensic analysis and correlation. Forensic Science International: Digital Investigation, 52, Artículo 301877\. https\://doi.org/10.1016/j.fsidi.2025.301877

Oracle. (s. f.). The binary log. MySQL 8.4 Reference Manual. https\://dev.mysql.com/doc/refman/8.4/en/binary-log.html

Pasquale, L., Alrajeh, D., Peersman, C., Tun, T., Nuseibeh, B., & Rashid, A. (2018). Towards forensic-ready software systems. En Proceedings of the 40th International Conference on Software Engineering: New Ideas and Emerging Results (pp. 9–12). ACM. https\://doi.org/10.1145/3183399.3183426

Rowlingson, R. (2004). A ten step process for forensic readiness. International Journal of Digital Evidence, 2(3), 1–28. https\://www\.utica.edu/academic/institutes/ecii/publications/articles/A0B13342-B4E0-1F6A-156F501C49CF5F51.pdf

Schneier, B., & Kelsey, J. (1999). Secure audit logs to support computer forensics. ACM Transactions on Information and System Security, 2(2), 159–176. https\://doi.org/10.1145/317087.317089

Verizon. (2026). 2026 Data breach investigations report. [https\://www\.verizon.com/business/resources/T158/reports/2026-dbir-data-breach-investigations-report.pdf](https://www.verizon.com/business/resources/T158/reports/2026-dbir-data-breach-investigations-report.pdf)

Australian Signals Directorate’s Australian Cyber Security Centre. (2024, 22 de agosto). Best practices for event logging and threat detection. https\://www\.cyber.gov.au/business-government/detecting-responding-to-threats/event-logging/best-practices-for-event-logging-and-threat-detection

Shier, J., Gunn, A., & Wood, H. (2025, 2 de abril). It takes two: The 2025 Sophos Active Adversary Report. Sophos. https\://www\.sophos.com/en-us/blog/2025-sophos-active-adversary-report

[image1]: <data:image/png;base64,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>