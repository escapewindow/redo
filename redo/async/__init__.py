import sys

if sys.version_info >= (3, 4):
    from redo.async.source import retry, calculate_sleep_time

__all__ = ['retry', 'calculate_sleep_time']
