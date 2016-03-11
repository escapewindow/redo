# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
from __future__ import absolute_import, division, print_function

import asyncio
from functools import wraps
from contextlib import contextmanager
import logging
import random
log = logging.getLogger(__name__)


def calculate_sleep_time(attempt, sleeptime=10, max_sleeptime=300, sleepscale=1.5,
                         jitter=1):
    """
    A function that calculates exponential backoff and jitter.

    Args:
        attempt (int): the current attempt number, starting from 1.
        sleeptime (float): how many seconds to sleep between tries; defaults to
                           60s (one minute)
        max_sleeptime (float): the longest we'll sleep, in seconds; defaults to
                               300s (five minutes)
        sleepscale (float): how much to multiply the sleep time by each
                            iteration; defaults to 1.5
        jitter (int): random jitter to introduce to sleep time each iteration.
                      the amount is chosen at random between [-jitter, +jitter]
                      defaults to 1

    Returns:
        sleeptime (float): the lenght of time to sleep
    """
    if jitter:
        if jitter > sleeptime:
            # To prevent negative sleep times
            raise Exception('jitter ({}) must be less than sleep time ({})'.format(jitter, sleeptime))
        jitter = int(jitter * attempt * sleepscale)
        sleeptime = sleeptime + random.randint(-jitter, jitter)
    else:
        sleeptime = sleeptime

    if attempt > 1:
        exp = attempt - 1
        multiplier = sleepscale ** exp
        sleeptime = int(sleeptime * multiplier)

    if sleeptime > max_sleeptime:
        sleeptime = max_sleeptime

    return sleeptime


async def retry(action, attempts=5, sleeptime=60, max_sleeptime=5 * 60,
                sleepscale=1.5, jitter=1, retry_exceptions=(Exception,),
                cleanup=None, args=(), kwargs={}):
    """
    Calls an action function until it succeeds, or we give up.

    Args:
        action (callable): the function to retry
        attempts (int): maximum number of times to try; defaults to 5
        sleeptime (float): how many seconds to sleep between tries; defaults to
                           60s (one minute)
        max_sleeptime (float): the longest we'll sleep, in seconds; defaults to
                               300s (five minutes)
        sleepscale (float): how much to multiply the sleep time by each
                            iteration; defaults to 1.5
        jitter (int): random jitter to introduce to sleep time each iteration.
                      the amount is chosen at random between [-jitter, +jitter]
                      defaults to 1
        retry_exceptions (tuple): tuple of exceptions to be caught. If other
                                  exceptions are raised by action(), then these
                                  are immediately re-raised to the caller.
        cleanup (callable): optional; called if one of `retry_exceptions` is
                            caught. No arguments are passed to the cleanup
                            function; if your cleanup requires arguments,
                            consider using functools.partial or a lambda
                            function.
        args (tuple): positional arguments to call `action` with
        hwargs (dict): keyword arguments to call `action` with

    Returns:
        Whatever action(*args, **kwargs) returns

    Raises:
        Whatever action(*args, **kwargs) raises. `retry_exceptions` are caught
        up until the last attempt, in which case they are re-raised.

    Example:
        >>> import asyncio
        >>> count = 0
        >>> def foo():
        ...     global count
        ...     count += 1
        ...     print(count)
        ...     if count < 3:
        ...         raise ValueError("count is too small!")
        ...     return "success!"
        >>> loop = asyncio.get_event_loop()
        >>> loop.run_until_complete(retry(foo, sleeptime=0, jitter=0))
        1
        2
        3
        'success!'
    """
    assert callable(action)
    assert not cleanup or callable(cleanup)

    action_name = getattr(action, '__name__', action)
    if args or kwargs:
        log_attempt_format = ("retry: calling %s with args: %s,"
                              " kwargs: %s, attempt #%%d"
                              % (action_name, args, kwargs))
    else:
        log_attempt_format = ("retry: calling %s, attempt #%%d"
                              % action_name)

    if max_sleeptime < sleeptime:
        log.debug("max_sleeptime %d less than sleeptime %d" % (
            max_sleeptime, sleeptime))

    index = 1
    while index < attempts:
#    for _ in retrier(attempts=attempts, sleeptime=sleeptime,
#                     max_sleeptime=max_sleeptime, sleepscale=sleepscale,
#                     jitter=jitter):
        log.debug("attempt %i/%i", index, attempts)
        #print("attempt %i/%i" % (index, attempts))
        try:
            logfn = log.info if index != 1 else log.debug
            logfn(log_attempt_format, index)
            return action(*args, **kwargs)
        except retry_exceptions as exc:
            log.debug("retry: Caught exception: ", exc_info=True)
            #print("retry: Caught exception: " + str(exc))
            if cleanup:
                cleanup()
            if index == attempts:
                log.info("retry: Giving up on %s" % action_name)
                raise
            length = calculate_sleep_time(
                index,
                sleeptime=sleeptime,
                max_sleeptime=max_sleeptime,
                sleepscale=sleepscale,
                jitter=jitter
            )
            #print("retry: sleeping {}...".format(length))
            await asyncio.sleep(length)
        finally:
            index += 1


def retriable(*retry_args, **retry_kwargs):
    """
    A decorator factory for retry(). Wrap your function in @retriable(...) to
    give it retry powers!

    Arguments:
        Same as for `retry`, with the exception of `action`, `args`, and `kwargs`,
        which are left to the normal function definition.

    Returns:
        A function decorator

    Example:
        >>> count = 0
        >>> @retriable(sleeptime=0, jitter=0)
        ... def foo():
        ...     global count
        ...     count += 1
        ...     print(count)
        ...     if count < 3:
        ...         raise ValueError("count too small")
        ...     return "success!"
        >>> for i in foo:
        ...     print(i)
        1
        2
        3
        'success!'
    """
    def _retriable_factory(func):
        @wraps(func)
        def _retriable_wrapper(*args, **kwargs):
            return retry(func, args=args, kwargs=kwargs, *retry_args,
                         **retry_kwargs)
        return _retriable_wrapper
    return _retriable_factory


@contextmanager
def retrying(func, *retry_args, **retry_kwargs):
    """
    A context manager for wrapping functions with retry functionality.

    Arguments:
        func (callable): the function to wrap
        other arguments as per `retry`

    Returns:
        A context manager that returns retriable(func) on __enter__

    Example:
        >>> count = 0
        >>> def foo():
        ...     global count
        ...     count += 1
        ...     print(count)
        ...     if count < 3:
        ...         raise ValueError("count too small")
        ...     return "success!"
        >>> with retrying(foo, sleeptime=0, jitter=0) as f:
        ...     f()
        1
        2
        3
        'success!'
    """
    yield retriable(*retry_args, **retry_kwargs)(func)
