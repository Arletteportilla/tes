# Sistema de Polinización y Germinación

Sistema web desarrollado en Django para gestionar y monitorear procesos de polinización y germinación de plantas.

## Características

- **Autenticación basada en roles**: Polinizador, Germinador, Secretaria, Administrador
- **Módulos especializados**: Polinización, Germinación, Alertas, Reportes
- **API REST**: Documentada con Swagger/OpenAPI
- **Sistema de alertas automáticas**: Notificaciones basadas en fechas
- **Generación de reportes**: Exportación en PDF y Excel
- **Arquitectura modular**: Apps Django independientes

## Tecnologías

- **Backend**: Django 4.2.7 + Django REST Framework
- **Base de datos**: PostgreSQL (SQLite para desarrollo)
- **Autenticación**: JWT con django-rest-framework-simplejwt
- **Documentación**: drf-spectacular (Swagger)
- **Tareas asíncronas**: Celery + Redis
- **Testing**: pytest-django + factory-boy

## Estructura del Proyecto

```
sistema_polinizacion/
├── authentication/          # Gestión de usuarios y roles
├── pollination/            # Módulo de polinización
├── germination/            # Módulo de germinación
├── alerts/                 # Sistema de alertas
├── reports/                # Generación de reportes
├── core/                   # Utilidades compartidas
├── sistema_polinizacion/   # Configuración principal
├── static/                 # Archivos estáticos
├── media/                  # Archivos multimedia
├── templates/              # Plantillas HTML
└── logs/                   # Archivos de log
```

## Instalación

1. **Clonar el repositorio**
   ```bash
   git clone <repository-url>
   cd sistema_polinizacion
   ```

2. **Crear entorno virtual**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # o
   venv\Scripts\activate     # Windows
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno**
   ```bash
   cp .env.example .env
   # Editar .env con tus configuraciones
   ```

5. **Ejecutar migraciones**
   ```bash
   python manage.py migrate
   ```

6. **Crear superusuario**
   ```bash
   python manage.py createsuperuser
   ```

7. **Ejecutar servidor de desarrollo**
   ```bash
   python manage.py runserver
   ```

## URLs Principales

- **Admin**: http://localhost:8000/admin/
- **API Docs**: http://localhost:8000/api/docs/
- **API Schema**: http://localhost:8000/api/schema/
- **ReDoc**: http://localhost:8000/api/redoc/

## Configuración de Desarrollo

El proyecto está configurado para desarrollo con:

- **DEBUG = True**
- **Base de datos**: SQLite (fallback automático si PostgreSQL no está disponible)
- **CORS**: Habilitado para todas las origins
- **APIs públicas para testing**: Configuración opcional para desarrollo sin autenticación

### Testing de APIs sin Autenticación

Para facilitar el desarrollo y testing, el sistema incluye un modo especial que permite acceso público a las APIs:

```bash
# Habilitar APIs públicas para testing
python manage.py toggle_public_api --enable

# Verificar estado actual
python manage.py toggle_public_api --status

# Deshabilitar cuando no sea necesario
python manage.py toggle_public_api --disable
```

**⚠️ Advertencia**: Esta funcionalidad solo está disponible en modo DEBUG y nunca debe usarse en producción.

Ver [documentación completa](docs/PUBLIC_API_TESTING.md) para más detalles.

## Próximos Pasos

1. Implementar modelos de autenticación y roles
2. Desarrollar módulos de polinización y germinación
3. Configurar sistema de alertas automáticas
4. Implementar generación de reportes
5. Añadir tests unitarios e integración

## Contribución

1. Fork el proyecto
2. Crear rama para feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Añadir nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.