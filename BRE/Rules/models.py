from django.db import models
from django.contrib.auth.models import User


# choices for the operator field
OPERATOR_CHOICES = [
    ('>', 'Greater Than'),
    ('<', 'Less Than'),
    ('>=', 'Greater Than or Equal'),
    ('<=', 'Less Than or Equal'),
    ('==', 'Equal To'),
    ('!=', 'Not Equal To'),
]

# choices for the category field
CATEGORY_CHOICES = [
    ('mandatory', 'Mandatory'),
    ('scoring', 'Scoring'),
    ('warning', 'Warning'),
    ('informational', 'Informational'),
]

# choices for the action field
ACTION_CHOICES = [
    ('reject', 'Reject'),
    ('add_score', 'Add Score'),
    ('warning', 'Warning'),
    ('info', 'Info'),
    ('continue', 'Continue'),
]

# choices for the rule status (approval workflow)
STATUS_CHOICES = [
    ('active', 'Active'),
    ('pending', 'Pending Approval'),
    ('rejected', 'Rejected'),
    ('draft', 'Draft'),
]


class BusinessRule(models.Model):
    """
    Stores a single business rule as a database record.
    Instead of writing if-else in code, we keep rules here
    so admins can change them anytime without touching code.
    """
    rule_name = models.CharField(max_length=200, help_text="A short name for this rule")
    field_name = models.CharField(max_length=100, help_text="Which field to check, e.g. salary, age, credit_score")
    operator = models.CharField(max_length=10, choices=OPERATOR_CHOICES, help_text="Comparison operator")
    value = models.CharField(max_length=200, help_text="The value to compare against")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='scoring')
    priority = models.IntegerField(default=10, help_text="Lower number runs first")
    weight = models.IntegerField(default=0, help_text="Score added when this rule passes (used for scoring rules)")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default='add_score')
    explanation_pass = models.TextField(blank=True, default='', help_text="Message shown when the rule passes")
    explanation_fail = models.TextField(blank=True, default='', help_text="Message shown when the rule fails")
    is_active = models.BooleanField(default=True, help_text="Only active rules are used during evaluation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # approval workflow fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active',
                              help_text="Current status of the rule in the approval workflow")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='created_rules',
                                   help_text="The user who created or submitted this rule")
    # if this rule is a draft edit of an existing active rule,
    # parent_rule points to the original rule it wants to replace
    parent_rule = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='draft_versions',
                                    help_text="If this is a draft edit, points to the original rule")
    admin_notes = models.TextField(blank=True, default='',
                                   help_text="Notes from admin when approving or rejecting")

    class Meta:
        ordering = ['priority', 'rule_name']

    def __str__(self):
        return f"{self.rule_name} ({self.field_name} {self.operator} {self.value})"


class EvaluationLog(models.Model):
    """
    Stores the result of every evaluation.
    This keeps a complete history so we can review past decisions.
    """
    applicant_name = models.CharField(max_length=200, default='Anonymous')
    application_data = models.TextField(help_text="JSON string of the submitted data")
    decision = models.CharField(max_length=20)  # approved, rejected, manual_review
    final_score = models.IntegerField(default=0)
    risk_level = models.CharField(max_length=20, default='unknown')  # low, medium, high
    rules_passed = models.TextField(default='[]', help_text="JSON list of passed rule names")
    rules_failed = models.TextField(default='[]', help_text="JSON list of failed rule names")
    warnings = models.TextField(default='[]', help_text="JSON list of warning messages")
    info_messages = models.TextField(default='[]', help_text="JSON list of info messages")
    full_explanation = models.TextField(default='', help_text="Complete human-readable explanation")
    evaluated_at = models.DateTimeField(auto_now_add=True)

    # track which employee ran this evaluation
    evaluated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='evaluations',
                                     help_text="The employee who ran this evaluation")

    class Meta:
        ordering = ['-evaluated_at']

    def __str__(self):
        return f"{self.applicant_name} - {self.decision} (Score: {self.final_score})"


class DecisionThreshold(models.Model):
    """
    Configurable thresholds that decide approval, manual review, or rejection.
    Only one threshold should be active at a time.
    """
    name = models.CharField(max_length=100, default='Default Threshold')
    min_score_approve = models.IntegerField(default=80, help_text="Score >= this means Approved")
    min_score_review = models.IntegerField(default=60, help_text="Score >= this but < approve means Manual Review")
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (Approve >= {self.min_score_approve}, Review >= {self.min_score_review})"
