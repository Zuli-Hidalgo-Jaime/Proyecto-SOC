# Tests

Esta carpeta contiene los tests unitarios y de integración para el backend y Azure Functions.

## Estructura sugerida

- `backend/`: Tests para la API FastAPI y lógica de negocio.
- `functions/`: Tests para las Azure Functions.

## Pasos para ejecutar y escribir tests

1. Instala las dependencias de testing en cada módulo (`pytest`, `pytest-asyncio`).
2. Para ejecutar los tests del backend:
   ```bash
   cd backend
   pytest
   ```
3. Para ejecutar los tests de functions:
   ```bash
   cd functions
   pytest
   ```
4. Agrega nuevos tests siguiendo los ejemplos y usando mocks para servicios externos.
5. Revisa los resultados y corrige los errores antes de avanzar.

## Consejos

- Escribe tests pequeños y enfocados en una sola funcionalidad.
- Usa mocks para simular servicios externos (Azure, Redis, Twilio, ElevenLabs).
- Si tienes dudas, pregunta a tu mentor/a.

## Notas

- Agrega mocks para servicios externos (Azure, Redis, Twilio, ElevenLabs) donde sea necesario.
- Usa `pytest` y `pytest-asyncio` para pruebas asíncronas. 