# Infraestructura como Código (IaC)

Esta carpeta contiene los scripts y plantillas para desplegar la infraestructura del sistema en Azure usando Bicep y Terraform.

## Estructura

- `main.bicep`: Plantilla principal Bicep para recursos en Azure
- `main.tf`, `variables.tf`, `outputs.tf`: Plantillas principales Terraform
- `azuredeploy.parameters.json`: Ejemplo de parámetros para despliegue Bicep
- `modules/`: Submódulos reutilizables para App Service, PostgreSQL, Redis, OpenAI, Storage y Functions (en Bicep y Terraform)

## Pasos para desplegar la infraestructura

1. Lee y adapta las plantillas Bicep o Terraform según tu suscripción y necesidades.
2. Despliega los recursos principales en Azure:
   - App Service (o Static Web App)
   - PostgreSQL Flexible Server
   - Azure Redis Enterprise
   - Azure OpenAI Resource
   - Azure Functions
   - Storage Account (si aplica)
3. Guarda los endpoints y cadenas de conexión generados para usarlos en el backend y functions.
4. Configura los secretos y variables de entorno en Azure Key Vault o como variables protegidas en tu pipeline.

## Consejos

- Trabaja primero en un entorno de pruebas antes de desplegar en producción.
- Consulta la documentación oficial de Azure Bicep y Terraform si tienes dudas.
- Si tienes problemas, pregunta a tu mentor/a. 