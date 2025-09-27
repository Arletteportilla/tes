"""
Report generation services for the reports app.
Provides services for generating different types of reports.
"""

from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .models import Report, ReportType
from pollination.models import PollinationRecord
from germination.models import GerminationRecord


class ReportGeneratorService:
    """
    Main service for generating reports.
    Coordinates different report generators based on report type.
    """
    
    def __init__(self):
        self.generators = {
            'pollination': PollinationReportGenerator(),
            'germination': GerminationReportGenerator(),
            'statistical': StatisticalReportGenerator(),
        }
    
    def generate_report(self, report: Report) -> Dict[str, Any]:
        """
        Generate report data based on report type and parameters.
        
        Args:
            report: Report instance to generate
            
        Returns:
            Dict containing report data
            
        Raises:
            ValueError: If report type is not supported
        """
        if report.report_type.name not in self.generators:
            raise ValueError(f"Unsupported report type: {report.report_type.name}")
        
        generator = self.generators[report.report_type.name]
        return generator.generate(report.parameters)
    
    def get_available_report_types(self) -> List[str]:
        """
        Get list of available report types.
        
        Returns:
            List of report type names
        """
        return list(self.generators.keys())


class BaseReportGenerator:
    """
    Base class for report generators.
    Provides common functionality for all report types.
    """
    
    def generate(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate report data.
        
        Args:
            parameters: Report generation parameters
            
        Returns:
            Dict containing report data
        """
        raise NotImplementedError("Subclasses must implement generate method")
    
    def parse_date_range(self, parameters: Dict[str, Any]) -> tuple:
        """
        Parse date range from parameters.
        
        Args:
            parameters: Report parameters
            
        Returns:
            Tuple of (start_date, end_date)
        """
        start_date = parameters.get('start_date')
        end_date = parameters.get('end_date')
        
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Default to last 30 days if not provided
        if not start_date or not end_date:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)
        
        return start_date, end_date
    
    def format_percentage(self, value: float, total: int) -> float:
        """
        Calculate percentage with proper formatting.
        
        Args:
            value: Numerator value
            total: Denominator value
            
        Returns:
            Percentage as float
        """
        if total == 0:
            return 0.0
        return round((value / total) * 100, 2)


class PollinationReportGenerator(BaseReportGenerator):
    """
    Generator for pollination reports.
    Creates detailed reports about pollination processes.
    """
    
    def generate(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate pollination report data.
        
        Args:
            parameters: Report parameters including date range, filters
            
        Returns:
            Dict containing pollination report data
        """
        start_date, end_date = self.parse_date_range(parameters)
        
        # Base queryset
        queryset = PollinationRecord.objects.filter(
            pollination_date__range=[start_date, end_date]
        )
        
        # Apply additional filters
        if parameters.get('responsible_id'):
            queryset = queryset.filter(responsible_id=parameters['responsible_id'])
        
        if parameters.get('pollination_type'):
            queryset = queryset.filter(pollination_type__name=parameters['pollination_type'])
        
        if parameters.get('genus'):
            queryset = queryset.filter(
                Q(mother_plant__genus__icontains=parameters['genus']) |
                Q(father_plant__genus__icontains=parameters['genus']) |
                Q(new_plant__genus__icontains=parameters['genus'])
            )
        
        # Generate report data
        report_data = {
            'summary': self._generate_summary(queryset, start_date, end_date),
            'by_type': self._generate_by_type_analysis(queryset),
            'by_responsible': self._generate_by_responsible_analysis(queryset),
            'by_genus': self._generate_by_genus_analysis(queryset),
            'by_month': self._generate_monthly_analysis(queryset, start_date, end_date),
            'success_rates': self._generate_success_rates(queryset),
            'records': self._generate_records_list(queryset, parameters),
            'metadata': {
                'generated_at': timezone.now().isoformat(),
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'filters_applied': parameters,
                'total_records': queryset.count()
            }
        }
        
        return report_data
    
    def _generate_summary(self, queryset, start_date, end_date) -> Dict[str, Any]:
        """Generate summary statistics."""
        total_records = queryset.count()
        total_capsules = queryset.aggregate(
            total=Count('capsules_quantity')
        )['total'] or 0
        
        # Get unique counts
        unique_plants = queryset.values('mother_plant', 'father_plant', 'new_plant').distinct().count()
        unique_responsible = queryset.values('responsible').distinct().count()
        
        return {
            'total_records': total_records,
            'total_capsules': sum(record.capsules_quantity for record in queryset if record.capsules_quantity),
            'unique_plants_involved': unique_plants,
            'unique_responsible': unique_responsible,
            'date_range_days': (end_date - start_date).days + 1,
            'average_per_day': round(total_records / max(1, (end_date - start_date).days + 1), 2)
        }
    
    def _generate_by_type_analysis(self, queryset) -> List[Dict[str, Any]]:
        """Generate analysis by pollination type."""
        type_stats = queryset.values('pollination_type__name').annotate(
            count=Count('id'),
            avg_capsules=Avg('capsules_quantity')
        ).order_by('-count')
        
        total = queryset.count()
        
        return [
            {
                'type': stat['pollination_type__name'],
                'display_name': stat['pollination_type__name'],  # Use name as display name for now
                'count': stat['count'],
                'percentage': self.format_percentage(stat['count'], total),
                'avg_capsules': round(stat['avg_capsules'] or 0, 2)
            }
            for stat in type_stats
        ]
    
    def _generate_by_responsible_analysis(self, queryset) -> List[Dict[str, Any]]:
        """Generate analysis by responsible person."""
        responsible_stats = queryset.values(
            'responsible__username',
            'responsible__first_name',
            'responsible__last_name'
        ).annotate(
            count=Count('id'),
            avg_capsules=Avg('capsules_quantity')
        ).order_by('-count')
        
        return [
            {
                'username': stat['responsible__username'],
                'full_name': f"{stat['responsible__first_name']} {stat['responsible__last_name']}".strip(),
                'count': stat['count'],
                'avg_capsules': round(stat['avg_capsules'] or 0, 2)
            }
            for stat in responsible_stats
        ]
    
    def _generate_by_genus_analysis(self, queryset) -> List[Dict[str, Any]]:
        """Generate analysis by plant genus."""
        # This is a simplified version - in reality, you'd want more complex genus analysis
        genus_data = {}
        
        for record in queryset.select_related('mother_plant', 'father_plant', 'new_plant'):
            genera = set()
            if record.mother_plant:
                genera.add(record.mother_plant.genus)
            if record.father_plant:
                genera.add(record.father_plant.genus)
            if record.new_plant:
                genera.add(record.new_plant.genus)
            
            for genus in genera:
                if genus not in genus_data:
                    genus_data[genus] = {'count': 0, 'capsules': []}
                genus_data[genus]['count'] += 1
                if record.capsules_quantity:
                    genus_data[genus]['capsules'].append(record.capsules_quantity)
        
        result = []
        for genus, data in genus_data.items():
            avg_capsules = sum(data['capsules']) / len(data['capsules']) if data['capsules'] else 0
            result.append({
                'genus': genus,
                'count': data['count'],
                'avg_capsules': round(avg_capsules, 2)
            })
        
        return sorted(result, key=lambda x: x['count'], reverse=True)
    
    def _generate_monthly_analysis(self, queryset, start_date, end_date) -> List[Dict[str, Any]]:
        """Generate monthly analysis."""
        monthly_data = queryset.extra(
            select={'month': "strftime('%%Y-%%m', pollination_date)"}
        ).values('month').annotate(
            count=Count('id'),
            avg_capsules=Avg('capsules_quantity')
        ).order_by('month')
        
        return [
            {
                'month': data['month'],
                'count': data['count'],
                'avg_capsules': round(data['avg_capsules'] or 0, 2)
            }
            for data in monthly_data
        ]
    
    def _generate_success_rates(self, queryset) -> Dict[str, Any]:
        """Generate success rate analysis (simplified)."""
        total = queryset.count()
        if total == 0:
            return {'total_records': 0, 'success_rate': 0}
        
        # For now, we'll consider records with capsules > 0 as successful
        successful = queryset.filter(capsules_quantity__gt=0).count()
        
        return {
            'total_records': total,
            'successful_records': successful,
            'success_rate': self.format_percentage(successful, total)
        }
    
    def _generate_records_list(self, queryset, parameters) -> List[Dict[str, Any]]:
        """Generate list of records for detailed view."""
        # Limit records for performance
        limit = parameters.get('record_limit', 100)
        records = queryset.select_related(
            'responsible', 'pollination_type', 'mother_plant', 'father_plant', 'new_plant'
        )[:limit]
        
        return [
            {
                'id': record.id,
                'date': record.pollination_date.isoformat(),
                'responsible': record.responsible.get_full_name() or record.responsible.username,
                'type': record.pollination_type.get_name_display(),
                'mother_plant': f"{record.mother_plant.genus} {record.mother_plant.species}" if record.mother_plant else None,
                'father_plant': f"{record.father_plant.genus} {record.father_plant.species}" if record.father_plant else None,
                'new_plant': f"{record.new_plant.genus} {record.new_plant.species}" if record.new_plant else None,
                'capsules_quantity': record.capsules_quantity,
                'estimated_maturation': record.estimated_maturation_date.isoformat() if record.estimated_maturation_date else None,
                'observations': record.observations
            }
            for record in records
        ]


class GerminationReportGenerator(BaseReportGenerator):
    """
    Generator for germination reports.
    Creates detailed reports about germination processes.
    """
    
    def generate(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate germination report data.
        
        Args:
            parameters: Report parameters including date range, filters
            
        Returns:
            Dict containing germination report data
        """
        start_date, end_date = self.parse_date_range(parameters)
        
        # Base queryset
        queryset = GerminationRecord.objects.filter(
            germination_date__range=[start_date, end_date]
        )
        
        # Apply additional filters
        if parameters.get('responsible_id'):
            queryset = queryset.filter(responsible_id=parameters['responsible_id'])
        
        if parameters.get('genus'):
            queryset = queryset.filter(plant__genus__icontains=parameters['genus'])
        
        if parameters.get('seed_source'):
            queryset = queryset.filter(seed_source__name=parameters['seed_source'])
        
        # Generate report data
        report_data = {
            'summary': self._generate_summary(queryset, start_date, end_date),
            'by_responsible': self._generate_by_responsible_analysis(queryset),
            'by_genus': self._generate_by_genus_analysis(queryset),
            'by_seed_source': self._generate_by_seed_source_analysis(queryset),
            'by_month': self._generate_monthly_analysis(queryset, start_date, end_date),
            'success_rates': self._generate_success_rates(queryset),
            'records': self._generate_records_list(queryset, parameters),
            'metadata': {
                'generated_at': timezone.now().isoformat(),
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'filters_applied': parameters,
                'total_records': queryset.count()
            }
        }
        
        return report_data
    
    def _generate_summary(self, queryset, start_date, end_date) -> Dict[str, Any]:
        """Generate summary statistics."""
        total_records = queryset.count()
        total_seedlings = sum(record.seedlings_germinated for record in queryset if record.seedlings_germinated)
        
        unique_plants = queryset.values('plant').distinct().count()
        unique_responsible = queryset.values('responsible').distinct().count()
        
        return {
            'total_records': total_records,
            'total_seedlings': total_seedlings,
            'unique_plants': unique_plants,
            'unique_responsible': unique_responsible,
            'date_range_days': (end_date - start_date).days + 1,
            'average_per_day': round(total_records / max(1, (end_date - start_date).days + 1), 2)
        }
    
    def _generate_by_responsible_analysis(self, queryset) -> List[Dict[str, Any]]:
        """Generate analysis by responsible person."""
        responsible_stats = queryset.values(
            'responsible__username',
            'responsible__first_name',
            'responsible__last_name'
        ).annotate(
            count=Count('id'),
            avg_seedlings=Avg('seedlings_germinated')
        ).order_by('-count')
        
        return [
            {
                'username': stat['responsible__username'],
                'full_name': f"{stat['responsible__first_name']} {stat['responsible__last_name']}".strip(),
                'count': stat['count'],
                'avg_seedlings': round(stat['avg_seedlings'] or 0, 2)
            }
            for stat in responsible_stats
        ]
    
    def _generate_by_genus_analysis(self, queryset) -> List[Dict[str, Any]]:
        """Generate analysis by plant genus."""
        genus_stats = queryset.values('plant__genus').annotate(
            count=Count('id'),
            avg_seedlings=Avg('seedlings_germinated')
        ).order_by('-count')
        
        return [
            {
                'genus': stat['plant__genus'],
                'count': stat['count'],
                'avg_seedlings': round(stat['avg_seedlings'] or 0, 2)
            }
            for stat in genus_stats
        ]
    
    def _generate_by_seed_source_analysis(self, queryset) -> List[Dict[str, Any]]:
        """Generate analysis by seed source."""
        source_stats = queryset.values('seed_source__name').annotate(
            count=Count('id'),
            avg_seedlings=Avg('seedlings_germinated')
        ).order_by('-count')
        
        return [
            {
                'source': stat['seed_source__name'],
                'count': stat['count'],
                'avg_seedlings': round(stat['avg_seedlings'] or 0, 2)
            }
            for stat in source_stats
        ]
    
    def _generate_monthly_analysis(self, queryset, start_date, end_date) -> List[Dict[str, Any]]:
        """Generate monthly analysis."""
        monthly_data = queryset.extra(
            select={'month': "strftime('%%Y-%%m', germination_date)"}
        ).values('month').annotate(
            count=Count('id'),
            avg_seedlings=Avg('seedlings_germinated')
        ).order_by('month')
        
        return [
            {
                'month': data['month'],
                'count': data['count'],
                'avg_seedlings': round(data['avg_seedlings'] or 0, 2)
            }
            for data in monthly_data
        ]
    
    def _generate_success_rates(self, queryset) -> Dict[str, Any]:
        """Generate success rate analysis."""
        total = queryset.count()
        if total == 0:
            return {'total_records': 0, 'success_rate': 0}
        
        # Consider records with seedlings > 0 as successful
        successful = queryset.filter(seedlings_germinated__gt=0).count()
        
        return {
            'total_records': total,
            'successful_records': successful,
            'success_rate': self.format_percentage(successful, total)
        }
    
    def _generate_records_list(self, queryset, parameters) -> List[Dict[str, Any]]:
        """Generate list of records for detailed view."""
        limit = parameters.get('record_limit', 100)
        records = queryset.select_related(
            'responsible', 'plant', 'seed_source', 'germination_condition'
        )[:limit]
        
        return [
            {
                'id': record.id,
                'date': record.germination_date.isoformat(),
                'responsible': record.responsible.get_full_name() or record.responsible.username,
                'plant': f"{record.plant.genus} {record.plant.species}",
                'seed_source': record.seed_source.name,
                'seedlings_germinated': record.seedlings_germinated,
                'estimated_transplant': record.estimated_transplant_date.isoformat() if record.estimated_transplant_date else None,
                'observations': record.observations
            }
            for record in records
        ]


class StatisticalReportGenerator(BaseReportGenerator):
    """
    Generator for statistical reports.
    Creates consolidated statistical reports combining pollination and germination data.
    """
    
    def generate(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate statistical report data.
        
        Args:
            parameters: Report parameters including date range, filters
            
        Returns:
            Dict containing statistical report data
        """
        start_date, end_date = self.parse_date_range(parameters)
        
        # Get data from both modules
        pollination_data = self._get_pollination_stats(start_date, end_date, parameters)
        germination_data = self._get_germination_stats(start_date, end_date, parameters)
        
        # Generate consolidated report
        report_data = {
            'summary': self._generate_consolidated_summary(pollination_data, germination_data),
            'pollination_stats': pollination_data,
            'germination_stats': germination_data,
            'comparative_analysis': self._generate_comparative_analysis(pollination_data, germination_data),
            'trends': self._generate_trend_analysis(start_date, end_date),
            'metadata': {
                'generated_at': timezone.now().isoformat(),
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'filters_applied': parameters
            }
        }
        
        return report_data
    
    def _get_pollination_stats(self, start_date, end_date, parameters) -> Dict[str, Any]:
        """Get pollination statistics."""
        queryset = PollinationRecord.objects.filter(
            pollination_date__range=[start_date, end_date]
        )
        
        return {
            'total_records': queryset.count(),
            'total_capsules': queryset.aggregate(total=Count('capsules_quantity'))['total'] or 0,
            'avg_capsules': queryset.aggregate(avg=Avg('capsules_quantity'))['avg'] or 0,
            'by_type': list(queryset.values('pollination_type__name').annotate(count=Count('id')))
        }
    
    def _get_germination_stats(self, start_date, end_date, parameters) -> Dict[str, Any]:
        """Get germination statistics."""
        queryset = GerminationRecord.objects.filter(
            germination_date__range=[start_date, end_date]
        )
        
        return {
            'total_records': queryset.count(),
            'total_seedlings': sum(record.seedlings_germinated for record in queryset if record.seedlings_germinated),
            'avg_seedlings': queryset.aggregate(avg=Avg('seedlings_germinated'))['avg'] or 0,
            'by_source': list(queryset.values('seed_source__name').annotate(count=Count('id')))
        }
    
    def _generate_consolidated_summary(self, pollination_data, germination_data) -> Dict[str, Any]:
        """Generate consolidated summary."""
        return {
            'total_activities': pollination_data['total_records'] + germination_data['total_records'],
            'pollination_records': pollination_data['total_records'],
            'germination_records': germination_data['total_records'],
            'total_capsules': pollination_data['total_capsules'],
            'total_seedlings': germination_data['total_seedlings'],
            'pollination_percentage': self.format_percentage(
                pollination_data['total_records'],
                pollination_data['total_records'] + germination_data['total_records']
            ),
            'germination_percentage': self.format_percentage(
                germination_data['total_records'],
                pollination_data['total_records'] + germination_data['total_records']
            )
        }
    
    def _generate_comparative_analysis(self, pollination_data, germination_data) -> Dict[str, Any]:
        """Generate comparative analysis between pollination and germination."""
        return {
            'activity_ratio': {
                'pollination_to_germination': round(
                    pollination_data['total_records'] / max(1, germination_data['total_records']), 2
                ),
                'germination_to_pollination': round(
                    germination_data['total_records'] / max(1, pollination_data['total_records']), 2
                )
            },
            'productivity_comparison': {
                'avg_capsules_per_pollination': round(pollination_data['avg_capsules'], 2),
                'avg_seedlings_per_germination': round(germination_data['avg_seedlings'], 2)
            }
        }
    
    def _generate_trend_analysis(self, start_date, end_date) -> Dict[str, Any]:
        """Generate trend analysis over time."""
        # This is a simplified version - in a real implementation,
        # you'd want more sophisticated trend analysis
        
        # Get monthly data for both processes
        pollination_monthly = PollinationRecord.objects.filter(
            pollination_date__range=[start_date, end_date]
        ).extra(
            select={'month': "strftime('%%Y-%%m', pollination_date)"}
        ).values('month').annotate(count=Count('id')).order_by('month')
        
        germination_monthly = GerminationRecord.objects.filter(
            germination_date__range=[start_date, end_date]
        ).extra(
            select={'month': "strftime('%%Y-%%m', germination_date)"}
        ).values('month').annotate(count=Count('id')).order_by('month')
        
        return {
            'pollination_monthly': list(pollination_monthly),
            'germination_monthly': list(germination_monthly),
            'trend_direction': 'stable'  # Simplified - would need more complex calculation
        }