# Indice del corpus RAG (generado por rag/construir_corpus.py)

Generado: 2026-10-18. Fuentes: ver cabecera de cada fragmento.

| Documento | Fragmentos | Caracteres | sha256 |
|---|---:|---:|---|
| 01-metodologia-score.md | 10 | 6231 | `c53566db359878c879381f4135874101f55508e3c00b6b37bb17f1008c10f993` |
| 01-nota-discrepancias.md | 1 | 990 | `f18360f3a5501da699816674b4f0d496eafdf5623513cfd4207a1462a3b64894` |
| 02-ipm-conpes-150.md | 7 | 3483 | `a736ae00a5de2f68449c9c28ce97180a0de64a8281d5053645527168fadba2c6` |
| 03-glosario.md | 10 | 3820 | `67a4661b35b3673f730e7422f07e29920088a7466f779f08773777818c9f214e` |
| 04-decisiones-fuentes-metodos.md | 9 | 6370 | `47e3fe0da907a307a7e1e1dc72510aa3dcf98b576907d2a91e0bbcb3e64ac8e9` |
| 05-divipola.md | 5 | 2352 | `f7dad77ad412543c063babf6e0714a405d73c8d64a8764c01e242e3b8cef4892` |
| 06-guia-uso.md | 3 | 1344 | `3202c58e031d794c9ab9b24094f3173ef248b4480ff8a7ad2756d967db944225` |
| **Total** | **45** | **24590** | |

PDF del CONPES 150 usado (no versionado): https://colaboracion.dnp.gov.co/CDT/Conpes/Social/150.pdf
sha256 del PDF: `22bc8b48cad011e3974082ae21f70fbf2be20b3f715724f2f127bcb643af89fa`

## Huecos anotados

- Glosario: no hay texto fuente en los repos con la definicion oficial de cobertura de acueducto ni de alcantarillado (DANE/SSPD/DNP); no se inventa. Pendiente de aprobacion de una fuente publica.
- Glosario: la densidad poblacional solo tiene la formula del proyecto (poblacion DANE / area), no una definicion oficial.
- Guia de uso (#6): no existe README de usuario; solo reglas del prompt, comentarios del frontend y estados de mensaje. No hay texto fuente que describa el mapa de calor ni el panel en lenguaje de usuario.
- IPM: solo CONPES Social 150 (2012). Las actualizaciones posteriores del IPM (p. ej. DANE 2018) no estan en el corpus.
