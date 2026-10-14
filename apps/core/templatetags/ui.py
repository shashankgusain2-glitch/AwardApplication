from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Look up a dictionary value by key in a template: {{ dict|get_item:key }}."""
    return mapping.get(key, "")


@register.filter
def ready_problems(award):
    """What an award still needs before it can open: {{ award|ready_problems }} (empty = ready)."""
    from apps.awards.services import ready_to_open
    return ready_to_open(award)


@register.filter
def judging_problems(award):
    """What an award still needs before judges can be assigned: {{ award|judging_problems }}."""
    from apps.awards.services import ready_to_judge
    return ready_to_judge(award)


@register.filter
def judged_percent(obj):
    """How much is judged, 0-100: {{ report|judged_percent }} (all its judges) or {{ assignment|judged_percent }}."""
    from apps.applications.models import Application
    from apps.evaluations.services import assignment_progress, report_progress
    return report_progress(obj) if isinstance(obj, Application) else assignment_progress(obj)


@register.inclusion_tag("partials/judged_bar.html")
def judged_bar(obj, label="judged"):
    """A small progress bar with its percentage: {% judged_bar report %}."""
    return {"percent": judged_percent(obj), "label": label}


@register.simple_tag
def award_statuses():
    """The award status choices, for a drop-down: {% award_statuses as statuses %}."""
    from apps.awards.models import Award
    return Award.Status.choices
