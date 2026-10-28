# Registro de prompts

Registro del uso de asistencia de IA según la Sección 14.8 y Apéndice A.5 del Taller MCP 3.

## 2026-10-26 — Gemini / Antigravity — Inicialización SDD
**Prompt:** "Para hacer cambios, primero, necesito crear una nueva branch... Para agregar una BD de MONDO DB, luego te paso el PDF... Contexto y Prioridades: Estamos trabajando en la rama activa feature/mongodb-integration... Metodología Spec Driven Development (SDD)..."
**Resultado:** Creación y push de rama `feature/mongodb-integration`, análisis integral del documento "Taller MCP 3", creación de `CLAUDE.md`, inicialización de `docs/prompts.md` y redacción de `specs/01-mongodb/spec.md`.
**Qué corregí:** Se fijó la obligatoriedad estricta de no tocar la funcionalidad existente de la app web y servidor MCP actual hasta que las nuevas capas estén especificadas y probadas.
**Aprendizaje:** Seguir el flujo SDD evita roturas tempranas en el código preexistente de taller 2.2.
