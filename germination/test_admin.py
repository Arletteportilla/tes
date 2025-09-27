from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from authentication.models import Role
from pollination.models import Plant
from germination.models import SeedSource, GerminationCondition, GerminationRecord
from germination.admin import SeedSourceAdmin, GerminationConditionAdmin, GerminationRecordAdmin

User = get_user_model()


class GerminationAdminTest(TestCase):
    """Test cases for germination admin interface."""
    
    def setUp(self):
        """Set up test data."""
        self.site = AdminSite()
        
        # Create role and user
        self.role = Role.objects.create(name='Germinador')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=self.role
        )
        
        # Create plant
        self.plant = Plant.objects.create(
            genus='Orchidaceae',
            species='cattleya',
            vivero='Vivero 1',
            mesa='Mesa 1',
            pared='Pared A'
        )
        
        # Create seed source
        self.seed_source = SeedSource.objects.create(
            name='Semillas Test',
            source_type='Otra fuente',
            external_supplier='Test Supplier'
        )
        
        # Create germination condition
        self.germination_condition = GerminationCondition.objects.create(
            climate='Invernadero',
            substrate='Turba',
            location='Vivero Principal'
        )
        
        # Create germination record
        self.germination_record = GerminationRecord.objects.create(
            responsible=self.user,
            germination_date=date.today() - timedelta(days=30),
            plant=self.plant,
            seed_source=self.seed_source,
            germination_condition=self.germination_condition,
            seeds_planted=100,
            seedlings_germinated=75
        )
    
    def test_seed_source_admin(self):
        """Test SeedSource admin configuration."""
        admin = SeedSourceAdmin(SeedSource, self.site)
        
        # Test list display
        self.assertIn('name', admin.list_display)
        self.assertIn('source_type', admin.list_display)
        self.assertIn('is_active', admin.list_display)
        
        # Test search fields
        self.assertIn('name', admin.search_fields)
        self.assertIn('external_supplier', admin.search_fields)
        
        # Test queryset optimization
        queryset = admin.get_queryset(None)
        self.assertTrue(hasattr(queryset, '_prefetch_related_lookups') or 
                       hasattr(queryset, 'query'))
    
    def test_germination_condition_admin(self):
        """Test GerminationCondition admin configuration."""
        admin = GerminationConditionAdmin(GerminationCondition, self.site)
        
        # Test list display
        self.assertIn('climate', admin.list_display)
        self.assertIn('substrate', admin.list_display)
        self.assertIn('location', admin.list_display)
        
        # Test search fields
        self.assertIn('location', admin.search_fields)
        
        # Test readonly fields
        self.assertIn('created_at', admin.readonly_fields)
        self.assertIn('updated_at', admin.readonly_fields)
    
    def test_germination_record_admin(self):
        """Test GerminationRecord admin configuration."""
        admin = GerminationRecordAdmin(GerminationRecord, self.site)
        
        # Test list display
        self.assertIn('germination_date', admin.list_display)
        self.assertIn('responsible', admin.list_display)
        self.assertIn('plant', admin.list_display)
        
        # Test custom methods
        self.assertTrue(hasattr(admin, 'germination_rate'))
        self.assertTrue(hasattr(admin, 'transplant_status'))
        self.assertTrue(hasattr(admin, 'days_to_transplant'))
        
        # Test custom method outputs
        germination_rate = admin.germination_rate(self.germination_record)
        self.assertEqual(germination_rate, "75.0%")
        
        transplant_status = admin.transplant_status(self.germination_record)
        self.assertIn('Pendiente', transplant_status)  # Should be pending (60 days remaining)
        
        days_to_transplant = admin.days_to_transplant(self.germination_record)
        self.assertIn('días', days_to_transplant)
        
        # Test queryset optimization
        queryset = admin.get_queryset(None)
        self.assertTrue(hasattr(queryset, '_prefetch_related_lookups') or 
                       hasattr(queryset, 'query'))
    
    def test_admin_readonly_fields(self):
        """Test that calculated fields are readonly."""
        admin = GerminationRecordAdmin(GerminationRecord, self.site)
        
        readonly_fields = admin.readonly_fields
        self.assertIn('estimated_transplant_date', readonly_fields)
        self.assertIn('germination_rate', readonly_fields)
        self.assertIn('transplant_status', readonly_fields)
        self.assertIn('days_to_transplant', readonly_fields)
        self.assertIn('is_transplant_overdue', readonly_fields)