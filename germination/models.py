from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from core.models import BaseModel
from authentication.models import CustomUser
from pollination.models import Plant


class SeedSource(BaseModel):
    """
    Model representing the source/origin of seeds used in germination.
    Tracks where the seeds came from (pollination records or external sources).
    """
    SOURCE_TYPES = [
        ('Autopolinización', 'Autopolinización'),
        ('Sibling', 'Polinización entre hermanos'),
        ('Híbrido', 'Hibridación'),
        ('Otra fuente', 'Otra fuente externa'),
    ]
    
    name = models.CharField(
        max_length=100,
        help_text="Nombre descriptivo de la fuente de semillas"
    )
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPES,
        help_text="Tipo de procedencia de las semillas"
    )
    description = models.TextField(
        blank=True,
        help_text="Descripción detallada de la fuente"
    )
    
    # Optional reference to pollination record if seeds come from internal pollination
    pollination_record = models.ForeignKey(
        'pollination.PollinationRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='seed_sources',
        help_text="Registro de polinización de origen (si aplica)"
    )
    
    # External source information
    external_supplier = models.CharField(
        max_length=200,
        blank=True,
        help_text="Proveedor externo de semillas (si aplica)"
    )
    collection_date = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de recolección de las semillas"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Indica si la fuente está activa en el sistema"
    )

    class Meta:
        verbose_name = "Fuente de Semillas"
        verbose_name_plural = "Fuentes de Semillas"
        ordering = ['name', 'source_type']

    def __str__(self):
        return f"{self.name} ({self.get_source_type_display()})"

    def clean(self):
        """Custom validation for SeedSource model."""
        super().clean()
        
        # Validate collection date is not in the future
        if self.collection_date and self.collection_date > date.today():
            raise ValidationError({'collection_date': 'La fecha de recolección no puede ser futura'})
        
        # If source type is from pollination, should have pollination_record
        if self.source_type in ['Autopolinización', 'Sibling', 'Híbrido']:
            if not self.pollination_record and not self.external_supplier:
                raise ValidationError({
                    'pollination_record': 'Se requiere un registro de polinización para este tipo de fuente'
                })
        
        # If source type is external, should have external supplier
        if self.source_type == 'Otra fuente' and not self.external_supplier:
            raise ValidationError({
                'external_supplier': 'Se requiere especificar el proveedor externo'
            })


class GerminationCondition(BaseModel):
    """
    Model representing the environmental conditions during germination.
    Simplified climate tracking with predefined temperature ranges.
    """
    CLIMATE_CHOICES = [
        ('I', 'Intermedio'),
        ('W', 'Caliente'),
        ('C', 'Frío'),
        ('IW', 'Intermedio Caliente'),
        ('IC', 'Intermedio Frío'),
    ]
    
    SUBSTRATE_CHOICES = [
        ('Turba', 'Turba'),
        ('Perlita', 'Perlita'),
        ('Vermiculita', 'Vermiculita'),
        ('Corteza de pino', 'Corteza de pino'),
        ('Musgo sphagnum', 'Musgo sphagnum'),
        ('Mezcla personalizada', 'Mezcla personalizada'),
    ]
    
    climate = models.CharField(
        max_length=2,
        choices=CLIMATE_CHOICES,
        help_text="Tipo de clima durante la germinación"
    )
    substrate = models.CharField(
        max_length=50,
        choices=SUBSTRATE_CHOICES,
        help_text="Tipo de sustrato utilizado"
    )
    location = models.CharField(
        max_length=200,
        help_text="Ubicación específica (vivero, mesa, etc.)"
    )
    
    # Additional details
    substrate_details = models.TextField(
        blank=True,
        help_text="Detalles adicionales sobre el sustrato (proporciones, preparación, etc.)"
    )
    notes = models.TextField(
        blank=True,
        help_text="Observaciones adicionales sobre las condiciones"
    )

    class Meta:
        verbose_name = "Condición de Germinación"
        verbose_name_plural = "Condiciones de Germinación"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_climate_display()} - {self.substrate} - {self.location}"

    @property
    def temperature_range(self):
        """Get the temperature range for the climate type."""
        ranges = {
            'C': '10-18°C',
            'IC': '18-22°C', 
            'I': '22-26°C',
            'IW': '26-30°C',
            'W': '30-35°C'
        }
        return ranges.get(self.climate, 'No definido')

    @property
    def description(self):
        """Get detailed description of the climate condition."""
        descriptions = {
            'C': 'Clima frío, ideal para especies de alta montaña',
            'IC': 'Clima intermedio frío, condiciones templadas',
            'I': 'Clima intermedio, condiciones estándar',
            'IW': 'Clima intermedio caliente, condiciones cálidas',
            'W': 'Clima caliente, ideal para especies tropicales'
        }
        return descriptions.get(self.climate, 'Sin descripción')


