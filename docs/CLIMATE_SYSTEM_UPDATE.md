# Sistema de Clima Unificado

## Resumen de Cambios

Se ha unificado el sistema de condiciones climáticas para polinización y germinación, creando un modelo compartido que simplifica la gestión del clima y garantiza consistencia entre ambos módulos.

## Arquitectura del Nuevo Sistema

### Modelo Compartido: ClimateCondition (core.models)
- **Ubicación**: `core/models.py`
- **Propósito**: Modelo base compartido entre polinización y germinación
- **Campos**: `climate`, `notes`, timestamps

### Modelo Específico: GerminationSetup (germination.models)
- **Ubicación**: `germination/models.py`
- **Propósito**: Configuración específica de germinación que referencia ClimateCondition
- **Campos**: `climate_condition` (FK), `substrate`, `location`, `substrate_details`, `setup_notes`

## Códigos de Clima Disponibles

| Código | Nombre | Rango de Temperatura | Descripción |
|--------|--------|---------------------|-------------|
| **C** | Frío | 10-18°C | Ideal para especies de alta montaña |
| **IC** | Intermedio Frío | 18-22°C | Condiciones templadas |
| **I** | Intermedio | 22-26°C | Condiciones estándar |
| **IW** | Intermedio Caliente | 26-30°C | Condiciones cálidas |
| **W** | Caliente | 30-35°C | Ideal para especies tropicales |

## Cambios en los Modelos

### ClimateCondition (Compartido - core.models)

**Nuevo modelo unificado:**
```python
{
    "climate": "I",
    "notes": "Condiciones estándar"
}
```

### GerminationSetup (Germinación)

**Antes (GerminationCondition):**
```python
{
    "climate": "Controlado",
    "substrate": "Turba",
    "location": "Invernadero 1",
    "temperature": 24.5,
    "humidity": 75,
    "light_hours": 12
}
```

**Después (GerminationSetup):**
```python
{
    "climate_condition": 3,  // Referencia al ClimateCondition compartido
    "substrate": "Turba", 
    "location": "Invernadero 1",
    "substrate_details": "Turba con perlita",
    "setup_notes": "Configuración estándar"
}
```

### PollinationRecord

**Ahora usa:**
```python
{
    "climate_condition": 3  // Referencia al ClimateCondition compartido
}
```

## Nuevos Endpoints de API

### Crear Condición Climática Compartida

```http
POST /api/core/climate-conditions/
Content-Type: application/json

{
    "climate": "I",
    "notes": "Condiciones estándar para la mayoría de especies"
}
```

### Crear Configuración de Germinación

```http
POST /api/germination/setups/
Content-Type: application/json

{
    "climate_condition": 3,
    "substrate": "Corteza de pino",
    "location": "Invernadero cálido",
    "substrate_details": "Corteza fina con perlita",
    "setup_notes": "Configuración para especies intermedias"
}
```

### Crear Registro de Polinización

```http
POST /api/pollination/records/
Content-Type: application/json

{
    "pollination_type": 1,
    "pollination_date": "2024-01-15",
    "mother_plant": 1,
    "father_plant": 2,
    "new_plant": 3,
    "climate_condition": 3,
    "capsules_quantity": 5,
    "observations": "Polinización exitosa"
}
```

### Crear Registro de Germinación

```http
POST /api/germination/records/
Content-Type: application/json

{
    "germination_date": "2024-01-20",
    "plant": 1,
    "seed_source": 1,
    "germination_setup": 4,
    "seeds_planted": 50,
    "seedlings_germinated": 42
}
```

## Respuestas de API Actualizadas

### ClimateCondition Response

```json
{
    "id": 1,
    "climate": "I",
    "climate_display": "Intermedio",
    "temperature_range": "22-26°C",
    "description": "Clima intermedio, condiciones estándar",
    "notes": "Condiciones óptimas para la mayoría de especies",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
}
```

### GerminationSetup Response

