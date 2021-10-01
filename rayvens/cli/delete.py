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


def delete_deployment(args):
    if args.deployment is None:
        raise RuntimeError("No deployment name provided.")

    namespace = "default"
    if args.namespace is not None:
        namespace = args.namespace

    # Delete kubernetes deployment for integration.
    from kubernetes import client, config
    config.load_kube_config()
    k8s_client = client.AppsV1Api(client.ApiClient())
    k8s_client.delete_namespaced_deployment(args.deployment, namespace)
