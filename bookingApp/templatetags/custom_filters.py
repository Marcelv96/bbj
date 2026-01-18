from django import template

register = template.Library()

from django import template

register = template.Library()
from django import template

register = template.Library()
from django import template
import hashlib

register = template.Library()

# A small palette of accessible background colors
_PALETTE = [
    "#eef2ff",  # indigo-50
    "#fff1f2",  # rose-50
    "#ecfdf5",  # emerald-50
    "#fff7ed",  # amber-50
    "#f0f9ff",  # sky-50
    "#fffbeb",  # amber-50 (alt)
    "#fff5f5",  # rose-50 (alt)
    "#f8fafc",  # slate-50 (neutral)
]


@register.filter(name="hashcolor")
def hashcolor(value):
    """
    Deterministically return a hex color from the palette for the given string.

    Usage in template:
        {{ staff.name|hashcolor }}

    This returns a simple hex color suitable for use in inline CSS backgrounds.
    """
    try:
        s = str(value) if value is not None else ""
        if not s:
            return _PALETTE[0]
        # Use md5 for deterministic distribution
        digest = hashlib.md5(s.encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16) % len(_PALETTE)
        return _PALETTE[idx]
    except Exception:
        return _PALETTE[0]

@register.filter
def mul(value, arg):
    """
    Multiply value by arg
    Usage: {{ value|mul:80 }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def div(value, arg):
    """
    Divide value by arg
    Usage: {{ value|div:60 }}
    """
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

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
