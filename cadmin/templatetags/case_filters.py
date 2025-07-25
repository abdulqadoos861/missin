from django import template

register = template.Library()

@register.filter(name='status_badge_class')
def status_badge_class(status):
    """
    Returns the appropriate CSS class for a status badge.
    """
    status_classes = {
        'pending': 'bg-warning text-dark',
        'investigation': 'bg-info text-white',
        'found': 'bg-success text-white',
        'closed': 'bg-secondary text-white',
    }
    return status_classes.get(status.lower(), 'bg-light text-dark')

@register.filter(name='status_icon')
def status_icon(status):
    """
    Returns the appropriate icon for a status.
    """
    status_icons = {
        'pending': 'clock',
        'investigation': 'search',
        'found': 'check-circle',
        'closed': 'archive',
    }
    return status_icons.get(status.lower(), 'circle')

@register.filter(name='status_text')
def status_text(status):
    """
    Returns the display text for a status.
    """
    status_texts = {
        'pending': 'Pending',
        'investigation': 'Under Investigation',
        'found': 'Found',
        'closed': 'Closed',
    }
    return status_texts.get(status.lower(), status.title())
