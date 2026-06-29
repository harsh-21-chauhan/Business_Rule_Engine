from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
import json

from .models import BusinessRule, EvaluationLog, DecisionThreshold
from .models import OPERATOR_CHOICES, CATEGORY_CHOICES, ACTION_CHOICES
from .evaluator import evaluate_application


# ============================================================
# Authentication Views
# ============================================================

def login_view(request):
    """Login page. If already logged in, redirect to home."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # redirect to the page they were trying to access, or home
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'Rules/login.html')


def register_view(request):
    """Registration page for new employees."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        # basic validation
        if not username or not password:
            messages.error(request, 'Username and password are required.')
        elif password != password2:
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken. Please choose another.')
        else:
            # create the user (regular employee, NOT superuser)
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            messages.success(request, f'Welcome {username}! Your account has been created.')
            return redirect('home')

    return render(request, 'Rules/register.html')


def logout_view(request):
    """Log the user out and redirect to login page."""
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')


# ============================================================
# Home Page
# ============================================================

@login_required
def home(request):
    """Landing page with a quick overview of the system."""
    total_rules = BusinessRule.objects.filter(status='active').count()
    active_rules = BusinessRule.objects.filter(is_active=True, status='active').count()
    total_evaluations = EvaluationLog.objects.count()

    # count decisions
    approved_count = EvaluationLog.objects.filter(decision='approved').count()
    rejected_count = EvaluationLog.objects.filter(decision='rejected').count()
    review_count = EvaluationLog.objects.filter(decision='manual_review').count()

    # pending count for admin badge
    pending_count = BusinessRule.objects.filter(status='pending').count()

    context = {
        'total_rules': total_rules,
        'active_rules': active_rules,
        'total_evaluations': total_evaluations,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'review_count': review_count,
        'pending_count': pending_count,
    }
    return render(request, 'Rules/home.html', context)


# ============================================================
# Rule Management
# ============================================================

@login_required
def rule_list(request):
    """Show all business rules in a table."""
    if request.user.is_superuser:
        # admin sees everything
        rules = BusinessRule.objects.all().order_by('priority')
    else:
        # employees see active rules + their own pending/rejected drafts
        from django.db.models import Q
        rules = BusinessRule.objects.filter(
            Q(status='active') | Q(created_by=request.user)
        ).order_by('priority')

    # count pending for navbar badge
    pending_count = BusinessRule.objects.filter(status='pending').count()

    context = {
        'rules': rules,
        'pending_count': pending_count,
    }
    return render(request, 'Rules/rule_list.html', context)


@login_required
def add_rule(request):
    """Form to create a new business rule."""
    if request.method == 'POST':
        rule = BusinessRule()
        rule.rule_name = request.POST.get('rule_name', '').strip()
        rule.field_name = request.POST.get('field_name', '').strip()
        rule.operator = request.POST.get('operator', '>')
        rule.value = request.POST.get('value', '').strip()
        rule.category = request.POST.get('category', 'scoring')
        rule.priority = int(request.POST.get('priority', 10))
        rule.weight = int(request.POST.get('weight', 0))
        rule.action = request.POST.get('action', 'add_score')
        rule.explanation_pass = request.POST.get('explanation_pass', '').strip()
        rule.explanation_fail = request.POST.get('explanation_fail', '').strip()
        rule.created_by = request.user

        if request.user.is_superuser:
            # admin's rules go live immediately
            rule.status = 'active'
            rule.is_active = request.POST.get('is_active') == 'on'
            rule.save()
            messages.success(request, f'Rule "{rule.rule_name}" created and is now active!')
        else:
            # employee's rules go to pending status
            rule.status = 'pending'
            rule.is_active = False
            rule.save()
            messages.success(request, f'Rule "{rule.rule_name}" submitted for admin approval!')

        return redirect('rule_list')

    context = {
        'operator_choices': OPERATOR_CHOICES,
        'category_choices': CATEGORY_CHOICES,
        'action_choices': ACTION_CHOICES,
    }
    return render(request, 'Rules/add_rule.html', context)


