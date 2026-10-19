---
fragmento: 05-codigos-oficiales
fuente: Proyecto Techo 360 - fase1-2-divipola-cruce.md
ruta: claude/fase1-2-divipola-cruce.md
fecha: 2026-10-16
vigencia: DIVIPOLA DANE actualizado al 30-jun-2026
version: sin-control-de-versiones (mtime)
tema: Codigos DIVIPOLA oficiales: 1.122 codigos y sus tipos
---
Hoja `Municipios`: **1 122 códigos de 5 dígitos, todos distintos**, con prefijo de departamento válido (33 códigos de departamento = 32 + Bogotá D.C.).

| Tipo (columna «Tipo») | Códigos |
|---|---:|
| Municipio | 1 103 |
| Isla (San Andrés, 88001) | 1 |
| Área no municipalizada | 18 |
| **Total** | **1 122** |

---
fragmento: 05-areas-no-municipalizadas
fuente: Proyecto Techo 360 - fase1-2-divipola-cruce.md
ruta: claude/fase1-2-divipola-cruce.md
fecha: 2026-10-16
vigencia: DIVIPOLA DANE actualizado al 30-jun-2026
version: sin-control-de-versiones (mtime)
tema: Las 18 areas no municipalizadas sin poligono en el mapa
---
**18 códigos en DIVIPOLA sin geometría en el geojson.** Son exactamente las 18 «áreas no municipalizadas»:

| Departamento | Códigos |
|---|---|
| Amazonas (9) | 91263 El Encanto, 91405 La Chorrera, 91407 La Pedrera, 91430 La Victoria, 91460 Mirití-Paraná, 91530 Puerto Alegría, 91536 Puerto Arica, 91669 Puerto Santander, 91798 Tarapacá |
| Guainía (6) | 94883 San Felipe, 94884 Puerto Colombia, 94885 La Guadalupe, 94886 Cacahual, 94887 Pana Pana, 94888 Morichal |
| Vaupés (3) | 97511 Pacoa, 97777 Papunahua, 97889 Yavaraté |

---
fragmento: 05-caso-00000
fuente: Proyecto Techo 360 - zonas.py
ruta: techo360-backend/routers/zonas.py
fecha: 2026-10-10
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@f10a0e0
tema: El codigo 00000: Area en Litigio Cauca-Huila
---
"Area En Litigio Cauca - Huila": existe como poligono en zonas_municipio
(codigo '00000') y en zonas_departamento (codigo '00'), pero no es un
municipio ni un departamento reales -- DANE no le asigna codigo propio
y mapcalordb no tiene ninguna fila para ella (verificado en produccion,
4-oct-2026). Se excluye de la respuesta para que no aparezca en el mapa
ni en los selectores. Es un filtro de lectura: NO se borra ninguna fila
de zonas_municipio / zonas_departamento (el ETL de zonas la repone).

---
fragmento: 05-nombres-distintos
fuente: Proyecto Techo 360 - fase1-2-divipola-cruce.md
ruta: claude/fase1-2-divipola-cruce.md
fecha: 2026-10-16
vigencia: DIVIPOLA DANE actualizado al 30-jun-2026
version: sin-control-de-versiones (mtime)
tema: Nombre oficial frente a nombre corto en los mismos codigos
---
**Nombres.** En los 1 104 códigos comunes hay **22** pares con nombre distinto tras normalizar mayúsculas y tildes, por ejemplo 05148 «EL CARMEN DE VIBORAL» (DANE) vs «Carmen De Viboral» (IGAC), 88564 «PROVIDENCIA» vs «Providencia y Santa Catalina», 52835 «SAN ANDRÉS DE TUMACO» vs «Tumaco». Son diferencias de nombre oficial vs nombre corto, no de código. Lista completa reproducible con el script. COMPROBADO el conteo; que todas sean solo de formato es lectura mía de la muestra de 22.

---
fragmento: 05-join-por-codigo
fuente: Proyecto Techo 360 - CLAUDE.md
ruta: CLAUDE.md
fecha: 2026-10-16
vigencia: vigente en el codigo de la rama revisada
version: sin-control-de-versiones (mtime)
tema: Regla: unir siempre por codigo DIVIPOLA, nunca por nombre
---
- **Join por `codigoDivipola`, nunca por nombre de municipio** — nombres duplicados
  entre municipios reales distintos (ej. "Sabanalarga") ya causaron un bug real de
  UPDATE cruzado. La tabla `zonas_municipio` (1,105 filas, capa canónica IGAC) es la
  referencia contra la que se audita "qué municipio existe de verdad" para el mapa —
  hay ~20 códigos DANE reales (corregimientos departamentales de Amazonas/Guainía/
  Vaupés) que NO están en esa capa; es un desalineamiento real documentado, no basura
  a limpiar sin más.
