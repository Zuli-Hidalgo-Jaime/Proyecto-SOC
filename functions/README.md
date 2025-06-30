# Functions - Azure Functions (Python)

Esta carpeta contiene funciones serverless para procesamiento de tickets, embeddings y voz.

## Estructura

- `function_app.py`: Entry point de ejemplo para Azure Functions.
- `embeddings_function/`: Función para procesar y almacenar embeddings en Redis.
- `twilio_elevenlabs_function/`: Función para integración de llamadas (Twilio + ElevenLabs).
- `redis_utils.py`: Utilidad para conexión a Redis.
- `settings.py`: Configuración de entorno.

## Pasos para trabajar en Functions

1. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Configura los secretos y variables de entorno en `local.settings.json` o como variables de entorno del sistema.
3. Completa la lógica de cada función siguiendo los TODOs y docstrings en los archivos.
4. Prueba las funciones localmente usando Azure Functions Core Tools:
   ```bash
   func start
   ```
5. Cuando todo funcione, despliega las funciones en Azure.

## Consejos

- Usa los TODOs y docstrings como guía para saber qué falta implementar.
- Si integras servicios externos (Twilio, ElevenLabs, OpenAI, Redis), revisa la documentación oficial.
- Si tienes dudas, pregunta a tu mentor/a. 