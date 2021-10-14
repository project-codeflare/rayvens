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

from rayvens.cli import utils


def delete(args):
    if args.name is not None:
        delete_deployment(args)

    if args.all_jobs is not None:
        delete_all_jobs(args)


def delete_all_jobs(args):
    namespace = "default"
    if args.namespace is not None:
        namespace = args.namespace

    prefix = args.all_jobs

    # Delete the jobs that start with the provided string.
    from kubernetes import client, config
    config.load_kube_config()
    k8s_client = client.BatchV1Api(client.ApiClient())

    exception_occured = False
    try:
        api_response = k8s_client.list_namespaced_job(namespace)
        body = client.V1DeleteOptions(propagation_policy='Background')
        for job in api_response.items:
            if job.metadata.name.startswith(prefix):
                k8s_client.delete_namespaced_job(job.metadata.name,
                                                 namespace,
                                                 body=body)
    except client.exceptions.ApiException:
        exception_occured = True

    # Delete the jobs that start with the provided string.
    k8s_client = client.CoreV1Api(client.ApiClient())

    if not exception_occured:
        print(f"Successfully deleted jobs starting with {prefix} from "
              f"{namespace} namespace.")


def delete_deployment(args, with_job_launcher_priviledges=True):
    if args.name is None:
        raise RuntimeError("No integration name provided.")

    namespace = "default"
    if args.namespace is not None:
        namespace = args.namespace

    # Delete kubernetes deployment for integration.
    from kubernetes import client, config
    config.load_kube_config()
    k8s_client = client.AppsV1Api(client.ApiClient())

    # Delete the integration deployment.
    deployment_name = utils.get_kubernetes_integration_name(args.name)

    exception_occured = False
    try:
        k8s_client.delete_namespaced_deployment(deployment_name, namespace)
    except client.exceptions.ApiException:
        exception_occured = True

    # Delete the entrypoint service.
    k8s_client = client.CoreV1Api(client.ApiClient())
    entrypoint_service = utils.get_kubernetes_entrypoint_name(args.name)

    try:
        k8s_client.delete_namespaced_service(entrypoint_service, namespace)
    except client.exceptions.ApiException:
        exception_occured = True

    if with_job_launcher_priviledges:
        # Delete service account:
        # job-launcher-service-account
        name = utils.job_launcher_service_account
        try:
            k8s_client.delete_namespaced_service_account(name, namespace)
        except client.exceptions.ApiException:
            exception_occured = True

        api_instance = client.RbacAuthorizationV1Api(client.ApiClient())

        # Delete cluster role binding:
        # job-launcher-service-account
        name = utils.job_launcher_cluster_role_binding
        try:
            api_instance.delete_cluster_role_binding(
                name, body=client.V1DeleteOptions())
        except client.exceptions.ApiException:
            exception_occured = True

        # Delete cluster role:
        # job-manager-role
        name = utils.job_manager_role
        try:
            api_instance.delete_cluster_role(name,
                                             body=client.V1DeleteOptions())
        except client.exceptions.ApiException:
            exception_occured = True

    try:
        k8s_client.delete_namespaced_service(entrypoint_service, namespace)
    except client.exceptions.ApiException:
        exception_occured = True

    if not exception_occured:
        print(f"Successfully deleted {deployment_name} from {namespace} "
              "namespace")
    else:
        print("Successfully deleted the remaining components of "
              f"{deployment_name} from {namespace} namespace")
