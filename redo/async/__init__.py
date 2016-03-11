import sys

if sys.version_info >= (3, 4):
    from redo.async.source import Retry, calculate_sleep_time

__all__ = ['Retry', 'calculate_sleep_time']
