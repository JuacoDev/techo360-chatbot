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
