# Actualización del Sistema de Clima

## Resumen de Cambios

Se ha simplificado el sistema de condiciones climáticas para polinización y germinación, reemplazando múltiples parámetros ambientales por un sistema de códigos de clima predefinidos.

## Nuevos Códigos de Clima

| Código | Nombre | Rango de Temperatura | Descripción |
|--------|--------|---------------------|-------------|
| **C** | Frío | 10-18°C | Ideal para especies de alta montaña |
| **IC** | Intermedio Frío | 18-22°C | Condiciones templadas |
| **I** | Intermedio | 22-26°C | Condiciones estándar |
| **IW** | Intermedio Caliente | 26-30°C | Condiciones cálidas |
| **W** | Caliente | 30-35°C | Ideal para especies tropicales |

## Cambios en los Modelos

### ClimateCondition (Polinización)

**Antes:**
```python
{
    "weather": "Soleado",
    "temperature": 25.0,
    "humidity": 65,
    "wind_speed": 5.2,
    "notes": "Condiciones óptimas"
}
```

**Después:**
```python
{
    "climate": "I",
    "notes": "Condiciones óptimas"
}
```

### GerminationCondition (Germinación)

**Antes:**
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

**Después:**
```python
{
    "climate": "I",
    "substrate": "Turba", 
    "location": "Invernadero 1"
}
```

## Nuevos Endpoints de API

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
    "climate_condition": {
        "climate": "I",
        "notes": "Condiciones estándar"
    },
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
    "germination_condition": {
        "climate": "IW",
        "substrate": "Corteza de pino",
        "location": "Invernadero cálido"
    },
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

### GerminationCondition Response

```json
{
    "id": 1,
    "climate": "IW",
    "climate_display": "Intermedio Caliente",
    "substrate": "Corteza de pino",
    "location": "Invernadero cálido",
    "temperature_range": "26-30°C",
    "description": "Clima intermedio caliente, condiciones cálidas",
    "substrate_details": "Corteza de pino fina con vermiculita",
    "notes": "Ideal para especies subtropicales",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
}
```

## Validaciones Automáticas

### Compatibilidad Clima-Especie

El sistema ahora valida automáticamente la compatibilidad entre el tipo de clima y el género de la planta:

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
python manage.py migrate pollination
python manage.py migrate germination

# Configurar condiciones climáticas predefinidas
python manage.py setup_climate_conditions
```

### Migración Manual de Datos Existentes

Si tienes datos existentes, puedes mapear las condiciones antiguas a los nuevos códigos:

```python
# Mapeo sugerido de temperatura a código de clima
def map_temperature_to_climate(temperature):
    if temperature < 18:
        return 'C'
    elif temperature < 22:
        return 'IC'
    elif temperature < 26:
        return 'I'
    elif temperature < 30:
        return 'IW'
    else:
        return 'W'
```

## Beneficios del Nuevo Sistema

1. **Simplicidad**: Un solo parámetro en lugar de múltiples campos
2. **Consistencia**: Rangos de temperatura predefinidos y estandarizados
3. **Validación**: Compatibilidad automática clima-especie
4. **Usabilidad**: Interfaz más simple para los usuarios
5. **Mantenimiento**: Menos campos que validar y mantener

## Retrocompatibilidad

⚠️ **Importante**: Esta actualización no es retrocompatible. Los datos existentes necesitarán ser migrados manualmente o se perderán durante la migración.

## Comandos Útiles

```bash
# Crear condiciones climáticas predefinidas
python manage.py setup_climate_conditions

# Resetear y recrear condiciones climáticas
python manage.py setup_climate_conditions --reset

# Verificar migraciones
python manage.py showmigrations pollination germination
```