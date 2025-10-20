from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from core.models import BaseModel, ClimateCondition
from authentication.models import CustomUser


class Plant(BaseModel):
    """
    Model representing a plant with botanical and location information.
    Used in pollination records to track plant relationships.
    """
    genus = models.CharField(
        max_length=100,
        help_text="Género botánico de la planta"
    )
    species = models.CharField(
        max_length=100,
        help_text="Especie botánica de la planta"
    )
    vivero = models.CharField(
        max_length=100,
        help_text="Nombre del vivero donde se encuentra la planta"
    )
    mesa = models.CharField(
        max_length=50,
        help_text="Mesa o sección dentro del vivero"
    )
    pared = models.CharField(
        max_length=50,
        help_text="Pared o ubicación específica en la mesa"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indica si la planta está activa en el sistema"
    )

    class Meta:
        verbose_name = "Planta"
        verbose_name_plural = "Plantas"
        ordering = ['genus', 'species', 'vivero', 'mesa', 'pared']
        unique_together = ['genus', 'species', 'vivero', 'mesa', 'pared']

    def __str__(self):
        return f"{self.genus} {self.species} - {self.vivero}/{self.mesa}/{self.pared}"

    @property
    def full_scientific_name(self):
        """Returns the full scientific name of the plant."""
        return f"{self.genus} {self.species}"

    @property
    def location(self):
        """Returns the full location string."""
        return f"{self.vivero}/{self.mesa}/{self.pared}"

    def clean(self):
        """Custom validation for Plant model."""
        super().clean()
        
        # Ensure genus and species are properly formatted
        if self.genus:
            self.genus = self.genus.strip().title()
        if self.species:
            self.species = self.species.strip().lower()


class PollinationType(BaseModel):
    """
    Model representing different types of pollination.
    Defines the rules and requirements for each pollination type.
    """
    POLLINATION_TYPES = [
        ('Self', 'Autopolinización'),
        ('Sibling', 'Polinización entre hermanos'),
        ('Híbrido', 'Hibridación'),
    ]
    
    name = models.CharField(
        max_length=20,
        choices=POLLINATION_TYPES,
        unique=True,
        help_text="Tipo de polinización"
    )
    description = models.TextField(
        help_text="Descripción detallada del tipo de polinización"
    )
    requires_father_plant = models.BooleanField(
        default=True,
        help_text="Indica si este tipo requiere planta padre"
    )
    allows_different_species = models.BooleanField(
        default=False,
        help_text="Indica si permite especies diferentes entre plantas"
    )
    maturation_days = models.PositiveIntegerField(
        default=120,
        help_text="Días estimados para maduración de cápsulas"
    )

    class Meta:
        verbose_name = "Tipo de Polinización"
        verbose_name_plural = "Tipos de Polinización"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.get_name_display()}"

    def save(self, *args, **kwargs):
        """Override save to set default values based on pollination type."""
        if self.name == 'Self':
            self.requires_father_plant = False
            self.allows_different_species = False
        elif self.name == 'Sibling':
            self.requires_father_plant = True
            self.allows_different_species = False
        elif self.name == 'Híbrido':
            self.requires_father_plant = True
            self.allows_different_species = True
            
        super().save(*args, **kwargs)



