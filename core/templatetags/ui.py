from django import template

register = template.Library()


def initials(user) -> str:
    parts = [user.first_name, user.last_name]
    letters = ''.join(part[0] for part in parts if part)
    return (letters or user.get_username()[:1]).upper()


def nav_active(context, *view_names) -> str:
    match = context['request'].resolver_match
    if match and match.view_name in view_names:
        return 'is-active'
    return ''


register.filter('initials', initials)
register.simple_tag(nav_active, takes_context=True)
