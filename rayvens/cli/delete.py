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
import rayvens.cli.kubernetes as kube
import rayvens.cli.docker as docker


def delete(args):
    # Set verbosity:
    utils.verbose = args.verbose

    if args.deployed:
        if args.name is not None:
            delete_deployment(args)
    else:
        if args.name is not None:
            delete_local_deployment(args)

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

    exception_occurred = False
    try:
        api_response = k8s_client.list_namespaced_job(namespace)
        body = client.V1DeleteOptions(propagation_policy='Background')
        for job in api_response.items:
            if job.metadata.name.startswith(prefix):
                k8s_client.delete_namespaced_job(job.metadata.name,
                                                 namespace,
                                                 body=body)
    except client.exceptions.ApiException:
        exception_occurred = True

    # Delete the jobs that start with the provided string.
    k8s_client = client.CoreV1Api(client.ApiClient())

    if not exception_occurred:
        print(f"Successfully deleted jobs starting with {prefix} from "
              f"{namespace} namespace.")


def delete_deployment(args, with_job_launcher_privileges=True):
    if args.name is None:
        raise RuntimeError("No integration name provided.")

    namespace = "default"
    if args.namespace is not None:
        namespace = args.namespace

    # Delete kubernetes deployment for integration.
    from kubernetes import client, config
    config.load_kube_config()
    k8s_client = client.ApiClient()

    # Delete the integration deployment.
    deployment_name = utils.get_kubernetes_integration_name(args.name)
    deployment = kube.Deployment(deployment_name, namespace=namespace)
    deployment.delete(k8s_client, starting_with=deployment_name)

    # Delete the entrypoint service.
    entrypoint_service_name = utils.get_kubernetes_entrypoint_name(args.name)
    service = kube.Service(entrypoint_service_name, namespace=namespace)
    service.delete(k8s_client, starting_with=entrypoint_service_name)

    # Delete configMap for updating the integration file.
    config_map = kube.ConfigMap(namespace=namespace)
    config_map.delete(k8s_client, kube.volume_base_name)

    if with_job_launcher_privileges:
        # Delete service account:
        # job-launcher-service-account
        name = utils.job_launcher_service_account
        service_account = kube.ServiceAccount(name, namespace=namespace)
        service_account.delete(k8s_client)

        # Delete cluster role binding:
        # job-launcher-service-account
        name = utils.job_launcher_cluster_role_binding
        cluster_role_binding = kube.ClusterRoleBinding(name, [], None)
        cluster_role_binding.delete(k8s_client)

        # Delete cluster role:
        # job-manager-role
        name = utils.job_manager_role
        cluster_role_binding = kube.ClusterRole(name, namespace=namespace)
        cluster_role_binding.delete(k8s_client)


def delete_local_deployment(args):
    if args.name is None:
        raise RuntimeError("No integration name provided.")

    containers = docker.docker_container_ls()

    for container_name in containers:
        if container_name.startswith(args.name):
            docker.docker_kill(containers[container_name])
            docker.docker_rm(containers[container_name])
