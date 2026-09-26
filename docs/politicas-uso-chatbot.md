# Políticas de uso — Chatbot Techo 360

Este documento describe qué pasa con las conversaciones que un usuario tiene
con el chatbot de Techo 360, y bajo qué condiciones ese contenido puede
usarse para mejorar el modelo. Aplica a las tablas `conversaciones` y
`mensajes` definidas en `migrations/0001_conversaciones_mensajes.sql`.

## Qué se guarda

Cada conversación queda registrada con:

- El identificador de la cuenta que la inició (`usuario_id`).
- Si esa cuenta había dado consentimiento para reentrenamiento en el
  momento de la conversación (`consentimiento_entrenamiento`).
- Cada mensaje intercambiado, con su rol (`usuario` o `asistente`) y su
  contenido completo, sin resumir ni truncar.
- Si el usuario marcó una respuesta como útil o no útil (`feedback_util`),
  cuando decide dar ese feedback.

## Uso para reentrenamiento

- Solo las conversaciones marcadas con `consentimiento_entrenamiento = true`
  entran como candidatas al dataset de reentrenamiento. Una conversación sin
  ese consentimiento nunca se usa para este fin, sin excepción.
- El consentimiento se registra por conversación, tomado de la cuenta en el
  momento en que ocurrió esa conversación. Si el usuario cambia su
  consentimiento después, eso no cambia retroactivamente las conversaciones
  ya guardadas — cada una conserva el estado que tenía cuando ocurrió.
- Del contenido de la conversación, se conserva el mensaje completo tal como
  el usuario lo escribió, sin editar ni recortar, para no introducir sesgos
  al preparar el dataset.

## Qué NO se incluye en el dataset de reentrenamiento

- El identificador de cuenta (`usuario_id`) **no se incluye** en el dataset
  exportado para reentrenar. El dataset no permite reconstruir qué cuenta
  dijo qué.
- No se agrega ninguna otra columna identificatoria (correo, nombre, etc.)
  al dataset — el proceso de exportación solo toma el contenido de los
  mensajes de conversaciones con consentimiento, nunca datos de la cuenta.

## Limitación conocida: PII voluntaria del usuario

Si un usuario escribe información personal identificable (nombre propio,
número de documento, dirección, teléfono, etc.) dentro del **contenido** de
su mensaje, esa información queda tal cual en el mensaje guardado, y por lo
tanto **podría terminar en el dataset de reentrenamiento** si esa
conversación tenía consentimiento — no hay un filtro automático de PII sobre
el contenido de los mensajes hoy.

Este documento no promete que el sistema detecte o elimine esa información:
la ausencia de identificador de cuenta protege quién dijo algo, no qué se
dijo. Si el usuario decide compartir un dato personal en el texto de su
mensaje, esa decisión es suya y el sistema no la revierte.

## Retención

Este documento no define todavía un plazo de borrado ni un proceso de
eliminación a solicitud del usuario — queda pendiente como trabajo aparte,
no cubierto por esta versión.
