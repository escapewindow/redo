# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
from __future__ import absolute_import, division, print_function

import aiowrap
import asyncio
import time

import redo

_time_sleep = time.sleep
time.sleep = aiowrap.wrap_async(asyncio.sleep)
_patched_time_sleep = time.sleep
retrier = aiowrap.wrap_sync(redo.retrier)
retry = aiowrap.wrap_sync(redo.retry)
retrying = aiowrap.wrap_sync(redo.retrying)
retriable = aiowrap.wrap_sync(redo.retriable)

__all__ = ['retrier', 'retry', 'retrying', 'retriable']
