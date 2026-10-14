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


@register.simple_tag
def award_statuses():
    """The award status choices, for a drop-down: {% award_statuses as statuses %}."""
    from apps.awards.models import Award
    return Award.Status.choices
