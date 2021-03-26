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
from rayvens.core.mode import mode
from rayvens.core.name import name_integration, name_sink


def verify_log(stream, config, message):
    integration_name = name_integration(stream.name, name_sink(config))
    invocation = kamel.log(mode, integration_name, message)
    log = "FAIL"
    if invocation is not None:
        log = "SUCCESS"
        invocation.kill()
    print("[LOG CHECK]:", log)
