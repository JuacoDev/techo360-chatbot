# Indice del corpus RAG (generado por rag/construir_corpus.py)

Generado: 2026-10-19. Fuentes: ver cabecera de cada fragmento.

| Documento | Fragmentos | Caracteres | sha256 |
|---|---:|---:|---|
| 01-metodologia-score.md | 9 | 5307 | `74e376c91fef0323f4a8e8837c32f2b2fe6c570aeb52d14a95a379632f38f200` |
| 02-ipm-conpes-150.md | 6 | 3318 | `5273e92acbb943d83876f54b4bb2071eed65eb645f4b132ceeb059259adcac48` |
| 03-glosario.md | 9 | 3150 | `bcce085d95becb05073937659ce2077bd62fbe2dec411287862ebaf507501901` |
| 04-decisiones-fuentes-metodos.md | 7 | 4798 | `f1d1efdc2c85e1e7f9d930d4c0c6c99f3d2d21805ec075f2f4babcb9f130a45c` |
| 05-divipola.md | 5 | 1945 | `c307ad1c9c3cb534b55c775d22e26f583cf444bac8bd6797decddd74f2ef901e` |
| 06-guia-uso.md | 5 | 1136 | `81729d5233c46b0f13fceb5c09784bd46cba4053ba7235bb117648f57c5fb98f` |
| **Total** | **41** | **19654** | |

PDF del CONPES 150 usado (no versionado): https://colaboracion.dnp.gov.co/CDT/Conpes/Social/150.pdf
sha256 del PDF: `22bc8b48cad011e3974082ae21f70fbf2be20b3f715724f2f127bcb643af89fa`

## Huecos anotados

- Glosario: no hay texto fuente en los repos con la definicion oficial de cobertura de acueducto ni de alcantarillado (DANE/SSPD/DNP); no se inventa. Pendiente de aprobacion de una fuente publica.
- Glosario: la densidad poblacional solo tiene la formula del proyecto (poblacion DANE / area), no una definicion oficial.
- Guia de uso (#6): no existe README de usuario; solo reglas del prompt, comentarios del frontend y estados de mensaje. Solo hay texto fuente para la escala y el semaforo del mapa (06-leyenda-escala, 06-mapa-semaforo); no lo hay para el panel en lenguaje de usuario.
- Prioridad alta: ningun documento revisado define umbrales ni categorias (alta/media/baja) de prioridad. Solo existe la frase de la leyenda («1.0 indica la maxima prioridad o necesidad de intervencion»). Pendiente de Juan (ver rag/PENDIENTES_JUAN.md).
- Mapa: el gris de «Sin dato / Area en litigio» y las notas de la leyenda (deficit constante, fiabilidad al pasar el cursor) solo existen como constantes/JSX, sin prosa fuente; no se incluyeron.
- IPM: solo CONPES Social 150 (2012). Las actualizaciones posteriores del IPM (p. ej. DANE 2018) no estan en el corpus.
