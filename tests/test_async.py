# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

import asyncio
import mock
import unittest
import time

from redo.async import retry, calculate_sleep_time

ATTEMPT_N = 1

def bar():
    yield "bar"

def foo():
    yield from bar()


def _succeedOnSecondAttempt(foo=None, exception=Exception):
    global ATTEMPT_N
    if ATTEMPT_N == 2:
        ATTEMPT_N += 1
        return
    ATTEMPT_N += 1
    raise exception("Fail")


def _alwaysPass():
    global ATTEMPT_N
    ATTEMPT_N += 1
    return True


def _mirrorArgs(*args, **kwargs):
    return args, kwargs


def _alwaysFail():
    raise Exception("Fail")


class NewError(Exception):
    pass


class OtherError(Exception):
    pass


def _raiseCustomException():
    return _succeedOnSecondAttempt(exception=NewError)


class TestAsync(unittest.TestCase):
    def setUp(self):
        global ATTEMPT_N
        ATTEMPT_N = 1
        self.sleep_patcher = mock.patch('asyncio.sleep')
        self.sleep_patcher.start()

    def tearDown(self):
        self.sleep_patcher.stop()

    def testRetrySucceed(self):
        # Will raise if anything goes wrong
        retry(_succeedOnSecondAttempt, attempts=2, sleeptime=0, jitter=0)

    def testRetryFailWithoutCatching(self):
        self.assertRaises(Exception, retry, _alwaysFail, sleeptime=0, jitter=0,
                          exceptions=())

    def testRetryFailEnsureRaisesLastException(self):
        self.assertRaises(Exception, retry, _alwaysFail, sleeptime=0, jitter=0)

    def testRetrySelectiveExceptionSucceed(self):
        retry(_raiseCustomException, attempts=2, sleeptime=0, jitter=0,
              retry_exceptions=(NewError,))

    def testRetrySelectiveExceptionFail(self):
        self.assertRaises(NewError, retry, _raiseCustomException, attempts=2,
                          sleeptime=0, jitter=0, retry_exceptions=(OtherError,))

    def testRetryWithSleep(self):
        retry(_succeedOnSecondAttempt, attempts=2, sleeptime=1)

    def testRetryOnlyRunOnce(self):
        """Tests that retry() doesn't call the action again after success"""
        global ATTEMPT_N
        retry(_alwaysPass, attempts=3, sleeptime=0, jitter=0)
        # ATTEMPT_N gets increased regardless of pass/fail
        self.assertEquals(2, ATTEMPT_N)

    def testRetryReturns(self):
        loop = asyncio.get_event_loop()
        ret = loop.run_until_complete(retry(_alwaysPass, sleeptime=0, jitter=0))
        loop.close()
        self.assertEquals(ret, True)

    def testRetryCleanupIsCalled(self):
        cleanup = mock.Mock()
        retry(_succeedOnSecondAttempt, cleanup=cleanup, sleeptime=0, jitter=0)
        self.assertEquals(cleanup.call_count, 1)

    def testRetryArgsPassed(self):
        args = (1, 'two', 3)
        kwargs = dict(foo='a', bar=7)
        ret = retry(_mirrorArgs, args=args, kwargs=kwargs.copy(), sleeptime=0, jitter=0)
        self.assertEqual(ret[0], args)
        self.assertEqual(ret[1], kwargs)

    def test_sleeptime(self):
        """Make sure retrier sleep is behaving"""
        expected = [None, 10, 20, 40, 80]
        for attempt in range(1, 5):
            self.assertEqual(
                expected[attempt],
                calculate_sleep_time(attempt, sleeptime=10, max_sleeptime=300,
                                     sleepscale=2, jitter=0)
            )

    def test_sleeptime_no_jitter(self):
        """Make sure retrier sleep is behaving"""
        expected = [None, 10, 20, 40, 80]
        for attempt in range(1, 5):
            self.assertEqual(
                expected[attempt],
                calculate_sleep_time(attempt, sleeptime=10, max_sleeptime=300,
                                     sleepscale=2, jitter=None)
            )

    def test_sleeptime_maxsleep(self):
        expected = [None, 10, 20, 30, 30]
        for attempt in range(1, 5):
            self.assertEqual(
                expected[attempt],
                calculate_sleep_time(attempt, sleeptime=10, max_sleeptime=30,
                                     sleepscale=2, jitter=0)
            )

    def test_jitter_bounds(self):
        self.assertRaises(Exception, calculate_sleep_time(1, sleeptime=1, jitter=2))

    def test_sleeptime_jitter(self):
        # Test that jitter works
        with mock.patch("random.randint") as randint:
            randint.return_value = -3
            expected = [None, 7, 23, 37, 83]
            for attempt in range(1, 5):
                self.assertEqual(
                    expected[attempt],
                    calculate_sleep_time(attempt, sleeptime=10, max_sleeptime=300,
                                         sleepscale=2, jitter=3)
                )
                randint.return_value *= -1
            self.assertEquals(randint.call_args, mock.call(-48, 48))
