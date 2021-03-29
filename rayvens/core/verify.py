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

from rayvens.core import kamel
from rayvens.core.name import name_integration


def verify_do(stream, _global_camel, action, *args, **kwargs):
    if action == 'verify_log':
        return _verify_log(stream, _global_camel, *args, **kwargs)
    raise RuntimeError('invalid meta action')


def _verify_log(stream, _global_camel, sink_source_name, message):
    integration_name = name_integration(stream.name, sink_source_name)

    # Check if source/sink exists.
    if sink_source_name not in stream._sinks and \
       sink_source_name not in stream._sources:
        raise RuntimeError(
            f'{sink_source_name} not found on stream {stream.name}')

    if _global_camel.mode.isLocal():
        # In the local case the integration run is ongoing and we can
        # access the logs directly.
        # TODO: for not this only works for the operator local implementation,
        # need to keep track of invocations in other implementations.
        invocation = _global_camel.invocations[integration_name]
        outcome = invocation.ongoing_command(message)
    else:
        # When running using the operator then the integration run command
        # is non-blocking and returns immediately. The logs can be queried
        # using the kamel log command.
        invocation = kamel.log(_global_camel.mode, integration_name, message)
        outcome = invocation is not None
        invocation.kill()

    log = "FAIL"
    if outcome:
        log = "SUCCESS"
    print("[LOG CHECK]:", log)
    return outcome
