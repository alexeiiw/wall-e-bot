# Plan de mejora del router y reducción de uso del LLM

## Objetivo

Reducir el uso del modelo local (Ollama) para consultas que no aportan valor a la intención del bot, evitando llamadas innecesarias al LLM y manteniendo la experiencia útil para tareas personales, notas y recordatorios.

La idea principal es esta:

- El router debe decidir primero la intención del mensaje.
- Solo los casos realmente valiosos deben activar el LLM.
- Las tareas estructuradas y locales deben resolverse sin modelo.
- Las consultas fuera del dominio del bot deben responderse con una respuesta clara o una herramienta externa, no con un prompt al LLM.

---

## Problema actual

El sistema ya tiene un router de intenciones con lógica determinista, pero todavía la mayoría de las consultas no estructuradas van directamente al LLM. Eso significa que una pregunta trivial o fuera de contexto puede consumir tokens sin necesidad.

Este patrón es el punto que hay que corregir.

---

## Cambio propuesto

### 1. Mejorar el router para clasificar por dominio

El router debe evaluar cada mensaje y asignarle una de estas categorías:

1. Comando local estructurado
   - guardar memoria
   - guardar nota
   - listar notas
   - buscar notas
   - resumir notas

2. Consulta sobre contenido personal
   - preguntas sobre notas, recordatorios, ideas o datos almacenados

3. Consulta de chat general
   - conversación normal con el bot
   - explicación, redacción o ideas generales

4. Consulta fuera de alcance
   - clima
   - noticias
   - datos en tiempo real
   - hechos externos no disponibles localmente

5. Necesita herramienta externa
   - APIs, búsqueda web, clima, calendario, etc.

6. Consulta trivial o no útil para el LLM
   - saludos, confirmaciones, frases breves, mensajes sin intención clara

La clave es que estas categorías no deben depender solo de regex; deben estar organizadas por tipo de tarea.

---

### 2. Reducir el número de mensajes que llegan al LLM

Se deben excluir del LLM estas clases:

- saludos simples
- mensajes de confirmación
- preguntas de clima sin integración real
- consultas que no forman parte del dominio del asistente
- mensajes demasiado breves y sin contexto relevante

En lugar de enviar esas consultas al modelo, el bot debe responder con una respuesta directa o con una indicación de que no puede resolver ese tipo de solicitud aquí.

---

### 3. Mantener el LLM solo en casos con valor real

El modelo local debe usarse principalmente para:

- resumir información personal
- responder con memoria del usuario
- ayudar con contenido de notas e ideas
- responder en estilo conversacional cuando sí aporta valor

No tiene sentido usar el LLM como “fallback universal” para toda consulta.

---

### 4. Añadir una capa de “fuera de alcance”

Esto es clave.

El bot debe reconocer cuando una consulta no corresponde a su dominio y responder de forma honesta, por ejemplo:

- “No tengo acceso al clima en tiempo real.”
- “No puedo consultar noticias desde aquí.”
- “Eso está fuera de mi alcance actual.”
- “Puedo ayudarte con tus notas, recordatorios o tareas personales.”

Esto evita que el modelo local intente adivinar algo que no puede resolver correctamente.

---

### 5. Separar intención, recuperación y generación

La lógica debe quedar organizada en tres etapas:

1. Clasificación de la intención
2. Recuperación de contexto o datos
3. Generación de la respuesta

Esto permite que una petición de búsqueda o resumen haga solo lo necesario y no se convierta automáticamente en un chat completo con LLM.

---

## Casos de ejemplo

### Caso A: consulta personal

Mensaje: “¿Qué tengo sobre proyecto X?”

Resultado esperado:
- identificar que es una búsqueda en contenido personal
- buscar en notas
- devolver resultados directos o resumir si hace falta
- solo usar LLM si el resultado requiere síntesis

### Caso B: resumen

Mensaje: “Resúmeme mis notas”

Resultado esperado:
- reconocer que es una tarea de resumen
- cargar notas
- mandar solo ese texto al LLM para resumir

### Caso C: conversación abierta

Mensaje: “Explícame esto de otra forma”

Resultado esperado:
- reconocer que es chat general
- usar el LLM con contexto del usuario si existe

### Caso D: consulta externa

Mensaje: “¿Qué clima será hoy?”

Resultado esperado:
- identificar que es herramienta externa o fuera de alcance
- no usar el LLM como sustituto de servicio meteorológico
- responder con limitación o llamar a una API si existe

### Caso E: saludo

Mensaje: “Hola”

Resultado esperado:
- no enviar al LLM
- responder con un saludo o una respuesta simple

---

## Beneficios esperados

- menor consumo de tokens
- más velocidad de respuesta
- mejor claridad de la lógica del bot
- menos abuso del LLM para tareas triviales
- mejor separación entre manejo local, contenido personal y chat abierto

---

## Alcance recomendado

Este cambio no necesita ser un rediseño completo.

Lo ideal es:

- mantener la arquitectura actual
- reforzar el router
- añadir una categoría de consultas fuera de alcance
- mover algunas tareas de LLM a respuestas directas o herramientas

Esto es suficiente para obtener el beneficio sin riesgo ni gasto innecesario de tiempo.

---

## Orden recomendado de trabajo

1. Definir categorías de intención
2. Añadir filtro de consultas fuera de alcance
3. Reordenar prioridad del router
4. Reducir llamadas al LLM en consultas simples
5. Dejar solo el LLM en casos de alto valor
6. Validar con una batería de ejemplos reales

---

## Conclusión

El cambio principal no es reemplazar el router por uno más complejo, sino hacer que el router sea realmente “decision-aware”: decide si una consulta necesita contexto local, herramienta externa, resumen o respuesta directa antes de invocar el LLM.

Eso es lo que reduce el consumo de tokens sin destruir la utilidad del bot.
