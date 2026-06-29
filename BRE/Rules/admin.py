from django.contrib import admin
from .models import BusinessRule, EvaluationLog, DecisionThreshold


class BusinessRuleAdmin(admin.ModelAdmin):
    """Admin setup for managing business rules."""
    list_display = ('rule_name', 'field_name', 'operator', 'value', 'category',
                    'priority', 'weight', 'status', 'is_active', 'created_by')
    list_filter = ('category', 'is_active', 'status', 'action')
    search_fields = ('rule_name', 'field_name')
    list_editable = ('is_active', 'priority', 'weight', 'status')
    ordering = ('priority',)


class EvaluationLogAdmin(admin.ModelAdmin):
    """Admin setup for viewing evaluation history."""
    list_display = ('applicant_name', 'decision', 'final_score', 'risk_level',
                    'evaluated_by', 'evaluated_at')
    list_filter = ('decision', 'risk_level')
    search_fields = ('applicant_name',)
    readonly_fields = ('applicant_name', 'application_data', 'decision', 'final_score',
                       'risk_level', 'rules_passed', 'rules_failed', 'warnings',
                       'info_messages', 'full_explanation', 'evaluated_at', 'evaluated_by')


class DecisionThresholdAdmin(admin.ModelAdmin):
    """Admin setup for decision thresholds."""
    list_display = ('name', 'min_score_approve', 'min_score_review', 'is_active', 'updated_at')
    list_editable = ('is_active',)


admin.site.register(BusinessRule, BusinessRuleAdmin)
admin.site.register(EvaluationLog, EvaluationLogAdmin)
admin.site.register(DecisionThreshold, DecisionThresholdAdmin)