@login_required
def edit_rule(request, rule_id):
    """Form to edit an existing rule."""
    original_rule = get_object_or_404(BusinessRule, id=rule_id)

    if request.method == 'POST':
        if request.user.is_superuser:
            # admin edits the rule directly (no draft needed)
            original_rule.rule_name = request.POST.get('rule_name', '').strip()
            original_rule.field_name = request.POST.get('field_name', '').strip()
            original_rule.operator = request.POST.get('operator', '>')
            original_rule.value = request.POST.get('value', '').strip()
            original_rule.category = request.POST.get('category', 'scoring')
            original_rule.priority = int(request.POST.get('priority', 10))
            original_rule.weight = int(request.POST.get('weight', 0))
            original_rule.action = request.POST.get('action', 'add_score')
            original_rule.explanation_pass = request.POST.get('explanation_pass', '').strip()
            original_rule.explanation_fail = request.POST.get('explanation_fail', '').strip()
            original_rule.is_active = request.POST.get('is_active') == 'on'
            original_rule.save()

            messages.success(request, f'Rule "{original_rule.rule_name}" updated successfully!')
        else:
            # employee creates a draft copy linked to the original
            draft = BusinessRule()
            draft.rule_name = request.POST.get('rule_name', '').strip()
            draft.field_name = request.POST.get('field_name', '').strip()
            draft.operator = request.POST.get('operator', '>')
            draft.value = request.POST.get('value', '').strip()
            draft.category = request.POST.get('category', 'scoring')
            draft.priority = int(request.POST.get('priority', 10))
            draft.weight = int(request.POST.get('weight', 0))
            draft.action = request.POST.get('action', 'add_score')
            draft.explanation_pass = request.POST.get('explanation_pass', '').strip()
            draft.explanation_fail = request.POST.get('explanation_fail', '').strip()
            draft.status = 'pending'
            draft.is_active = False
            draft.created_by = request.user
            draft.parent_rule = original_rule  # link to original
            draft.save()

            messages.success(request, f'Your changes to "{original_rule.rule_name}" have been submitted for admin approval!')

        return redirect('rule_list')

    context = {
        'rule': original_rule,
        'operator_choices': OPERATOR_CHOICES,
        'category_choices': CATEGORY_CHOICES,
        'action_choices': ACTION_CHOICES,
    }
    return render(request, 'Rules/edit_rule.html', context)


@login_required
def delete_rule(request, rule_id):
    """Delete a rule with confirmation. Only admin can delete."""
    rule = get_object_or_404(BusinessRule, id=rule_id)

    # only admin can delete rules, or employee can delete their own pending drafts
    if not request.user.is_superuser and rule.created_by != request.user:
        messages.error(request, 'Only administrators can delete rules.')
        return redirect('rule_list')

    if not request.user.is_superuser and rule.status == 'active':
        messages.error(request, 'Only administrators can delete active rules.')
        return redirect('rule_list')

    if request.method == 'POST':
        name = rule.rule_name
        rule.delete()
        messages.success(request, f'Rule "{name}" deleted successfully!')
        return redirect('rule_list')

    context = {'rule': rule}
    return render(request, 'Rules/delete_confirm.html', context)


@login_required
def toggle_rule(request, rule_id):
    """Activate or deactivate a rule. Only admin can toggle."""
    if not request.user.is_superuser:
        messages.error(request, 'Only administrators can activate or deactivate rules.')
        return redirect('rule_list')

    rule = get_object_or_404(BusinessRule, id=rule_id)
    rule.is_active = not rule.is_active
    rule.save()

    status = "activated" if rule.is_active else "deactivated"
    messages.success(request, f'Rule "{rule.rule_name}" {status}!')
    return redirect('rule_list')


# ============================================================
# Approval Workflow (Admin Only)
# ============================================================

@login_required
def pending_approvals(request):
    """Shows all rules waiting for admin approval. Admin only."""
    if not request.user.is_superuser:
        messages.error(request, 'Only administrators can access this page.')
        return redirect('home')

    pending_rules = BusinessRule.objects.filter(status='pending').order_by('-created_at')
    pending_count = pending_rules.count()

    context = {
        'pending_rules': pending_rules,
        'pending_count': pending_count,
    }
    return render(request, 'Rules/pending_approvals.html', context)


