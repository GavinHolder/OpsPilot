from django import template

register = template.Library()

@register.filter(name='abs')
def abs_filter(value):
    """Returns the absolute value of a number"""
    try:
        return abs(int(value))
    except (ValueError, TypeError):
        return value