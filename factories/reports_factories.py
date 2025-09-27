import factory
from datetime import datetime, timedelta
from django.utils import timezone
from reports.models import ReportType, Report
from .authentication_factories import AdministradorUserFactory


class ReportTypeFactory(factory.django.DjangoModelFactory):
    """Factory for ReportType model."""
    
    class Meta:
        model = ReportType
        django_get_or_create = ('name',)
    
    name = factory.Iterator(['pollination', 'germination', 'statistical'])
    display_name = factory.LazyAttribute(lambda obj: {
        'pollination': 'Reporte de Polinización',
        'germination': 'Reporte de Germinación',
        'statistical': 'Reporte Estadístico'
    }.get(obj.name, 'Reporte Desconocido'))
    description = factory.LazyAttribute(lambda obj: f"Descripción para {obj.display_name}")
    is_active = True
    
    @factory.post_generation
    def set_template(obj, create, extracted, **kwargs):
        """Set template name based on report type."""
        if not create:
            return
        
        if not obj.template_name:
            obj.template_name = obj.get_default_template()
            obj.save()


class ReportFactory(factory.django.DjangoModelFactory):
    """Factory for Report model."""
    
    class Meta:
        model = Report
    
    title = factory.Faker('sentence', nb_words=4)
    report_type = factory.SubFactory(ReportTypeFactory)
    generated_by = factory.SubFactory(AdministradorUserFactory)
    status = factory.Iterator(['pending', 'generating', 'completed', 'failed'])
    format = factory.Iterator(['pdf', 'excel', 'json'])
    parameters = factory.LazyFunction(lambda: {
        'date_from': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
        'date_to': datetime.now().strftime('%Y-%m-%d'),
        'include_charts': True
    })
    metadata = factory.LazyFunction(lambda: {
        'version': '1.0',
        'auto_generated': False
    })


class CompletedReportFactory(ReportFactory):
    """Factory for completed reports."""
    status = 'completed'
    file_path = factory.LazyAttribute(lambda obj: f"reports/{obj.title.replace(' ', '_').lower()}_20240101_120000.{obj.format}")
    file_size = factory.Faker('pyint', min_value=1024, max_value=10485760)  # 1KB to 10MB
    generation_started_at = factory.LazyFunction(lambda: timezone.now() - timedelta(minutes=15))
    generation_completed_at = factory.LazyAttribute(lambda obj: obj.generation_started_at + timedelta(minutes=5))


class FailedReportFactory(ReportFactory):
    """Factory for failed reports."""
    status = 'failed'
    error_message = factory.Faker('sentence', nb_words=8)
    generation_started_at = factory.LazyFunction(lambda: timezone.now() - timedelta(minutes=30))
    generation_completed_at = factory.LazyAttribute(lambda obj: obj.generation_started_at + timedelta(minutes=2))


class PollinationReportFactory(ReportFactory):
    """Factory for pollination reports."""
    report_type = factory.SubFactory(ReportTypeFactory, name='pollination')
    title = "Reporte de Polinización"
    parameters = factory.LazyFunction(lambda: {
        'date_from': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
        'date_to': datetime.now().strftime('%Y-%m-%d'),
        'pollination_types': ['Self', 'Sibling', 'Híbrido'],
        'include_charts': True,
        'group_by': 'species'
    })


class GerminationReportFactory(ReportFactory):
    """Factory for germination reports."""
    report_type = factory.SubFactory(ReportTypeFactory, name='germination')
    title = "Reporte de Germinación"
    parameters = factory.LazyFunction(lambda: {
        'date_from': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
        'date_to': datetime.now().strftime('%Y-%m-%d'),
        'include_success_rates': True,
        'include_charts': True,
        'group_by': 'species'
    })


class StatisticalReportFactory(ReportFactory):
    """Factory for statistical reports."""
    report_type = factory.SubFactory(ReportTypeFactory, name='statistical')
    title = "Reporte Estadístico Consolidado"
    parameters = factory.LazyFunction(lambda: {
        'date_from': (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
        'date_to': datetime.now().strftime('%Y-%m-%d'),
        'include_pollination': True,
        'include_germination': True,
        'include_trends': True,
        'include_charts': True
    })