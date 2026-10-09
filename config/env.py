import datetime
import os

_TRUE_VALUES = frozenset({'1', 'true', 'yes', 'on'})
_FALSE_VALUES = frozenset({'0', 'false', 'no', 'off', ''})


class ImproperlyConfiguredEnvError(RuntimeError):
    pass


def _raw(name: str, default: str | None) -> str:
    value = os.environ.get(name)
    if value is None:
        if default is None:
            raise ImproperlyConfiguredEnvError(
                f'Environment variable {name} is required.'
            )
        return default
    return value.strip()


def get_str(name: str, default: str | None = None) -> str:
    return _raw(name, default)


def get_bool(name: str, default: bool = False) -> bool:
    value = _raw(name, '1' if default else '0').lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    raise ImproperlyConfiguredEnvError(f'{name} must be a boolean: {value!r}.')


def get_int(name: str, default: int | None = None) -> int:
    value = _raw(name, None if default is None else str(default))
    try:
        return int(value)
    except ValueError as e:
        raise ImproperlyConfiguredEnvError(
            f'{name} must be an integer: {value!r}.'
        ) from e


def get_list(name: str, default: str = '') -> list[str]:
    items = (item.strip() for item in _raw(name, default).split(','))
    return [item for item in items if item]


def get_date(name: str, default: str | None = None) -> datetime.date:
    value = _raw(name, default)
    try:
        return datetime.date.fromisoformat(value)
    except ValueError as e:
        raise ImproperlyConfiguredEnvError(
            f'{name} must be a date in YYYY-MM-DD format: {value!r}.'
        ) from e
