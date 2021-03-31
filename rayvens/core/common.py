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
import requests
from rayvens.core import kamel
from rayvens.core import kubernetes
from rayvens.core.mode import mode, RayvensMode


def get_run_mode(camel_mode):
    if camel_mode == 'local.local':
        mode.run_mode = RayvensMode.LOCAL
    elif camel_mode == 'mixed.operator':
        mode.run_mode = RayvensMode.MIXED_OPERATOR
    elif camel_mode == 'operator':
        mode.run_mode = RayvensMode.CLUSTER_OPERATOR
    else:
        raise RuntimeError("Unsupported camel mode.")
    return mode


@ray.remote(num_cpus=0)
class Helper:
    def __init__(self, url):
        self.url = url

    def append(self, data):
        if data is not None:
            requests.post(self.url, data)


# Wait for an integration to reach its running state and not only that but
# also be in a state where it can immediately execute incoming requests.
def await_start(mode, integration_name):
    # TODO: remove this once we enable this for local mode.
    if mode.isLocal():
        return True

    # Wait for pod to start.
    pod_is_running, pod_name = kubernetes.getPodRunningStatus(
        mode, integration_name)
    if pod_is_running:
        print(f'Pod {pod_name} is running.')
    else:
        print('Pod did not run correctly.')
        return False

    # Wait for integration to be installed. Since we now know that the pod
    # is running we can use that to check that the integration is installed
    # correctly.
    integration_is_running = kubernetes.getIntegrationStatus(mode, pod_name)
    if integration_is_running:
        print(f'Integration {integration_name} is running.')
    else:
        print('Integration did not start correctly.')

    return integration_is_running


# Function which disconnects an integration whether it is an integration
# created using the kamel operator and `kamel run` or an integration created
# using `kamel local run`.
def disconnect_integration(mode, integration, kamel_operator=False):
    if kamel_operator:
        # If kamel is running the cluster then use kamel delete to
        # terminate the integration. First we terminate any services
        # associated with the integration.
        if integration.service is not None:
            if not kubernetes.deleteService(mode, integration.service):
                raise RuntimeError(
                    f'Service with name {integration.service} for'
                    '{integration.integration_name} could not be'
                    'terminated')

        # Terminate the integration itself.
        if not kamel.delete(integration.invocation,
                            integration.integration_name):
            raise RuntimeError(
                f'Failed to terminate {integration.integration_name}')
        return

    # If no kamel operator is used the only other alternative is that the
    # integration is running locally. In that case we only need to kill the
    # process that runs it.
    integration.invocation.kill()


# If running in mixed mode, i.e. Ray locally and kamel in the cluster, then we
# have to also start a service the allows outside processes to send data to
# the sink.
def create_externalizing_service(mode, integration):
    service_name = get_service_name(integration.integration_name)
    print("service_name = ", service_name)
    kubernetes.createExternalServiceForKamel(mode, service_name,
                                             integration.integration_name)
    return service_name


# Automatic name of a service.
def get_service_name(integration_name):
    return "-".join(["service", integration_name])
