# Factories for Testing

This directory contains Factory Boy factories for creating test data in the Sistema de Polinización y Germinación.

## Available Factories

### Authentication Factories
- `RoleFactory` - Creates user roles (Polinizador, Germinador, Secretaria, Administrador)
- `CustomUserFactory` - Creates users with random data
- `PolinizadorUserFactory` - Creates users with Polinizador role
- `GerminadorUserFactory` - Creates users with Germinador role
- `SecretariaUserFactory` - Creates users with Secretaria role
- `AdministradorUserFactory` - Creates users with Administrador role
- `UserProfileFactory` - Creates user profiles with additional information

### Pollination Factories
- `PlantFactory` - Creates plants with generic names
- `OrchidPlantFactory` - Creates orchid plants with realistic genus/species
- `PollinationTypeFactory` - Creates pollination types (Self, Sibling, Híbrido)
- `ClimateConditionFactory` - Creates climate conditions for pollination
- `PollinationRecordFactory` - Creates general pollination records
- `SelfPollinationRecordFactory` - Creates self-pollination records
- `SiblingPollinationRecordFactory` - Creates sibling pollination records
- `HybridPollinationRecordFactory` - Creates hybrid pollination records

### Germination Factories
- `SeedSourceFactory` - Creates seed sources (internal or external)
- `InternalSeedSourceFactory` - Creates seed sources from pollination records
- `ExternalSeedSourceFactory` - Creates external seed sources
- `GerminationConditionFactory` - Creates germination conditions
- `GerminationRecordFactory` - Creates germination records
- `SuccessfulGerminationRecordFactory` - Creates completed germination records
- `PendingGerminationRecordFactory` - Creates pending germination records

### Alerts Factories
- `AlertTypeFactory` - Creates alert types (semanal, preventiva, frecuente)
- `AlertFactory` - Creates general alerts
- `PollinationAlertFactory` - Creates pollination-related alerts
- `GerminationAlertFactory` - Creates germination-related alerts
- `WeeklyAlertFactory` - Creates weekly alerts
- `PreventiveAlertFactory` - Creates preventive alerts
- `FrequentAlertFactory` - Creates frequent alerts
- `UserAlertFactory` - Creates user-alert relationships
- `ReadUserAlertFactory` - Creates read user alerts
- `DismissedUserAlertFactory` - Creates dismissed user alerts

### Reports Factories
- `ReportTypeFactory` - Creates report types (pollination, germination, statistical)
- `ReportFactory` - Creates general reports
- `CompletedReportFactory` - Creates completed reports
- `FailedReportFactory` - Creates failed reports
- `PollinationReportFactory` - Creates pollination reports
- `GerminationReportFactory` - Creates germination reports
- `StatisticalReportFactory` - Creates statistical reports

## Usage Examples

### Basic Usage
```python
from factories import CustomUserFactory, PlantFactory, SelfPollinationRecordFactory

# Create a user
user = CustomUserFactory(role__name='Polinizador')

# Create a plant
plant = PlantFactory()

# Create a pollination record
pollination = SelfPollinationRecordFactory(responsible=user, mother_plant=plant)
```

### Batch Creation
```python
# Create multiple users
users = [CustomUserFactory() for _ in range(10)]

# Create multiple plants
plants = [OrchidPlantFactory() for _ in range(20)]
```

### Specific Scenarios
```python
# Create a complete workflow
user = PolinizadorUserFactory()
pollination = SelfPollinationRecordFactory(responsible=user)
germination = GerminationRecordFactory(
    responsible=user,
    seed_source__pollination_record=pollination
)
```

## Management Commands

### populate_test_data
Creates test data using factories:
```bash
python manage.py populate_test_data --users=10 --plants=20 --pollinations=15 --germinations=12 --alerts=25 --reports=5
```

Options:
- `--users`: Number of users to create (default: 10)
- `--plants`: Number of plants to create (default: 50)
- `--pollinations`: Number of pollination records (default: 30)
- `--germinations`: Number of germination records (default: 25)
- `--alerts`: Number of alerts (default: 40)
- `--reports`: Number of reports (default: 15)
- `--clear`: Clear existing test data first

### create_demo_data
Creates realistic demonstration data:
```bash
python manage.py create_demo_data --clear
```

This creates:
- 4 demo users with different roles and realistic profiles
- 10 orchid plants with proper scientific names
- Realistic pollination and germination records
- Related alerts and reports

Demo users created:
- `maria.polinizadora` (password: demo123) - Polinizador role
- `carlos.germinador` (password: demo123) - Germinador role
- `ana.secretaria` (password: demo123) - Secretaria role
- `admin.sistema` (password: demo123) - Administrador role

## Testing

Run factory tests:
```bash
python manage.py test tests.test_factories
```

The factories are designed to create valid, related data that respects all model constraints and business rules.