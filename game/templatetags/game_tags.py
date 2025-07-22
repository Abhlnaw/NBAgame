from django import template

register = template.Library()

@register.filter
def get_range(value):
    return range(1, value + 1)

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def multiply(value, arg):
    """Multiplies the arg and the value."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter
def replace_underscores(value):
    """Replace underscores with spaces and title case."""
    return str(value).replace('_', ' ').title()

@register.filter
def count_won(score_details):
    """Count how many attributes were won."""
    if not isinstance(score_details, dict):
        return 0
    return sum(1 for attr_data in score_details.values() if attr_data.get('won') is True)

@register.filter
def count_lost(score_details):
    """Count how many attributes were lost."""
    if not isinstance(score_details, dict):
        return 0
    return sum(1 for attr_data in score_details.values() if attr_data.get('won') is False)

@register.filter
def count_tied(score_details):
    """Count how many attributes were tied."""
    if not isinstance(score_details, dict):
        return 0
    return sum(1 for attr_data in score_details.values() if attr_data.get('won') is None) 