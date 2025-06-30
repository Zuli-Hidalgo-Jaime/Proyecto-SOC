# ProyectoSoc - Sistema de Atención de Tickets con IA

Este repositorio contiene la base para desarrollar un sistema de gestión de tickets con automatización por voz e IA en Azure. Está diseñado para que puedas construir cada módulo paso a paso, incluso si es tu primer proyecto de este tipo.

## Estructura del repositorio

- `frontend/`: Webapp en HTML, CSS y JS puro para gestión de tickets.
- `backend/`: API REST en FastAPI (Python) con PostgreSQL y Redis para embeddings.
- `functions/`: Azure Functions en Python para procesamiento de embeddings y voz.
- `infra/`: Infraestructura como código (Bicep y Terraform) para desplegar en Azure.
- `scripts/`: Scripts de despliegue y utilidades.
- `docs/`: Documentación técnica y diagramas.
- `tests/`: Pruebas unitarias y de integración.

## Flujo de desarrollo recomendado

1. **Infraestructura**
   - Lee `infra/README.md` y adapta las plantillas Bicep/Terraform para tu suscripción de Azure.
   - Despliega los recursos principales: App Service, PostgreSQL, Redis Enterprise, Azure OpenAI, Functions y Storage.
   - Guarda los endpoints y cadenas de conexión generados.

2. **Backend**
   - Lee `backend/README.md` para entender la estructura y dependencias.
   - Configura el archivo `.env` con las variables de entorno necesarias (ver ejemplo en el README del backend).
   - Implementa los modelos, rutas y servicios siguiendo los TODOs y docstrings.
   - Asegúrate de que la API funcione localmente y pueda conectarse a PostgreSQL y Redis.

3. **Frontend**
   - Lee `frontend/README.md` para ver la estructura de la webapp.
   - Adapta los archivos HTML, CSS y JS para consumir la API del backend.
   - Ajusta los estilos y la experiencia de usuario según la referencia visual de ServiceNow.

4. **Azure Functions**
   - Lee `functions/README.md` para entender cómo funcionan las funciones serverless.
   - Implementa la lógica de embeddings y la integración con Twilio/ElevenLabs siguiendo los TODOs.
   - Prueba las funciones localmente y luego despliega en Azure.

5. **Pruebas**
   - Lee `tests/README.md` para saber cómo ejecutar y escribir pruebas.
   - Agrega tests unitarios y de integración para backend y functions.

6. **Documentación y scripts**
   - Usa la carpeta `docs/` para agregar diagramas, flujos y documentación técnica.
   - Agrega scripts útiles en `scripts/` para automatizar tareas comunes (deploy, setup local, etc).

## Consejos para avanzar

- Trabaja por módulos: termina y prueba cada parte antes de pasar a la siguiente.
- Usa los TODOs y docstrings como guía para saber qué falta implementar.
- Consulta la documentación oficial de cada tecnología si tienes dudas.
- Haz commits frecuentes y documenta tus cambios.
- Si tienes problemas, busca ejemplos en la web o pregunta a tu mentor/a.

## Configuración de secretos y variables

Recuerda nunca subir tus claves o contraseñas al repositorio. Usa variables de entorno o Azure Key Vault.

## Despliegue en Azure

Sigue los pasos de la carpeta `infra/` para desplegar la infraestructura. Luego, despliega el backend, frontend y functions usando los pipelines de CI/CD o manualmente.

---

Este repositorio es una base flexible: puedes adaptarlo y expandirlo según las necesidades del proyecto. Si tienes dudas, consulta los README de cada carpeta o pide ayuda a tu mentor/a.
