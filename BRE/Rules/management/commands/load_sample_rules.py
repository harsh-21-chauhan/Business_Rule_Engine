from django.core.management.base import BaseCommand
from Rules.models import BusinessRule, DecisionThreshold


class Command(BaseCommand):
    help = 'Load sample business rules for a loan approval demo'

    def handle(self, *args, **options):
        # clear existing rules if any
        BusinessRule.objects.all().delete()
        DecisionThreshold.objects.all().delete()

        self.stdout.write("Loading sample rules...")

        # ----- Mandatory Rules -----
        BusinessRule.objects.create(
            rule_name='Fraud Flag Check',
            field_name='fraud_flag',
            operator='==',
            value='false',
            category='mandatory',
            priority=1,
            weight=0,
            action='reject',
            explanation_pass='No fraud detected',
            explanation_fail='Fraud flag is raised — application rejected immediately',
            is_active=True,
        )

        BusinessRule.objects.create(
            rule_name='Minimum Age Requirement',
            field_name='age',
            operator='>=',
            value='21',
            category='mandatory',
            priority=2,
            weight=0,
            action='continue',
            explanation_pass='Applicant meets minimum age requirement',
            explanation_fail='Applicant is below the minimum age of 21',
            is_active=True,
        )

        BusinessRule.objects.create(
            rule_name='Identity Verified',
            field_name='identity_verified',
            operator='==',
            value='true',
            category='mandatory',
            priority=3,
            weight=0,
            action='continue',
            explanation_pass='Identity verification passed',
            explanation_fail='Identity could not be verified — application rejected',
            is_active=True,
        )

        # ----- Scoring Rules -----
        BusinessRule.objects.create(
            rule_name='Salary Requirement',
            field_name='salary',
            operator='>',
            value='50000',
            category='scoring',
            priority=4,
            weight=20,
            action='add_score',
            explanation_pass='Salary meets the requirement (+20 points)',
            explanation_fail='Salary is below the threshold (0 points)',
            is_active=True,
        )

        BusinessRule.objects.create(
            rule_name='Credit Score Check',
            field_name='credit_score',
            operator='>',
            value='700',
            category='scoring',
            priority=5,
            weight=30,
            action='add_score',
            explanation_pass='Excellent credit score (+30 points)',
            explanation_fail='Credit score is below 700 (0 points)',
            is_active=True,
        )

        BusinessRule.objects.create(
            rule_name='Employment Duration',
            field_name='employment_years',
            operator='>=',
            value='2',
            category='scoring',
            priority=6,
            weight=15,
            action='add_score',
            explanation_pass='Stable employment history (+15 points)',
            explanation_fail='Employment duration is less than 2 years (0 points)',
            is_active=True,
        )

        BusinessRule.objects.create(
            rule_name='Existing Customer Bonus',
            field_name='existing_customer',
            operator='==',
            value='true',
            category='scoring',
            priority=7,
            weight=10,
            action='add_score',
            explanation_pass='Existing customer — loyalty bonus (+10 points)',
            explanation_fail='Not an existing customer (0 points)',
            is_active=True,
        )

        BusinessRule.objects.create(
            rule_name='Low Debt Ratio',
            field_name='debt_ratio',
            operator='<',
            value='40',
            category='scoring',
            priority=8,
            weight=10,
            action='add_score',
            explanation_pass='Healthy debt-to-income ratio (+10 points)',
            explanation_fail='Debt ratio is above 40% (0 points)',
            is_active=True,
        )

        # ----- Warning Rules -----
        BusinessRule.objects.create(
            rule_name='High EMI Ratio Warning',
            field_name='emi_ratio',
            operator='>',
            value='50',
            category='warning',
            priority=9,
            weight=0,
            action='warning',
            explanation_pass='Warning: EMI ratio is above 50% — high monthly obligation',
            explanation_fail='',
            is_active=True,
        )

        BusinessRule.objects.create(
            rule_name='Frequent Applications Warning',
            field_name='recent_applications',
            operator='>',
            value='3',
            category='warning',
            priority=10,
            weight=0,
            action='warning',
            explanation_pass='Warning: Multiple recent applications detected',
            explanation_fail='',
            is_active=True,
        )

        # ----- Informational Rules -----
        BusinessRule.objects.create(
            rule_name='Premium Customer Check',
            field_name='premium_customer',
            operator='==',
            value='true',
            category='informational',
            priority=11,
            weight=0,
            action='info',
            explanation_pass='Applicant is a premium customer',
            explanation_fail='',
            is_active=True,
        )

        # ----- Decision Threshold -----
        DecisionThreshold.objects.create(
            name='Default Loan Threshold',
            min_score_approve=80,
            min_score_review=60,
            is_active=True,
        )

        total = BusinessRule.objects.count()
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {total} sample rules and 1 threshold!'))
        self.stdout.write('')
        self.stdout.write('Sample rules loaded:')
        self.stdout.write('  Mandatory: Fraud Check, Age Check, Identity Verification')
        self.stdout.write('  Scoring:   Salary, Credit Score, Employment, Existing Customer, Debt Ratio')
        self.stdout.write('  Warning:   High EMI, Frequent Applications')
        self.stdout.write('  Info:      Premium Customer')
        self.stdout.write('')
        self.stdout.write('Threshold: Approve >= 80, Manual Review >= 60, Reject < 60')