@login_required
def approve_rule(request, rule_id):
    """Admin approves a pending rule."""
    if not request.user.is_superuser:
        messages.error(request, 'Only administrators can approve rules.')
        return redirect('home')

    rule = get_object_or_404(BusinessRule, id=rule_id, status='pending')

    if request.method == 'POST':
        admin_notes = request.POST.get('admin_notes', '').strip()
        rule.admin_notes = admin_notes

        if rule.parent_rule:
            # this is a draft edit of an existing rule
            # replace the original rule's data with the draft's data
            original = rule.parent_rule
            original.rule_name = rule.rule_name
            original.field_name = rule.field_name
            original.operator = rule.operator
            original.value = rule.value
            original.category = rule.category
            original.priority = rule.priority
            original.weight = rule.weight
            original.action = rule.action
            original.explanation_pass = rule.explanation_pass
            original.explanation_fail = rule.explanation_fail
            original.save()

            # delete the draft since changes are merged
            rule_name = rule.rule_name
            rule.delete()
            messages.success(request, f'Changes to "{rule_name}" approved and merged into the active rule!')
        else:
            # this is a brand new rule, make it active
            rule.status = 'active'
            rule.is_active = True
            rule.save()
            messages.success(request, f'Rule "{rule.rule_name}" approved and is now active!')

        return redirect('pending_approvals')

    context = {'rule': rule}
    return render(request, 'Rules/approve_rule.html', context)


@login_required
def reject_rule(request, rule_id):
    """Admin rejects a pending rule."""
    if not request.user.is_superuser:
        messages.error(request, 'Only administrators can reject rules.')
        return redirect('home')

    rule = get_object_or_404(BusinessRule, id=rule_id, status='pending')

    if request.method == 'POST':
        admin_notes = request.POST.get('admin_notes', '').strip()
        rule.status = 'rejected'
        rule.admin_notes = admin_notes
        rule.save()
        messages.success(request, f'Rule "{rule.rule_name}" has been rejected.')
        return redirect('pending_approvals')

    context = {'rule': rule}
    return render(request, 'Rules/reject_rule.html', context)


# ============================================================
# Evaluation
# ============================================================

@login_required
def evaluate(request):
    """
    Application evaluation page.
    Shows a form where users enter application data,
    then runs the evaluator and shows the result.
    """
    result = None

    if request.method == 'POST':
        applicant_name = request.POST.get('applicant_name', 'Anonymous').strip()

        # collect all the field values from the form
        active_rules = BusinessRule.objects.filter(is_active=True, status='active')
        field_names = set()
        for rule in active_rules:
            field_names.add(rule.field_name)

        application_data = {}
        for field in field_names:
            raw_value = request.POST.get(field, '').strip()
            if raw_value:
                try:
                    application_data[field] = float(raw_value)
                    if application_data[field] == int(application_data[field]):
                        application_data[field] = int(application_data[field])
                except ValueError:
                    application_data[field] = raw_value

        # run the evaluator and pass the current user
        result = evaluate_application(
            application_data,
            applicant_name=applicant_name,
            save_log=True,
            evaluated_by=request.user,
        )

    # get unique field names from active rules so we can build the form dynamically
    active_rules = BusinessRule.objects.filter(is_active=True, status='active')
    field_names = []
    seen = set()
    for rule in active_rules:
        if rule.field_name not in seen:
            field_names.append(rule.field_name)
            seen.add(rule.field_name)

    context = {
        'field_names': field_names,
        'result': result,
    }
    return render(request, 'Rules/evaluate.html', context)


# ============================================================
# Evaluation History
# ============================================================

@login_required
def evaluation_history(request):
    """Show all past evaluations."""
    logs = EvaluationLog.objects.all().order_by('-evaluated_at')
    context = {'logs': logs}
    return render(request, 'Rules/history.html', context)


