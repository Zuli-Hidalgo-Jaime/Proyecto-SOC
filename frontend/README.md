# Frontend - Webapp de Gestión de Tickets

Esta carpeta contiene la interfaz web para crear, listar y consultar tickets. Está pensada para ser sencilla de modificar y entender.

## Estructura

- `index.html`: Página principal con tabla de tickets.
- `create-ticket.html`: Formulario para crear un ticket nuevo.
- `ticket-detail.html`: Página de detalle de ticket.
- `css/`: Estilos CSS.
- `js/`: Scripts JavaScript.
- `assets/`: Imágenes y recursos estáticos.

## Pasos para trabajar en el frontend

1. Abre `index.html` en tu navegador para ver la webapp.
2. Si quieres hacer cambios, edita los archivos HTML, CSS o JS según lo que necesites.
3. Para desarrollo local, puedes usar un servidor simple:
   ```bash
   python -m http.server 8000
   # o
   npx serve .
   ```
4. El frontend se conecta al backend FastAPI en `http://localhost:8000` por defecto. Si tu backend está en otra URL, cambia la variable en `js/config.js`.
5. Usa la referencia visual de ServiceNow para inspirarte en los estilos y disposición de los elementos.

## Consejos

- Mantén el código ordenado y usa los comentarios para entender cada parte.
- Si agregas nuevas páginas o componentes, sigue la misma estructura y estilo.
- Consulta a tu mentor/a si tienes dudas sobre cómo conectar el frontend con el backend.

## Características

- Tabla responsive de tickets con filtros
- Formulario de creación de tickets
- Vista detallada de tickets individuales
- Interfaz inspirada en ServiceNow
- Consumo de API REST del backend

## Uso

1. Abrir `index.html` en navegador web
2. Para desarrollo local, usar servidor HTTP:
   ```bash
   python -m http.server 8000
   # o
   npx serve .
   ```

## Configuración

El frontend se conecta al backend FastAPI en `http://localhost:8000` por defecto.
Modificar la URL base en `js/config.js` si es necesario. 