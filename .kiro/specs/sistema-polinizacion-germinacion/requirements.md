# Requirements Document

## Introduction

El Sistema de Polinización y Germinación es una aplicación web desarrollada en Django que permite gestionar y monitorear procesos de polinización y germinación de plantas. El sistema incluye autenticación basada en roles, módulos especializados para diferentes tipos de usuarios, sistema de alertas automáticas y generación de reportes. La aplicación seguirá patrones MVC, tendrá documentación Swagger para las APIs, y inicialmente contará con APIs públicas para pruebas (excepto autenticación).

## Requirements

### Requirement 1

**User Story:** Como usuario del sistema, quiero autenticarme de forma segura para acceder a las funcionalidades según mi rol asignado.

#### Acceptance Criteria

1. WHEN un usuario ingresa credenciales válidas THEN el sistema SHALL generar un token JWT para la sesión
2. WHEN un token JWT expira THEN el sistema SHALL permitir renovación mediante refresh token
3. WHEN un usuario no autenticado intenta acceder al dashboard THEN el sistema SHALL redirigir al login
4. IF las credenciales son incorrectas THEN el sistema SHALL mostrar mensaje de error apropiado

### Requirement 2

**User Story:** Como administrador, quiero gestionar roles y permisos de usuarios para controlar el acceso a diferentes módulos del sistema.

#### Acceptance Criteria

1. WHEN se asigna rol "Polinizador" a un usuario THEN el sistema SHALL permitir acceso solo al módulo de polinización
2. WHEN se asigna rol "Germinador" a un usuario THEN el sistema SHALL permitir acceso solo al módulo de germinación
3. WHEN se asigna rol "Secretaria" a un usuario THEN el sistema SHALL permitir gestión de registros y soporte administrativo
4. WHEN se asigna rol "Administrador" a un usuario THEN el sistema SHALL permitir acceso completo incluyendo reportes y gestión de usuarios
5. IF un usuario intenta acceder a módulo no autorizado THEN el sistema SHALL denegar acceso y mostrar mensaje apropiado

### Requirement 3

**User Story:** Como polinizador, quiero registrar procesos de polinización con todos los datos requeridos para mantener trazabilidad completa del proceso.

#### Acceptance Criteria

1. WHEN registro una polinización THEN el sistema SHALL requerir responsable, tipo de polinización, fecha, género, especie, clima, ubicación y cantidad de cápsulas
2. WHEN selecciono tipo "Self" THEN el sistema SHALL requerir planta madre y planta nueva de la misma especie
3. WHEN selecciono tipo "Sibling" THEN el sistema SHALL requerir planta madre, padre y nueva de la misma progenie
4. WHEN selecciono tipo "Híbrido" THEN el sistema SHALL requerir planta madre, padre y nueva permitiendo especies distintas
5. WHEN registro fecha de polinización THEN el sistema SHALL calcular automáticamente fecha estimada de maduración
6. IF intento registrar fecha futura THEN el sistema SHALL rechazar el registro y mostrar error
7. WHEN completo registro THEN el sistema SHALL permitir añadir observaciones adicionales opcionales

### Requirement 4

**User Story:** Como germinador, quiero registrar procesos de germinación para monitorear el desarrollo de las plántulas.

#### Acceptance Criteria

1. WHEN registro una germinación THEN el sistema SHALL requerir responsable, fecha, especie, género, procedencia, condiciones del medio y cantidad de plántulas
2. WHEN selecciono procedencia THEN el sistema SHALL ofrecer opciones: autopolinización, sibling, híbrido u otra fuente
3. WHEN registro condiciones del medio THEN el sistema SHALL permitir especificar clima, sustrato y ubicación
4. WHEN completo registro THEN el sistema SHALL calcular automáticamente fecha estimada de trasplante según especie
5. IF intento registrar fecha futura THEN el sistema SHALL rechazar el registro y mostrar error
6. WHEN finalizo registro THEN el sistema SHALL permitir añadir observaciones adicionales opcionales

### Requirement 5

**User Story:** Como usuario del sistema, quiero recibir alertas automáticas sobre mis registros para no perder fechas importantes del proceso.

#### Acceptance Criteria

1. WHEN registro una polinización o germinación THEN el sistema SHALL generar alerta semanal una semana después
2. WHEN se acerca fecha estimada THEN el sistema SHALL generar alerta preventiva una semana antes
3. WHEN llega la semana de fecha estimada THEN el sistema SHALL enviar recordatorios diarios
4. WHEN se genera una alerta THEN el sistema SHALL almacenarla en la BD de Alertas
5. WHEN hay alertas pendientes THEN el sistema SHALL mostrarlas como notificaciones in-app
6. IF usuario no tiene permisos THEN el sistema SHALL ocultar alertas no autorizadas

### Requirement 6

**User Story:** Como administrador, quiero generar reportes detallados para analizar los procesos de polinización y germinación.

#### Acceptance Criteria

1. WHEN solicito reporte THEN el sistema SHALL ofrecer opciones: polinización, germinación o estadístico consolidado
2. WHEN genero reporte THEN el sistema SHALL permitir exportar en formato PDF y Excel
3. WHEN se genera reporte THEN el sistema SHALL almacenarlo en BD de Reportes para consulta posterior
4. WHEN accedo a reportes históricos THEN el sistema SHALL mostrar lista de reportes generados previamente
5. IF usuario no es administrador THEN el sistema SHALL denegar acceso a módulo de reportes

### Requirement 7

**User Story:** Como usuario del sistema, quiero que se validen mis datos de entrada para mantener integridad de la información.

#### Acceptance Criteria

1. WHEN intento guardar registro incompleto THEN el sistema SHALL mostrar campos obligatorios faltantes
2. WHEN intento registrar duplicado THEN el sistema SHALL detectar y prevenir la duplicación
3. WHEN intento eliminar registro THEN el sistema SHALL verificar permisos de administrador
4. IF no soy administrador THEN el sistema SHALL denegar eliminación de registros
5. WHEN ingreso datos THEN el sistema SHALL validar formatos y rangos apropiados

### Requirement 8

**User Story:** Como desarrollador, quiero que el sistema tenga APIs bien documentadas para facilitar integración y mantenimiento.

#### Acceptance Criteria

1. WHEN accedo a documentación THEN el sistema SHALL mostrar especificación Swagger completa
2. WHEN desarrollo funcionalidad THEN el sistema SHALL seguir patrón MVC para mantenibilidad
3. WHEN pruebo APIs THEN el sistema SHALL permitir acceso público temporal (excepto autenticación)
4. WHEN estructura código THEN el sistema SHALL seguir mejores prácticas de Django
5. IF API requiere autenticación THEN el sistema SHALL validar token JWT apropiadamente