class PollinationRecord(BaseModel):
    """
    Main model for pollination records.
    Tracks all pollination activities with complete traceability.
    """
    responsible = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='pollination_records',
        help_text="Usuario responsable de la polinización"
    )
    pollination_type = models.ForeignKey(
        PollinationType,
        on_delete=models.PROTECT,
        related_name='pollination_records',
        help_text="Tipo de polinización realizada"
    )
    pollination_date = models.DateField(
        help_text="Fecha en que se realizó la polinización"
    )
    estimated_maturation_date = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha estimada de maduración de cápsulas (calculada automáticamente)"
    )
    
    # Plant relationships
    mother_plant = models.ForeignKey(
        Plant,
        on_delete=models.PROTECT,
        related_name='as_mother_plant',
        help_text="Planta madre (receptora del polen)"
    )
    father_plant = models.ForeignKey(
        Plant,
        on_delete=models.PROTECT,
        related_name='as_father_plant',
        null=True,
        blank=True,
        help_text="Planta padre (donadora del polen) - requerida para Sibling e Híbrido"
    )
    new_plant = models.ForeignKey(
        Plant,
        on_delete=models.PROTECT,
        related_name='as_new_plant',
        help_text="Nueva planta resultante de la polinización"
    )
    
    # Environmental conditions
    climate_condition = models.ForeignKey(
        ClimateCondition,
        on_delete=models.PROTECT,
        related_name='pollination_records',
        help_text="Condiciones climáticas durante la polinización"
    )
    
    # Additional data
    capsules_quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Cantidad de cápsulas polinizadas"
    )
    observations = models.TextField(
        blank=True,
        help_text="Observaciones adicionales sobre la polinización"
    )
    
    # Status tracking
    is_successful = models.BooleanField(
        null=True,
        blank=True,
        help_text="Indica si la polinización fue exitosa (se determina posteriormente)"
    )
    maturation_confirmed = models.BooleanField(
        default=False,
        help_text="Indica si se confirmó la maduración de las cápsulas"
    )
    maturation_confirmed_date = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha en que se confirmó la maduración"
    )

    class Meta:
        verbose_name = "Registro de Polinización"
        verbose_name_plural = "Registros de Polinización"
        ordering = ['-pollination_date', '-created_at']

    def __str__(self):
        return f"{self.pollination_type.name} - {self.mother_plant.full_scientific_name} - {self.pollination_date}"

    def clean(self):
        """Custom validation for PollinationRecord model."""
        super().clean()
        
        # Validate pollination date is not in the future
        if self.pollination_date and self.pollination_date > date.today():
            raise ValidationError({'pollination_date': 'La fecha de polinización no puede ser futura'})
        
        # Validate plant relationships based on pollination type
        if self.pollination_type and self.mother_plant:
            self._validate_plant_relationships()
    
    def _validate_plant_relationships(self):
        """Validate plant relationships based on pollination type."""
        pollination_type_name = self.pollination_type.name
        
        # Self pollination validation
        if pollination_type_name == 'Self':
            if self.father_plant:
                raise ValidationError({
                    'father_plant': 'La autopolinización no requiere planta padre'
                })
            if self.mother_plant and self.new_plant:
                if (self.mother_plant.genus != self.new_plant.genus or 
                    self.mother_plant.species != self.new_plant.species):
                    raise ValidationError({
                        'new_plant': 'En autopolinización, la planta nueva debe ser de la misma especie que la madre'
                    })
        
        # Sibling pollination validation
        elif pollination_type_name == 'Sibling':
            if not self.father_plant:
                raise ValidationError({
                    'father_plant': 'La polinización entre hermanos requiere planta padre'
                })
            if self.mother_plant and self.father_plant and self.new_plant:
                # All plants must be the same species for sibling pollination
                if not (self.mother_plant.genus == self.father_plant.genus == self.new_plant.genus and
                        self.mother_plant.species == self.father_plant.species == self.new_plant.species):
                    raise ValidationError({
                        'father_plant': 'En polinización entre hermanos, todas las plantas deben ser de la misma especie'
                    })
        
        # Hybrid pollination validation
        elif pollination_type_name == 'Híbrido':
            if not self.father_plant:
                raise ValidationError({
                    'father_plant': 'La hibridación requiere planta padre'
                })
            # For hybrids, different species are allowed but same genus is recommended
            if (self.mother_plant and self.father_plant and 
                self.mother_plant.genus == self.father_plant.genus and
                self.mother_plant.species == self.father_plant.species):
                raise ValidationError({
                    'father_plant': 'Para hibridación, se recomienda usar especies diferentes'
                })

    def save(self, *args, **kwargs):
        """Override save to calculate estimated maturation date."""
        if self.pollination_date and self.pollination_type and not self.estimated_maturation_date:
            self.estimated_maturation_date = (
                self.pollination_date + timedelta(days=self.pollination_type.maturation_days)
            )
        super().save(*args, **kwargs)

    def is_maturation_overdue(self):
        """Check if maturation is overdue."""
        if not self.estimated_maturation_date:
            return False
        return date.today() > self.estimated_maturation_date and not self.maturation_confirmed

    def days_to_maturation(self):
        """Calculate days remaining to estimated maturation."""
        if not self.estimated_maturation_date:
            return None
        delta = self.estimated_maturation_date - date.today()
        return delta.days

    def confirm_maturation(self, confirmed_date=None):
        """Mark the pollination as matured."""
        self.maturation_confirmed = True
        self.maturation_confirmed_date = confirmed_date or date.today()
        self.is_successful = True
        self.save()