```json
{
    "id": 1,
    "climate_condition": 4,
    "climate_display": "Intermedio Caliente",
    "substrate": "Corteza de pino",
    "location": "Invernadero cálido",
    "temperature_range": "26-30°C",
    "climate_description": "Clima intermedio caliente, condiciones cálidas",
    "substrate_details": "Corteza de pino fina con vermiculita",
    "setup_notes": "Ideal para especies subtropicales",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
}
```

## Ventajas del Sistema Unificado

1. **Consistencia**: Un solo modelo de clima compartido entre polinización y germinación
2. **Mantenimiento**: Cambios en condiciones climáticas se reflejan automáticamente en ambos módulos
3. **Simplicidad**: Eliminación de duplicación de código y datos
4. **Escalabilidad**: Fácil agregar nuevos tipos de clima que beneficien ambos procesos
5. **Integridad**: Referencias consistentes y validación centralizada
6. **Flexibilidad**: GerminationSetup permite configuraciones específicas manteniendo clima compartido

## Validaciones Automáticas

### Compatibilidad Clima-Especie

El sistema valida automáticamente la compatibilidad entre el tipo de clima y el género de la planta:

- **Orchidaceae**: Prefiere I, IW, IC
- **Cattleya**: Prefiere I, IW  
- **Dendrobium**: Prefiere I, IC
- **Phalaenopsis**: Prefiere IW, W
- **Cactaceae**: Prefiere W, IW
- **Bromeliaceae**: Prefiere IW, W, I

## Migración de Datos

### Ejecutar Migraciones

```bash
# Aplicar migraciones de base de datos
python manage.py migrate core
python manage.py migrate pollination
python manage.py migrate germination

# Configurar condiciones climáticas predefinidas
python manage.py setup_climate_conditions
```

### Estructura de Migraciones

1. **core.0001_initial**: Crea el modelo ClimateCondition compartido
2. **pollination.0003_remove_climatecondition**: Actualiza referencias y elimina modelo local
3. **germination.0003_update_to_shared_climate**: Crea GerminationSetup y actualiza referencias

## Comandos de Gestión

```bash
# Crear condiciones climáticas y configuraciones predefinidas
python manage.py setup_climate_conditions

# Resetear y recrear todas las condiciones
python manage.py setup_climate_conditions --reset

# Verificar estado de migraciones
python manage.py showmigrations core pollination germination

# Ejecutar script de ejemplos
python scripts/climate_examples.py
```

## Cambios en el Admin

### ClimateCondition Admin (core/admin.py)
- Gestión centralizada de condiciones climáticas
- Campos de solo lectura para propiedades calculadas
- Filtros por tipo de clima

### GerminationSetup Admin (germination/admin.py)
- Reemplaza GerminationCondition Admin
- Referencia a ClimateCondition compartido
- Campos específicos de configuración de germinación

## Cambios en Serializadores

### Nuevos Serializadores
- `GerminationSetupSerializer`: Reemplaza `GerminationConditionSerializer`
- `GerminationSetupListSerializer`: Para listados simplificados
- Ambos módulos ahora importan `ClimateCondition` desde `core.models`

## Fixtures Actualizados

### climate_conditions.json
- Ahora usa `core.climatecondition` en lugar de `pollination.climatecondition`

### germination_conditions.json
- Actualizado para usar `germination.germinationsetup`
- Referencias a `climate_condition` en lugar de campos de clima directos

## Retrocompatibilidad

⚠️ **Importante**: Esta actualización requiere migración de datos existentes. Las migraciones automáticas manejan la transición, pero se recomienda hacer backup antes de aplicarlas.

## Verificación del Sistema

Después de aplicar las migraciones, verifica que todo funciona correctamente:

```bash
# Ejecutar tests
python manage.py test core.tests
python manage.py test pollination.tests  
python manage.py test germination.tests

# Verificar datos de ejemplo
python scripts/climate_examples.py

# Verificar admin
python manage.py runserver
# Navegar a /admin/ y verificar los modelos
```

## Próximos Pasos

1. Actualizar frontend para usar nuevos endpoints
2. Actualizar documentación de API
3. Crear tests adicionales para el sistema unificado
4. Considerar agregar más tipos de clima según necesidades