@login_required
def evaluation_detail(request, log_id):
    """Detailed view of a single evaluation."""
    log = get_object_or_404(EvaluationLog, id=log_id)

    # parse JSON fields for display
    try:
        rules_passed = json.loads(log.rules_passed)
    except json.JSONDecodeError:
        rules_passed = []

    try:
        rules_failed = json.loads(log.rules_failed)
    except json.JSONDecodeError:
        rules_failed = []

    try:
        warnings_list = json.loads(log.warnings)
    except json.JSONDecodeError:
        warnings_list = []

    try:
        info_list = json.loads(log.info_messages)
    except json.JSONDecodeError:
        info_list = []

    try:
        app_data = json.loads(log.application_data)
    except json.JSONDecodeError:
        app_data = {}

    context = {
        'log': log,
        'rules_passed': rules_passed,
        'rules_failed': rules_failed,
        'warnings_list': warnings_list,
        'info_list': info_list,
        'app_data': app_data,
    }
    return render(request, 'Rules/evaluation_detail.html', context)


# ============================================================
# Simulation
# ============================================================

@login_required
def simulate(request):
    """
    Test rules with sample data WITHOUT saving to the database.
    Useful for admins to verify rules before going live.
    """
    result = None

    if request.method == 'POST':
        applicant_name = request.POST.get('applicant_name', 'Test User').strip()

        active_rules = BusinessRule.objects.filter(is_active=True, status='active')
        field_names = set()
        for rule in active_rules:
            field_names.add(rule.field_name)

        application_data = {}
        for field in field_names:
            raw_value = request.POST.get(field, '').strip()
            if raw_value:
                try:
                    application_data[field] = float(raw_value)
                    if application_data[field] == int(application_data[field]):
                        application_data[field] = int(application_data[field])
                except ValueError:
                    application_data[field] = raw_value

        # save_log=False so this is just a simulation
        result = evaluate_application(application_data, applicant_name=applicant_name, save_log=False)

    active_rules = BusinessRule.objects.filter(is_active=True, status='active')
    field_names = []
    seen = set()
    for rule in active_rules:
        if rule.field_name not in seen:
            field_names.append(rule.field_name)
            seen.add(rule.field_name)

    context = {
        'field_names': field_names,
        'result': result,
    }
    return render(request, 'Rules/simulate.html', context)


# ============================================================
# Dashboard
# ============================================================

@login_required
def dashboard(request):
    """Statistics overview page."""
    total_rules = BusinessRule.objects.filter(status='active').count()
    active_rules = BusinessRule.objects.filter(is_active=True, status='active').count()
    inactive_rules = total_rules - active_rules

    mandatory_count = BusinessRule.objects.filter(category='mandatory', is_active=True, status='active').count()
    scoring_count = BusinessRule.objects.filter(category='scoring', is_active=True, status='active').count()
    warning_count = BusinessRule.objects.filter(category='warning', is_active=True, status='active').count()
    info_count = BusinessRule.objects.filter(category='informational', is_active=True, status='active').count()

    total_evaluations = EvaluationLog.objects.count()
    approved_count = EvaluationLog.objects.filter(decision='approved').count()
    rejected_count = EvaluationLog.objects.filter(decision='rejected').count()
    review_count = EvaluationLog.objects.filter(decision='manual_review').count()

    # approval rate
    if total_evaluations > 0:
        approval_rate = round((approved_count / total_evaluations) * 100, 1)
    else:
        approval_rate = 0

    # recent evaluations
    recent_logs = EvaluationLog.objects.all().order_by('-evaluated_at')[:10]

    # active threshold
    threshold = DecisionThreshold.objects.filter(is_active=True).first()

    # pending count for admin
    pending_count = BusinessRule.objects.filter(status='pending').count()

    context = {
        'total_rules': total_rules,
        'active_rules': active_rules,
        'inactive_rules': inactive_rules,
        'mandatory_count': mandatory_count,
        'scoring_count': scoring_count,
        'warning_count': warning_count,
        'info_count': info_count,
        'total_evaluations': total_evaluations,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'review_count': review_count,
        'approval_rate': approval_rate,
        'recent_logs': recent_logs,
        'threshold': threshold,
        'pending_count': pending_count,
    }
    return render(request, 'Rules/dashboard.html', context)
