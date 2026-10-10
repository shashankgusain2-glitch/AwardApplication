from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Look up a dictionary value by key in a template: {{ dict|get_item:key }}."""
    return mapping.get(key, "")
