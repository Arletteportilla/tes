"""
Statistics services for the reports app.
Provides statistical analysis for pollination and germination data.
"""

from django.db.models import Count, Avg, Sum, Q, F, Max, Min
from django.utils import timezone
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

from pollination.models import PollinationRecord, Plant, PollinationType
from germination.models import GerminationRecord, SeedSource
from authentication.models import CustomUser


class StatisticsService:
    """
    Main service for generating statistical analysis.
    Provides comprehensive statistics for pollination and germination processes.
    """
    
    def __init__(self):
        self.pollination_stats = PollinationStatisticsService()
        self.germination_stats = GerminationStatisticsService()
    
    def get_comprehensive_statistics(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get comprehensive statistics combining pollination and germination data.
        
        Args:
            parameters: Filter parameters including date range, user filters, etc.
            
        Returns:
            Dict containing comprehensive statistics
        """
        start_date, end_date = self._parse_date_range(parameters)
        
        # Get individual statistics
        pollination_stats = self.pollination_stats.get_statistics(parameters)
        germination_stats = self.germination_stats.get_statistics(parameters)
        
        # Generate comparative and consolidated statistics
        comparative_stats = self._generate_comparative_statistics(
            pollination_stats, germination_stats, start_date, end_date
        )
        
        return {
            'summary': self._generate_summary_statistics(pollination_stats, germination_stats),
            'pollination': pollination_stats,
            'germination': germination_stats,
            'comparative': comparative_stats,
            'trends': self._generate_trend_statistics(start_date, end_date, parameters),
            'performance': self._generate_performance_statistics(start_date, end_date, parameters),
            'metadata': {
                'generated_at': timezone.now().isoformat(),
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'filters_applied': parameters
            }
        }
    
    def _parse_date_range(self, parameters: Dict[str, Any]) -> Tuple[date, date]:
        """Parse date range from parameters."""
        start_date = parameters.get('start_date')
        end_date = parameters.get('end_date')
        
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Default to last 90 days if not provided
        if not start_date or not end_date:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=90)
        
        return start_date, end_date
    
    def _generate_summary_statistics(self, pollination_stats: Dict, germination_stats: Dict) -> Dict[str, Any]:
        """Generate high-level summary statistics."""
        total_activities = (
            pollination_stats['summary']['total_records'] + 
            germination_stats['summary']['total_records']
        )
        
        return {
            'total_activities': total_activities,
            'pollination_records': pollination_stats['summary']['total_records'],
            'germination_records': germination_stats['summary']['total_records'],
            'total_capsules_produced': pollination_stats['summary']['total_capsules'],
            'total_seedlings_produced': germination_stats['summary']['total_seedlings'],
            'unique_species_involved': self._count_unique_species(),
            'active_users': self._count_active_users(),
            'activity_distribution': {
                'pollination_percentage': round(
                    (pollination_stats['summary']['total_records'] / max(1, total_activities)) * 100, 2
                ),
                'germination_percentage': round(
                    (germination_stats['summary']['total_records'] / max(1, total_activities)) * 100, 2
                )
            }
        }
    
    def _generate_comparative_statistics(self, pollination_stats: Dict, germination_stats: Dict, 
                                       start_date: date, end_date: date) -> Dict[str, Any]:
        """Generate comparative analysis between pollination and germination."""
        return {
            'activity_ratios': {
                'pollination_to_germination': round(
                    pollination_stats['summary']['total_records'] / 
                    max(1, germination_stats['summary']['total_records']), 2
                ),
                'capsules_to_seedlings': round(
                    pollination_stats['summary']['total_capsules'] / 
                    max(1, germination_stats['summary']['total_seedlings']), 2
                )
            },
            'efficiency_metrics': {
                'avg_capsules_per_pollination': pollination_stats['summary']['avg_capsules_per_record'],
                'avg_seedlings_per_germination': germination_stats['summary']['avg_seedlings_per_record'],
                'overall_success_rate': self._calculate_overall_success_rate(start_date, end_date)
            },
            'resource_utilization': {
                'plants_used_in_pollination': pollination_stats['summary']['unique_plants'],
                'plants_used_in_germination': germination_stats['summary']['unique_plants'],
                'total_unique_plants': self._count_total_unique_plants(start_date, end_date)
            }
        }
    
    def _generate_trend_statistics(self, start_date: date, end_date: date, 
                                 parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate trend analysis over time."""
        # Monthly trends
        monthly_trends = self._get_monthly_trends(start_date, end_date)
        
        # Weekly trends for recent data
        weekly_trends = self._get_weekly_trends(start_date, end_date)
        
        return {
            'monthly_trends': monthly_trends,
            'weekly_trends': weekly_trends,
            'growth_rates': self._calculate_growth_rates(monthly_trends),
            'seasonal_patterns': self._analyze_seasonal_patterns(monthly_trends)
        }
    
    def _generate_performance_statistics(self, start_date: date, end_date: date, 
                                       parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance and efficiency statistics."""
        return {
            'user_performance': self._get_user_performance_stats(start_date, end_date),
            'species_performance': self._get_species_performance_stats(start_date, end_date),
            'success_rates': self._get_detailed_success_rates(start_date, end_date),
            'productivity_metrics': self._get_productivity_metrics(start_date, end_date)
        }
    
    def _count_unique_species(self) -> int:
        """Count unique species involved in all activities."""
        return Plant.objects.values('genus', 'species').distinct().count()
    
    def _count_active_users(self) -> int:
        """Count users who have created records."""
        pollination_users = set(PollinationRecord.objects.values_list('responsible_id', flat=True))
        germination_users = set(GerminationRecord.objects.values_list('responsible_id', flat=True))
        return len(pollination_users.union(germination_users))
    
    def _count_total_unique_plants(self, start_date: date, end_date: date) -> int:
        """Count total unique plants used in the date range."""
        pollination_plants = set()
        germination_plants = set()
        
        # Get plants from pollination records
        for record in PollinationRecord.objects.filter(
            pollination_date__range=[start_date, end_date]
        ).select_related('mother_plant', 'father_plant', 'new_plant'):
            if record.mother_plant:
                pollination_plants.add(record.mother_plant.id)
            if record.father_plant:
                pollination_plants.add(record.father_plant.id)
            if record.new_plant:
                pollination_plants.add(record.new_plant.id)
        
        # Get plants from germination records
        for record in GerminationRecord.objects.filter(
            germination_date__range=[start_date, end_date]
        ).select_related('plant'):
            germination_plants.add(record.plant.id)
        
        return len(pollination_plants.union(germination_plants))
    
    def _calculate_overall_success_rate(self, start_date: date, end_date: date) -> float:
        """Calculate overall success rate across all activities."""
        # Pollination success (records with capsules > 0)
        total_pollinations = PollinationRecord.objects.filter(
            pollination_date__range=[start_date, end_date]
        ).count()
        successful_pollinations = PollinationRecord.objects.filter(
            pollination_date__range=[start_date, end_date],
            capsules_quantity__gt=0
        ).count()
        
        # Germination success (records with seedlings > 0)
        total_germinations = GerminationRecord.objects.filter(
            germination_date__range=[start_date, end_date]
        ).count()
        successful_germinations = GerminationRecord.objects.filter(
            germination_date__range=[start_date, end_date],
            seedlings_germinated__gt=0
        ).count()
        
        total_activities = total_pollinations + total_germinations
        successful_activities = successful_pollinations + successful_germinations
        
        if total_activities == 0:
            return 0.0
        
        return round((successful_activities / total_activities) * 100, 2)
    
    def _get_monthly_trends(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get monthly trend data."""
        # Pollination monthly data
        pollination_monthly = PollinationRecord.objects.filter(
            pollination_date__range=[start_date, end_date]
        ).extra(
            select={'month': "strftime('%%Y-%%m', pollination_date)"}
        ).values('month').annotate(
            count=Count('id'),
            total_capsules=Sum('capsules_quantity')
        ).order_by('month')
        
        # Germination monthly data
        germination_monthly = GerminationRecord.objects.filter(
            germination_date__range=[start_date, end_date]
        ).extra(
            select={'month': "strftime('%%Y-%%m', germination_date)"}
        ).values('month').annotate(
            count=Count('id'),
            total_seedlings=Sum('seedlings_germinated')
        ).order_by('month')
        
        # Combine data by month
        monthly_data = defaultdict(lambda: {
            'month': '',
            'pollination_count': 0,
            'germination_count': 0,
            'total_capsules': 0,
            'total_seedlings': 0,
            'total_activities': 0
        })
        
        for item in pollination_monthly:
            month = item['month']
            monthly_data[month]['month'] = month
            monthly_data[month]['pollination_count'] = item['count']
            monthly_data[month]['total_capsules'] = item['total_capsules'] or 0
            monthly_data[month]['total_activities'] += item['count']
        
        for item in germination_monthly:
            month = item['month']
            monthly_data[month]['month'] = month
            monthly_data[month]['germination_count'] = item['count']
            monthly_data[month]['total_seedlings'] = item['total_seedlings'] or 0
            monthly_data[month]['total_activities'] += item['count']
        
        return sorted(monthly_data.values(), key=lambda x: x['month'])
    
    def _get_weekly_trends(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get weekly trend data for recent periods."""
        # Only get weekly trends for last 12 weeks to avoid too much data
        recent_start = max(start_date, end_date - timedelta(weeks=12))
        
        weekly_data = []
        current_date = recent_start
        
        while current_date <= end_date:
            week_end = min(current_date + timedelta(days=6), end_date)
            
            pollination_count = PollinationRecord.objects.filter(
                pollination_date__range=[current_date, week_end]
            ).count()
            
            germination_count = GerminationRecord.objects.filter(
                germination_date__range=[current_date, week_end]
            ).count()
            
            weekly_data.append({
                'week_start': current_date.isoformat(),
                'week_end': week_end.isoformat(),
                'pollination_count': pollination_count,
                'germination_count': germination_count,
                'total_activities': pollination_count + germination_count
            })
            
            current_date = week_end + timedelta(days=1)
        
        return weekly_data
    
    def _calculate_growth_rates(self, monthly_trends: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate growth rates from monthly trends."""
        if len(monthly_trends) < 2:
            return {'pollination_growth': 0, 'germination_growth': 0, 'overall_growth': 0}
        
        # Compare first and last months
        first_month = monthly_trends[0]
        last_month = monthly_trends[-1]
        
        def calculate_rate(old_val, new_val):
            if old_val == 0:
                return 100 if new_val > 0 else 0
            return round(((new_val - old_val) / old_val) * 100, 2)
        
        return {
            'pollination_growth': calculate_rate(
                first_month['pollination_count'], 
                last_month['pollination_count']
            ),
            'germination_growth': calculate_rate(
                first_month['germination_count'], 
                last_month['germination_count']
            ),
            'overall_growth': calculate_rate(
                first_month['total_activities'], 
                last_month['total_activities']
            )
        }
    
    def _analyze_seasonal_patterns(self, monthly_trends: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze seasonal patterns in the data."""
        if not monthly_trends:
            return {'peak_month': None, 'low_month': None, 'seasonal_variation': 0}
        
        # Find peak and low months
        peak_month = max(monthly_trends, key=lambda x: x['total_activities'])
        low_month = min(monthly_trends, key=lambda x: x['total_activities'])
        
        # Calculate seasonal variation
        activities = [month['total_activities'] for month in monthly_trends]
        if activities:
            avg_activity = sum(activities) / len(activities)
            variation = (max(activities) - min(activities)) / max(1, avg_activity) * 100
        else:
            variation = 0
        
        return {
            'peak_month': peak_month['month'],
            'peak_activities': peak_month['total_activities'],
            'low_month': low_month['month'],
            'low_activities': low_month['total_activities'],
            'seasonal_variation': round(variation, 2)
        }
    
    def _get_user_performance_stats(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get performance statistics by user."""
        # Get pollination stats by user
        pollination_by_user = PollinationRecord.objects.filter(
            pollination_date__range=[start_date, end_date]
        ).values(
            'responsible__username',
            'responsible__first_name',
            'responsible__last_name'
        ).annotate(
            pollination_count=Count('id'),
            total_capsules=Sum('capsules_quantity'),
            avg_capsules=Avg('capsules_quantity')
        )
        
        # Get germination stats by user
        germination_by_user = GerminationRecord.objects.filter(
            germination_date__range=[start_date, end_date]
        ).values(
            'responsible__username',
            'responsible__first_name',
            'responsible__last_name'
        ).annotate(
            germination_count=Count('id'),
            total_seedlings=Sum('seedlings_germinated'),
            avg_seedlings=Avg('seedlings_germinated')
        )
        
        # Combine user stats
        user_stats = defaultdict(lambda: {
            'username': '',
            'full_name': '',
            'pollination_count': 0,
            'germination_count': 0,
            'total_capsules': 0,
            'total_seedlings': 0,
            'avg_capsules': 0,
            'avg_seedlings': 0,
            'total_activities': 0
        })
        
        for stat in pollination_by_user:
            username = stat['responsible__username']
            user_stats[username]['username'] = username
            user_stats[username]['full_name'] = f"{stat['responsible__first_name']} {stat['responsible__last_name']}".strip()
            user_stats[username]['pollination_count'] = stat['pollination_count']
            user_stats[username]['total_capsules'] = stat['total_capsules'] or 0
            user_stats[username]['avg_capsules'] = round(stat['avg_capsules'] or 0, 2)
            user_stats[username]['total_activities'] += stat['pollination_count']
        
        for stat in germination_by_user:
            username = stat['responsible__username']
            user_stats[username]['username'] = username
            user_stats[username]['full_name'] = f"{stat['responsible__first_name']} {stat['responsible__last_name']}".strip()
            user_stats[username]['germination_count'] = stat['germination_count']
            user_stats[username]['total_seedlings'] = stat['total_seedlings'] or 0
            user_stats[username]['avg_seedlings'] = round(stat['avg_seedlings'] or 0, 2)
            user_stats[username]['total_activities'] += stat['germination_count']
        
        return sorted(user_stats.values(), key=lambda x: x['total_activities'], reverse=True)
    
    def _get_species_performance_stats(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get performance statistics by species."""
        species_stats = defaultdict(lambda: {
            'genus': '',
            'species': '',
            'scientific_name': '',
            'pollination_count': 0,
            'germination_count': 0,
            'total_capsules': 0,
            'total_seedlings': 0,
            'total_activities': 0
        })
        
        # Get pollination data by species
        pollination_species = PollinationRecord.objects.filter(
            pollination_date__range=[start_date, end_date]
        ).values(
            'mother_plant__genus',
            'mother_plant__species'
        ).annotate(
            count=Count('id'),
            total_capsules=Sum('capsules_quantity')
        )
        
        for stat in pollination_species:
            genus = stat['mother_plant__genus']
            species = stat['mother_plant__species']
            key = f"{genus}_{species}"
            
            species_stats[key]['genus'] = genus
            species_stats[key]['species'] = species
            species_stats[key]['scientific_name'] = f"{genus} {species}"
            species_stats[key]['pollination_count'] = stat['count']
            species_stats[key]['total_capsules'] = stat['total_capsules'] or 0
            species_stats[key]['total_activities'] += stat['count']
        
        # Get germination data by species
        germination_species = GerminationRecord.objects.filter(
            germination_date__range=[start_date, end_date]
        ).values(
            'plant__genus',
            'plant__species'
        ).annotate(
            count=Count('id'),
            total_seedlings=Sum('seedlings_germinated')
        )
        
        for stat in germination_species:
            genus = stat['plant__genus']
            species = stat['plant__species']
            key = f"{genus}_{species}"
            
            species_stats[key]['genus'] = genus
            species_stats[key]['species'] = species
            species_stats[key]['scientific_name'] = f"{genus} {species}"
            species_stats[key]['germination_count'] = stat['count']
            species_stats[key]['total_seedlings'] = stat['total_seedlings'] or 0
            species_stats[key]['total_activities'] += stat['count']
        
        return sorted(species_stats.values(), key=lambda x: x['total_activities'], reverse=True)
    
    def _get_detailed_success_rates(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get detailed success rate analysis."""
        # Pollination success rates by type
        pollination_success = {}
        for poll_type in PollinationType.objects.all():
            total = PollinationRecord.objects.filter(
                pollination_date__range=[start_date, end_date],
                pollination_type=poll_type
            ).count()
            
            successful = PollinationRecord.objects.filter(
                pollination_date__range=[start_date, end_date],
                pollination_type=poll_type,
                capsules_quantity__gt=0
            ).count()
            
            success_rate = (successful / max(1, total)) * 100
            
            pollination_success[poll_type.name] = {
                'total_records': total,
                'successful_records': successful,
                'success_rate': round(success_rate, 2)
            }
        
        # Germination success rates by source type
        germination_success = {}
        for source_type, display_name in SeedSource.SOURCE_TYPES:
            total = GerminationRecord.objects.filter(
                germination_date__range=[start_date, end_date],
                seed_source__source_type=source_type
            ).count()
            
            successful = GerminationRecord.objects.filter(
                germination_date__range=[start_date, end_date],
                seed_source__source_type=source_type,
                seedlings_germinated__gt=0
            ).count()
            
            success_rate = (successful / max(1, total)) * 100
            
            germination_success[source_type] = {
                'total_records': total,
                'successful_records': successful,
                'success_rate': round(success_rate, 2)
            }
        
        return {
            'pollination_by_type': pollination_success,
            'germination_by_source': germination_success
        }
    
    def _get_productivity_metrics(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get productivity and efficiency metrics."""
        # Calculate daily averages
        date_range_days = (end_date - start_date).days + 1
        
        total_pollinations = PollinationRecord.objects.filter(
            pollination_date__range=[start_date, end_date]
        ).count()
        
        total_germinations = GerminationRecord.objects.filter(
            germination_date__range=[start_date, end_date]
        ).count()
        
        total_capsules = PollinationRecord.objects.filter(
            pollination_date__range=[start_date, end_date]
        ).aggregate(total=Sum('capsules_quantity'))['total'] or 0
        
        total_seedlings = GerminationRecord.objects.filter(
            germination_date__range=[start_date, end_date]
        ).aggregate(total=Sum('seedlings_germinated'))['total'] or 0
        
        return {
            'daily_averages': {
                'pollinations_per_day': round(total_pollinations / max(1, date_range_days), 2),
                'germinations_per_day': round(total_germinations / max(1, date_range_days), 2),
                'capsules_per_day': round(total_capsules / max(1, date_range_days), 2),
                'seedlings_per_day': round(total_seedlings / max(1, date_range_days), 2)
            },
            'efficiency_ratios': {
                'capsules_per_pollination': round(total_capsules / max(1, total_pollinations), 2),
                'seedlings_per_germination': round(total_seedlings / max(1, total_germinations), 2),
                'activities_per_day': round((total_pollinations + total_germinations) / max(1, date_range_days), 2)
            }
        }


class PollinationStatisticsService:
    """Service for pollination-specific statistics."""
    
    def get_statistics(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive pollination statistics."""
        start_date, end_date = self._parse_date_range(parameters)
        
        # Base queryset
        queryset = PollinationRecord.objects.filter(
            pollination_date__range=[start_date, end_date]
        )
        
        # Apply filters
        if parameters.get('responsible_id'):
            queryset = queryset.filter(responsible_id=parameters['responsible_id'])
        
        if parameters.get('pollination_type'):
            queryset = queryset.filter(pollination_type__name=parameters['pollination_type'])
        
        return {
            'summary': self._generate_summary(queryset),
            'by_type': self._get_stats_by_type(queryset),
            'by_responsible': self._get_stats_by_responsible(queryset),
            'by_genus': self._get_stats_by_genus(queryset),
            'success_analysis': self._get_success_analysis(queryset),
            'temporal_distribution': self._get_temporal_distribution(queryset, start_date, end_date)
        }
    
    def _parse_date_range(self, parameters: Dict[str, Any]) -> Tuple[date, date]:
        """Parse date range from parameters."""
        start_date = parameters.get('start_date')
        end_date = parameters.get('end_date')
        
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        if not start_date or not end_date:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=90)
        
        return start_date, end_date
    
    def _generate_summary(self, queryset) -> Dict[str, Any]:
        """Generate summary statistics for pollination."""
        total_records = queryset.count()
        
        if total_records == 0:
            return {
                'total_records': 0,
                'total_capsules': 0,
                'avg_capsules_per_record': 0,
                'unique_plants': 0,
                'unique_responsible': 0,
                'success_rate': 0
            }
        
        aggregates = queryset.aggregate(
            total_capsules=Sum('capsules_quantity'),
            avg_capsules=Avg('capsules_quantity'),
            unique_responsible=Count('responsible', distinct=True)
        )
        
        # Count unique plants involved
        unique_plants = set()
        for record in queryset.select_related('mother_plant', 'father_plant', 'new_plant'):
            if record.mother_plant:
                unique_plants.add(record.mother_plant.id)
            if record.father_plant:
                unique_plants.add(record.father_plant.id)
            if record.new_plant:
                unique_plants.add(record.new_plant.id)
        
        # Calculate success rate (records with capsules > 0)
        successful_records = queryset.filter(capsules_quantity__gt=0).count()
        success_rate = (successful_records / total_records) * 100
        
        return {
            'total_records': total_records,
            'total_capsules': aggregates['total_capsules'] or 0,
            'avg_capsules_per_record': round(aggregates['avg_capsules'] or 0, 2),
            'unique_plants': len(unique_plants),
            'unique_responsible': aggregates['unique_responsible'],
            'success_rate': round(success_rate, 2)
        }
    
    def _get_stats_by_type(self, queryset) -> List[Dict[str, Any]]:
        """Get statistics by pollination type."""
        return list(queryset.values('pollination_type__name').annotate(
            count=Count('id'),
            total_capsules=Sum('capsules_quantity'),
            avg_capsules=Avg('capsules_quantity'),
            success_count=Count('id', filter=Q(capsules_quantity__gt=0))
        ).annotate(
            success_rate=F('success_count') * 100.0 / F('count')
        ).order_by('-count'))
    
    def _get_stats_by_responsible(self, queryset) -> List[Dict[str, Any]]:
        """Get statistics by responsible person."""
        return list(queryset.values(
            'responsible__username',
            'responsible__first_name',
            'responsible__last_name'
        ).annotate(
            count=Count('id'),
            total_capsules=Sum('capsules_quantity'),
            avg_capsules=Avg('capsules_quantity')
        ).order_by('-count'))
    
    def _get_stats_by_genus(self, queryset) -> List[Dict[str, Any]]:
        """Get statistics by plant genus."""
        genus_stats = defaultdict(lambda: {'count': 0, 'capsules': []})
        
        for record in queryset.select_related('mother_plant'):
            if record.mother_plant:
                genus = record.mother_plant.genus
                genus_stats[genus]['count'] += 1
                if record.capsules_quantity:
                    genus_stats[genus]['capsules'].append(record.capsules_quantity)
        
        result = []
        for genus, data in genus_stats.items():
            avg_capsules = sum(data['capsules']) / len(data['capsules']) if data['capsules'] else 0
            result.append({
                'genus': genus,
                'count': data['count'],
                'avg_capsules': round(avg_capsules, 2)
            })
        
        return sorted(result, key=lambda x: x['count'], reverse=True)
    
    def _get_success_analysis(self, queryset) -> Dict[str, Any]:
        """Get detailed success analysis."""
        total = queryset.count()
        if total == 0:
            return {'total': 0, 'successful': 0, 'failed': 0, 'success_rate': 0}
        
        successful = queryset.filter(capsules_quantity__gt=0).count()
        failed = total - successful
        
        return {
            'total': total,
            'successful': successful,
            'failed': failed,
            'success_rate': round((successful / total) * 100, 2)
        }
    
    def _get_temporal_distribution(self, queryset, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get temporal distribution of pollination activities."""
        monthly_data = queryset.extra(
            select={'month': "strftime('%%Y-%%m', pollination_date)"}
        ).values('month').annotate(
            count=Count('id'),
            total_capsules=Sum('capsules_quantity')
        ).order_by('month')
        
        return {
            'monthly_distribution': list(monthly_data),
            'date_range_days': (end_date - start_date).days + 1
        }


class GerminationStatisticsService:
    """Service for germination-specific statistics."""
    
    def get_statistics(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive germination statistics."""
        start_date, end_date = self._parse_date_range(parameters)
        
        # Base queryset
        queryset = GerminationRecord.objects.filter(
            germination_date__range=[start_date, end_date]
        )
        
        # Apply filters
        if parameters.get('responsible_id'):
            queryset = queryset.filter(responsible_id=parameters['responsible_id'])
        
        if parameters.get('genus'):
            queryset = queryset.filter(plant__genus__icontains=parameters['genus'])
        
        return {
            'summary': self._generate_summary(queryset),
            'by_responsible': self._get_stats_by_responsible(queryset),
            'by_genus': self._get_stats_by_genus(queryset),
            'by_seed_source': self._get_stats_by_seed_source(queryset),
            'germination_rates': self._get_germination_rates(queryset),
            'temporal_distribution': self._get_temporal_distribution(queryset, start_date, end_date)
        }
    
    def _parse_date_range(self, parameters: Dict[str, Any]) -> Tuple[date, date]:
        """Parse date range from parameters."""
        start_date = parameters.get('start_date')
        end_date = parameters.get('end_date')
        
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        if not start_date or not end_date:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=90)
        
        return start_date, end_date
    
    def _generate_summary(self, queryset) -> Dict[str, Any]:
        """Generate summary statistics for germination."""
        total_records = queryset.count()
        
        if total_records == 0:
            return {
                'total_records': 0,
                'total_seedlings': 0,
                'total_seeds_planted': 0,
                'avg_seedlings_per_record': 0,
                'overall_germination_rate': 0,
                'unique_plants': 0,
                'unique_responsible': 0
            }
        
        aggregates = queryset.aggregate(
            total_seedlings=Sum('seedlings_germinated'),
            total_seeds=Sum('seeds_planted'),
            avg_seedlings=Avg('seedlings_germinated'),
            unique_plants=Count('plant', distinct=True),
            unique_responsible=Count('responsible', distinct=True)
        )
        
        # Calculate overall germination rate
        total_seeds = aggregates['total_seeds'] or 0
        total_seedlings = aggregates['total_seedlings'] or 0
        overall_rate = (total_seedlings / max(1, total_seeds)) * 100
        
        return {
            'total_records': total_records,
            'total_seedlings': total_seedlings,
            'total_seeds_planted': total_seeds,
            'avg_seedlings_per_record': round(aggregates['avg_seedlings'] or 0, 2),
            'overall_germination_rate': round(overall_rate, 2),
            'unique_plants': aggregates['unique_plants'],
            'unique_responsible': aggregates['unique_responsible']
        }
    
    def _get_stats_by_responsible(self, queryset) -> List[Dict[str, Any]]:
        """Get statistics by responsible person."""
        return list(queryset.values(
            'responsible__username',
            'responsible__first_name',
            'responsible__last_name'
        ).annotate(
            count=Count('id'),
            total_seedlings=Sum('seedlings_germinated'),
            total_seeds=Sum('seeds_planted'),
            avg_seedlings=Avg('seedlings_germinated')
        ).annotate(
            germination_rate=F('total_seedlings') * 100.0 / F('total_seeds')
        ).order_by('-count'))
    
    def _get_stats_by_genus(self, queryset) -> List[Dict[str, Any]]:
        """Get statistics by plant genus."""
        return list(queryset.values('plant__genus').annotate(
            count=Count('id'),
            total_seedlings=Sum('seedlings_germinated'),
            total_seeds=Sum('seeds_planted'),
            avg_seedlings=Avg('seedlings_germinated')
        ).annotate(
            germination_rate=F('total_seedlings') * 100.0 / F('total_seeds')
        ).order_by('-count'))
    
    def _get_stats_by_seed_source(self, queryset) -> List[Dict[str, Any]]:
        """Get statistics by seed source type."""
        return list(queryset.values('seed_source__source_type').annotate(
            count=Count('id'),
            total_seedlings=Sum('seedlings_germinated'),
            total_seeds=Sum('seeds_planted'),
            avg_seedlings=Avg('seedlings_germinated')
        ).annotate(
            germination_rate=F('total_seedlings') * 100.0 / F('total_seeds')
        ).order_by('-count'))
    
    def _get_germination_rates(self, queryset) -> Dict[str, Any]:
        """Get detailed germination rate analysis."""
        rates = []
        total_seeds = 0
        total_seedlings = 0
        
        for record in queryset:
            if record.seeds_planted > 0:
                rate = (record.seedlings_germinated / record.seeds_planted) * 100
                rates.append(rate)
                total_seeds += record.seeds_planted
                total_seedlings += record.seedlings_germinated
        
        if not rates:
            return {
                'average_rate': 0,
                'min_rate': 0,
                'max_rate': 0,
                'overall_rate': 0,
                'records_analyzed': 0
            }
        
        return {
            'average_rate': round(sum(rates) / len(rates), 2),
            'min_rate': round(min(rates), 2),
            'max_rate': round(max(rates), 2),
            'overall_rate': round((total_seedlings / max(1, total_seeds)) * 100, 2),
            'records_analyzed': len(rates)
        }
    
    def _get_temporal_distribution(self, queryset, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get temporal distribution of germination activities."""
        monthly_data = queryset.extra(
            select={'month': "strftime('%%Y-%%m', germination_date)"}
        ).values('month').annotate(
            count=Count('id'),
            total_seedlings=Sum('seedlings_germinated'),
            total_seeds=Sum('seeds_planted')
        ).order_by('month')
        
        return {
            'monthly_distribution': list(monthly_data),
            'date_range_days': (end_date - start_date).days + 1
        }