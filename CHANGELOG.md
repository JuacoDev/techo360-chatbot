# Changelog

La numeracion es una reconstruccion documental del historial y de PRs fusionados. No existen tags semanticos oficiales para estas versiones.

## Sin publicar

### 0.4.1

- Dataset 0.4.1 y trabajo de RAG posteriores al entrenamiento 0.4.0.
- System prompt de entrenamiento previsto: `sp-0.4.1-1`.
- TODO: fijar commit, dataset, artefacto y comando reproducible de 0.4.1.

## 0.4.0

- Dataset base (PR #12), system prompt `sp-0.4.0-1` (PR #16), entrenamiento (PR #18) y evaluacion (PR #19).
- Se documentan LoRA/QLoRA, empaquetado GGUF y evaluaciones de alucinacion, fidelidad y memoria.
- TODO: no existe tag de release ni artefacto desplegado rastreable desde este repo.

## 0.3.0

- Evolucion del servicio Ollama desde las versiones v3.2 y v3.3, con consumer RabbitMQ y persistencia.
- TODO: el historial no asigna formalmente v3.2/v3.3 a 0.3.0.

## 0.2.0

- Servicio conversacional con contrato RPC, migraciones de conversaciones/mensajes y cliente Ollama.
- TODO: identificar el commit exacto de 0.2.0; la evidencia disponible son PRs tempranos del repositorio.

## 0.1.0

- Base inicial del servicio FastAPI, consumer y persistencia del chatbot.
- TODO: identificar el commit exacto que debe representar 0.1.0.
