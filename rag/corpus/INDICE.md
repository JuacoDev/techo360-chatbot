# Indice del corpus RAG (generado por rag/construir_corpus.py)

Generado: 2026-10-19. Fuentes: ver cabecera de cada fragmento.

| Documento | Fragmentos | Caracteres | sha256 |
|---|---:|---:|---|
| 01-metodologia-score.md | 9 | 5307 | `74e376c91fef0323f4a8e8837c32f2b2fe6c570aeb52d14a95a379632f38f200` |
| 02-ipm-conpes-150.md | 6 | 3318 | `5273e92acbb943d83876f54b4bb2071eed65eb645f4b132ceeb059259adcac48` |
| 03-glosario.md | 9 | 3150 | `bcce085d95becb05073937659ce2077bd62fbe2dec411287862ebaf507501901` |
| 04-decisiones-fuentes-metodos.md | 7 | 4798 | `f1d1efdc2c85e1e7f9d930d4c0c6c99f3d2d21805ec075f2f4babcb9f130a45c` |
| 05-divipola.md | 5 | 1945 | `c307ad1c9c3cb534b55c775d22e26f583cf444bac8bd6797decddd74f2ef901e` |
| 06-guia-uso.md | 6 | 1509 | `c916592064b94eaf5327ac4d57fb6947046e4edfe19bd9e0592695815e81ea26` |
| **Total** | **42** | **20027** | |

PDF del CONPES 150 usado (no versionado): https://colaboracion.dnp.gov.co/CDT/Conpes/Social/150.pdf
sha256 del PDF: `22bc8b48cad011e3974082ae21f70fbf2be20b3f715724f2f127bcb643af89fa`

## Huecos anotados

- Glosario: no hay texto fuente en los repos con la definicion oficial de cobertura de acueducto ni de alcantarillado (DANE/SSPD/DNP); no se inventa. Pendiente de aprobacion de una fuente publica.
- Glosario: la densidad poblacional solo tiene la formula del proyecto (poblacion DANE / area), no una definicion oficial.
- Guia de uso (#6): no existe README de usuario; solo reglas del prompt, comentarios del frontend y estados de mensaje. Solo hay texto fuente para la escala y el semaforo del mapa (06-leyenda-escala, 06-mapa-semaforo); no lo hay para el panel en lenguaje de usuario.
- Prioridad alta: no hay categorias ni punto de corte (confirmado por Juan, 19-oct-2026); ver 06-prioridad y rag/PENDIENTES_JUAN.md.
- Mapa: las notas de la leyenda (deficit constante, fiabilidad al pasar el cursor) solo existen en JSX, sin prosa fuente; no se incluyeron. El gris lo cubre 06-mapa-gris (frase aprobada por Juan).
- IPM: solo CONPES Social 150 (2012). Las actualizaciones posteriores del IPM (p. ej. DANE 2018) no estan en el corpus.
