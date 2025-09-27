from rest_framework import serializers
from alerts.models import Alert, AlertType, UserAlert
from pollination.serializers import PollinationRecordSerializer
from germination.serializers import GerminationRecordSerializer


class AlertTypeSerializer(serializers.ModelSerializer):
    """Serializer for AlertType model"""
    
    class Meta:
        model = AlertType
        fields = [
            'id', 'name', 'description', 'is_active', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AlertSerializer(serializers.ModelSerializer):
    """Serializer for Alert model"""
    
    alert_type = AlertTypeSerializer(read_only=True)
    alert_type_name = serializers.CharField(source='alert_type.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    # Related record information (optional, only included when present)
    pollination_record = PollinationRecordSerializer(read_only=True)
    germination_record = GerminationRecordSerializer(read_only=True)
    
    class Meta:
        model = Alert
        fields = [
            'id', 'alert_type', 'alert_type_name', 'title', 'message',
            'status', 'status_display', 'priority', 'priority_display',
            'scheduled_date', 'expires_at', 'is_expired', 'metadata',
            'pollination_record', 'germination_record',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'alert_type', 'alert_type_name', 'status_display', 
            'priority_display', 'is_expired', 'pollination_record', 
            'germination_record', 'created_at', 'updated_at'
        ]


class UserAlertSerializer(serializers.ModelSerializer):
    """Serializer for UserAlert model"""
    
    alert = AlertSerializer(read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserAlert
        fields = [
            'id', 'user', 'user_username', 'alert', 'is_read', 'read_at',
            'is_dismissed', 'dismissed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'user_username', 'alert', 'read_at', 
            'dismissed_at', 'created_at', 'updated_at'
        ]


class NotificationSummarySerializer(serializers.Serializer):
    """Serializer for notification summary data"""
    
    total_notifications = serializers.IntegerField()
    unread_notifications = serializers.IntegerField()
    urgent_notifications = serializers.IntegerField()
    high_priority_notifications = serializers.IntegerField()
    recent_notifications = serializers.IntegerField()
    has_urgent = serializers.BooleanField()
    has_unread = serializers.BooleanField()


class MarkNotificationActionSerializer(serializers.Serializer):
    """Serializer for notification action requests"""
    
    alert_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=['read', 'dismiss'])
    
    def validate_alert_id(self, value):
        """Validate that the alert exists and belongs to the user"""
        user = self.context['request'].user
        try:
            UserAlert.objects.get(user=user, alert_id=value)
        except UserAlert.DoesNotExist:
            raise serializers.ValidationError("Alert not found or doesn't belong to user")
        return value


class BulkNotificationActionSerializer(serializers.Serializer):
    """Serializer for bulk notification actions"""
    
    action = serializers.ChoiceField(choices=['mark_all_read', 'dismiss_all_read'])
    alert_type = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.ChoiceField(
        choices=['low', 'medium', 'high', 'urgent'],
        required=False,
        allow_blank=True
    )
    
    def validate_alert_type(self, value):
        """Validate alert type if provided"""
        if value and not AlertType.objects.filter(name=value).exists():
            raise serializers.ValidationError("Invalid alert type")
        return value