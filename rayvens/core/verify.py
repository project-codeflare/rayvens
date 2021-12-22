#
# Copyright IBM Corporation 2021
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import ray
import time
from rayvens.core import kamel


def verify_do(handle, _global_camel, action, *args, **kwargs):
    if action == 'verify_log':
        return _verify_log(handle, _global_camel, *args, **kwargs)
    raise RuntimeError('invalid meta action')


def wait_for_event(handle):
    event_count = 0
    countdown = 20
    while event_count == 0:
        event_count = ray.get(handle.event_count.remote())
        time.sleep(1)
        countdown -= 1
        if countdown == 0:
            break
    if event_count == 0:
        return False
    return True


def _verify_log(handle,
                _global_camel,
                sink_source_name,
                message,
                wait_for_events=False):
    log = "FAIL"

    # Wait for at least one event to happen.
    if wait_for_events:
        if not wait_for_event(handle):
            print("[LOG CHECK]:", "NO EVENTS RECEIVED")
            return False

    if _global_camel.mode.is_local():
        # In the local case the integration run is ongoing and we can
        # access the logs directly.
        outcome = ray.get(
            handle._integration_invoke.remote(sink_source_name, message))
    else:
        # When running using the operator then the integration run command
        # is non-blocking and returns immediately. The logs can be queried
        # using the kamel log command.
        integration_name = ray.get(
            handle._get_integration_name.remote(sink_source_name))
        invocation = kamel.log(_global_camel.mode, integration_name, message)
        outcome = invocation is not None
        invocation.kill()

    if outcome:
        log = "SUCCESS"
    print("[LOG CHECK]:", log)
    return outcome
