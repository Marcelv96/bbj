from django import template

register = template.Library()

from django import template

register = template.Library()

@register.filter
def replace(value, args):
    old, new = args.split(',')
    return value.replace(old, new)



@register.filter(name='range')
def filter_range(number):
    return range(number)


@register.filter
def replace(value, arg):
    """Usage: {{ value|replace:"old,new" }}"""
    if "," in arg:
        old, new = arg.split(',')
        return value.replace(old, new)
    return value.replace(arg, ' ')

@register.filter
def replace_underscore(value, arg):
    """
    Usage:
    {{ value|replace_underscore:"find,replace_with" }}
    """
    if not value or "," not in arg:
        return value

    find, replace_with = arg.split(",", 1)
    return str(value).replace(find, replace_with)


@register.filter
def replace(value, arg):
    """
    Usage:
    {{ value|replace:"old,new" }}
    """
    if not value or "," not in arg:
        return value

    old, new = arg.split(",", 1)
    return str(value).replace(old, new)


@register.filter(name="split")
def split_filter(value, key):
    """
    Usage:
    {{ "a,b,c"|split:"," }}
    """
    if value is None:
        return []
    return str(value).split(key)


@register.filter
def get_item(dictionary, key):
    """
    Usage:
    {{ my_dict|get_item:"some_key" }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def get_attr(obj, attr):
    """
    Usage:
    {{ obj|get_attr:"field_name" }}
    """
    return getattr(obj, attr, None)
