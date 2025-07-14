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