---
fragmento: 06-tarjeta-fiabilidad
fuente: Proyecto Techo 360 - fiabilidadTarjeta.js
ruta: techo360-frontend/src/components/fiabilidadTarjeta.js
fecha: 2026-10-16
vigencia: vigente en el codigo de la rama revisada
version: techo360-frontend@ea4f6b0
tema: Panel de indicadores: dato confirmado frente a proyeccion y su insignia de fiabilidad
---
Regla (misma que el resto del frontend): una tarjeta es PROYECCION si esProyeccionZona() lo dice (es_real=false o
originVar con prefijo "proyeccion-"); cualquier otro origen es dato confirmado y no lleva badge. El backend
reusa intervalo_confianza como % de fiabilidad. Devuelve el numero a mostrar o null (sin badge).

---
fragmento: 06-estado-mensajes
fuente: Proyecto Techo 360 - README.md
ruta: techo360-frontend/README.md
fecha: 2026-10-09
vigencia: vigente en el codigo de la rama revisada
version: techo360-frontend@85bba52
tema: TechoBot: estados de un mensaje
---
- Cada mensaje de usuario tiene estado: `pendiente`, `procesando`, `respondido`, `error` o `cancelado`. Si el backend no manda estado, se trata como `respondido`.

---
fragmento: 06-leyenda-escala
fuente: Proyecto Techo 360 - MapView.jsx
ruta: techo360-frontend/src/components/MapView.jsx
fecha: 2026-10-11
vigencia: vigente en el codigo de la rama revisada
version: techo360-frontend@c4b2896
tema: Que significa prioridad o necesidad de intervencion: escala de privacion de 0.0 a 1.0 de la leyenda del mapa
nota: Texto de la leyenda del mapa (tooltip «i» de «Escala de Privación»). No define un umbral de «prioridad alta».
---
Índice de 0.0 a 1.0 que promedia las carencias en acueducto, alcantarillado y déficit habitacional. Un valor de 1.0 indica la máxima prioridad o necesidad de intervención.

---
fragmento: 06-mapa-color-por-variable
fuente: Proyecto Techo 360 - variablesProyeccion.js
ruta: techo360-frontend/src/pages/Proyeccion/variablesProyeccion.js
fecha: 2026-10-16
vigencia: vigente en el codigo de la rama revisada
version: techo360-frontend@62ad33f
tema: Mapa de proyeccion: que significa mas rojo segun la variable (Score, deficit, tenencia informal, cobertura, densidad)
---
color:
  "directo"    el valor ya esta en [0, 1] (score).
  "porcentaje" valor/100: mas = mas rojo (deficit, tenencia informal).
  "invertido"  1 - valor/100: menos cobertura = mas rojo.
  "log"        escala logaritmica entre el minimo y el maximo POSITIVOS del año mostrado (densidad).

---
fragmento: 06-mapa-semaforo
fuente: Proyecto Techo 360 - MapView.jsx
ruta: techo360-frontend/src/components/MapView.jsx
fecha: 2026-10-11
vigencia: vigente en el codigo de la rama revisada
version: techo360-frontend@c4b2896
tema: Como interpretar el color de un municipio en el mapa: semaforo blanco, amarillo y rojo del Score
---
Semaforo del score de privacion (0=mejor, 1=peor): interpolacion
lineal por tramos entre tres puntos, blanco en 0, amarillo en 0.5,
rojo en 1 (decision de producto, no buckets absolutos como antes).
