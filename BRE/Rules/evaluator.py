import json
from .models import BusinessRule, EvaluationLog, DecisionThreshold


def compare_values(applicant_value, operator, rule_value):
    """
    Compare two values using the given operator.
    We try to convert both to numbers first. If that fails,
    we compare them as strings (useful for True/False checks etc).
    """
    # try converting to float for numeric comparison
    try:
        applicant_num = float(applicant_value)
        rule_num = float(rule_value)

        if operator == '>':
            return applicant_num > rule_num
        elif operator == '<':
            return applicant_num < rule_num
        elif operator == '>=':
            return applicant_num >= rule_num
        elif operator == '<=':
            return applicant_num <= rule_num
        elif operator == '==':
            return applicant_num == rule_num
        elif operator == '!=':
            return applicant_num != rule_num
        else:
            return False

    except (ValueError, TypeError):
        # if not numbers, compare as strings (case-insensitive)
        applicant_str = str(applicant_value).strip().lower()
        rule_str = str(rule_value).strip().lower()

        if operator == '==':
            return applicant_str == rule_str
        elif operator == '!=':
            return applicant_str != rule_str
        else:
            # other operators don't make sense for strings
            return False


def get_risk_level(score):
    """Simple risk level based on score."""
    if score >= 80:
        return 'low'
    elif score >= 60:
        return 'medium'
    else:
        return 'high'


def evaluate_application(application_data, applicant_name='Anonymous', save_log=True, evaluated_by=None):
    """
    Main evaluation function. This is the heart of the BRE.

    It reads all active rules from the database, evaluates them
    against the application data, computes a score, and returns
    a complete decision with explanation.

    Parameters:
        application_data: dict with field names and values
                          e.g. {'salary': 70000, 'age': 25, 'credit_score': 760}
        applicant_name: name of the person being evaluated
        save_log: whether to save this evaluation to the database
        evaluated_by: the User object who ran this evaluation

    Returns:
        dict with decision, score, risk_level, passed/failed rules, explanation, etc.
    """

    # fetch all active and approved rules sorted by priority
    all_rules = BusinessRule.objects.filter(is_active=True, status='active').order_by('priority')

    # separate rules by category
    mandatory_rules = [r for r in all_rules if r.category == 'mandatory']
    scoring_rules = [r for r in all_rules if r.category == 'scoring']
    warning_rules = [r for r in all_rules if r.category == 'warning']
    info_rules = [r for r in all_rules if r.category == 'informational']

    # result tracking
    rules_passed = []
    rules_failed = []
    warnings_list = []
    info_list = []
    total_score = 0
    explanation_lines = []
    rejected_early = False
    rejection_reason = ''

    # ---- Step 1: Evaluate mandatory rules first ----
    for rule in mandatory_rules:
        field_value = application_data.get(rule.field_name, None)

        if field_value is None:
            # if the field is missing, mandatory rule fails
            rules_failed.append(rule.rule_name)
            explanation_lines.append(f"FAILED: {rule.rule_name} - Field '{rule.field_name}' is missing")
            rejected_early = True
            rejection_reason = rule.explanation_fail if rule.explanation_fail else f"Mandatory check failed: {rule.rule_name}"
            break

        passed = compare_values(field_value, rule.operator, rule.value)

        if passed:
            rules_passed.append(rule.rule_name)
            msg = rule.explanation_pass if rule.explanation_pass else f"Passed: {rule.rule_name}"
            explanation_lines.append(f"✓ {msg}")
        else:
            rules_failed.append(rule.rule_name)
            msg = rule.explanation_fail if rule.explanation_fail else f"Failed: {rule.rule_name}"
            explanation_lines.append(f"✗ {msg}")
            rejected_early = True
            rejection_reason = msg
            break  # stop immediately on mandatory failure

    # ---- Step 2: If mandatory rules passed, evaluate scoring rules ----
    if not rejected_early:
        for rule in scoring_rules:
            field_value = application_data.get(rule.field_name, None)

            if field_value is None:
                rules_failed.append(rule.rule_name)
                explanation_lines.append(f"✗ {rule.rule_name} - Field '{rule.field_name}' not provided (0 points)")
                continue

            passed = compare_values(field_value, rule.operator, rule.value)

            if passed:
                total_score += rule.weight
                rules_passed.append(rule.rule_name)
                msg = rule.explanation_pass if rule.explanation_pass else f"{rule.rule_name} (+{rule.weight} points)"
                explanation_lines.append(f"✓ {msg}")
            else:
                rules_failed.append(rule.rule_name)
                msg = rule.explanation_fail if rule.explanation_fail else f"{rule.rule_name} (0 points)"
                explanation_lines.append(f"✗ {msg}")

    # ---- Step 3: Evaluate warning rules ----
    if not rejected_early:
        for rule in warning_rules:
            field_value = application_data.get(rule.field_name, None)

            if field_value is None:
                continue  # skip if field not provided

            passed = compare_values(field_value, rule.operator, rule.value)

            if passed:
                msg = rule.explanation_pass if rule.explanation_pass else f"Warning: {rule.rule_name}"
                warnings_list.append(msg)
                explanation_lines.append(f"⚠ {msg}")

    # ---- Step 4: Evaluate informational rules ----
    if not rejected_early:
        for rule in info_rules:
            field_value = application_data.get(rule.field_name, None)

            if field_value is None:
                continue

            passed = compare_values(field_value, rule.operator, rule.value)

            if passed:
                msg = rule.explanation_pass if rule.explanation_pass else f"Info: {rule.rule_name}"
                info_list.append(msg)
                explanation_lines.append(f"ℹ {msg}")

    # ---- Step 5: Determine final decision ----
    if rejected_early:
        decision = 'rejected'
        risk_level = 'high'
        explanation_lines.insert(0, f"REJECTED — {rejection_reason}")
    else:
        # get active threshold
        threshold = DecisionThreshold.objects.filter(is_active=True).first()

        if threshold:
            approve_score = threshold.min_score_approve
            review_score = threshold.min_score_review
        else:
            # default thresholds if none set
            approve_score = 80
            review_score = 60

        if total_score >= approve_score:
            decision = 'approved'
        elif total_score >= review_score:
            decision = 'manual_review'
        else:
            decision = 'rejected'

        risk_level = get_risk_level(total_score)

        # add score summary to explanation
        explanation_lines.insert(0, f"Final Score: {total_score}")
        explanation_lines.insert(1, f"Decision: {decision.upper()}")
        explanation_lines.insert(2, f"Risk Level: {risk_level.upper()}")
        explanation_lines.insert(3, "---")

    # build full explanation text
    full_explanation = '\n'.join(explanation_lines)

    # ---- Step 6: Save evaluation log ----
    if save_log:
        EvaluationLog.objects.create(
            applicant_name=applicant_name,
            application_data=json.dumps(application_data),
            decision=decision,
            final_score=total_score,
            risk_level=risk_level,
            rules_passed=json.dumps(rules_passed),
            rules_failed=json.dumps(rules_failed),
            warnings=json.dumps(warnings_list),
            info_messages=json.dumps(info_list),
            full_explanation=full_explanation,
            evaluated_by=evaluated_by,
        )

    # return everything
    result = {
        'applicant_name': applicant_name,
        'decision': decision,
        'final_score': total_score,
        'risk_level': risk_level,
        'rules_passed': rules_passed,
        'rules_failed': rules_failed,
        'warnings': warnings_list,
        'info_messages': info_list,
        'full_explanation': full_explanation,
        'application_data': application_data,
    }

    return result