class GerminationRecord(BaseModel):
    """
    Main model for germination records.
    Tracks all germination activities with complete traceability.
    """
    responsible = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='germination_records',
        help_text="Usuario responsable de la germinación"
    )
    germination_date = models.DateField(
        help_text="Fecha en que se realizó la siembra/germinación"
    )
    estimated_transplant_date = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha estimada de trasplante (calculada automáticamente)"
    )
    
    # Plant and seed information
    plant = models.ForeignKey(
        Plant,
        on_delete=models.PROTECT,
        related_name='germination_records',
        help_text="Planta/especie que se está germinando"
    )
    seed_source = models.ForeignKey(
        SeedSource,
        on_delete=models.PROTECT,
        related_name='germination_records',
        help_text="Fuente de las semillas utilizadas"
    )
    
    # Germination conditions
    germination_condition = models.ForeignKey(
        GerminationCondition,
        on_delete=models.PROTECT,
        related_name='germination_records',
        help_text="Condiciones ambientales de germinación"
    )
    
    # Quantities and results
    seeds_planted = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Cantidad de semillas sembradas"
    )
    seedlings_germinated = models.PositiveIntegerField(
        default=0,
        help_text="Cantidad de plántulas que germinaron"
    )
    
    # Timing information
    transplant_days = models.PositiveIntegerField(
        default=90,
        help_text="Días estimados para trasplante según la especie"
    )
    
    # Status tracking
    is_successful = models.BooleanField(
        null=True,
        blank=True,
        help_text="Indica si la germinación fue exitosa"
    )
    transplant_confirmed = models.BooleanField(
        default=False,
        help_text="Indica si se confirmó el trasplante"
    )
    transplant_confirmed_date = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha en que se confirmó el trasplante"
    )
    
    # Additional information
    observations = models.TextField(
        blank=True,
        help_text="Observaciones adicionales sobre la germinación"
    )

    class Meta:
        verbose_name = "Registro de Germinación"
        verbose_name_plural = "Registros de Germinación"
        ordering = ['-germination_date', '-created_at']

    def __str__(self):
        return f"{self.plant.full_scientific_name} - {self.germination_date} - {self.responsible.username}"

    def clean(self):
        """Custom validation for GerminationRecord model."""
        super().clean()
        
        # Validate germination date is not in the future
        if self.germination_date and self.germination_date > date.today():
            raise ValidationError({'germination_date': 'La fecha de germinación no puede ser futura'})
        
        # Validate seedlings germinated doesn't exceed seeds planted
        if self.seedlings_germinated > self.seeds_planted:
            raise ValidationError({
                'seedlings_germinated': 'Las plántulas germinadas no pueden exceder las semillas sembradas'
            })
        
        # Validate transplant confirmation date
        if self.transplant_confirmed_date:
            if self.transplant_confirmed_date < self.germination_date:
                raise ValidationError({
                    'transplant_confirmed_date': 'La fecha de trasplante no puede ser anterior a la fecha de germinación'
                })
            
            if self.transplant_confirmed_date > date.today():
                raise ValidationError({
                    'transplant_confirmed_date': 'La fecha de trasplante no puede ser futura'
                })

    def save(self, *args, **kwargs):
        """Override save to calculate estimated transplant date."""
        if self.germination_date and not self.estimated_transplant_date:
            self.estimated_transplant_date = (
                self.germination_date + timedelta(days=self.transplant_days)
            )
        super().save(*args, **kwargs)

    def is_transplant_overdue(self):
        """Check if transplant is overdue."""
        if not self.estimated_transplant_date:
            return False
        return date.today() > self.estimated_transplant_date and not self.transplant_confirmed

    def days_to_transplant(self):
        """Calculate days remaining to estimated transplant."""
        if not self.estimated_transplant_date:
            return None
        delta = self.estimated_transplant_date - date.today()
        return delta.days

    def germination_rate(self):
        """Calculate germination success rate as percentage."""
        if not self.seeds_planted or self.seeds_planted == 0:
            return 0
        if not self.seedlings_germinated:
            return 0
        return round((self.seedlings_germinated / self.seeds_planted) * 100, 2)

    def confirm_transplant(self, confirmed_date=None, is_successful=True):
        """Mark the germination as transplanted."""
        self.transplant_confirmed = True
        self.transplant_confirmed_date = confirmed_date or date.today()
        self.is_successful = is_successful
        self.save()

    @property
    def transplant_status(self):
        """Get current transplant status."""
        if self.transplant_confirmed:
            return 'confirmed'
        elif self.is_transplant_overdue():
            return 'overdue'
        elif self.days_to_transplant() is not None:
            days_remaining = self.days_to_transplant()
            if days_remaining <= 7 and days_remaining >= 0:
                return 'approaching'
            else:
                return 'pending'
        return 'unknown'
