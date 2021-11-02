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

import yaml
import subprocess
import pathlib
import rayvens.cli.file as file
import rayvens.cli.docker as docker
import rayvens.cli.utils as utils

all_verbs = ["get", "list", "watch", "create", "update", "patch", "delete"]
api_groups = {'jobs': ["batch", "extensions"]}
volume_base_name = "rayvens-volume"
kubernetes_tag = "kubectl"


def get_deployment_yaml(name, namespace, image_name, registry, args,
                        with_job_launcher, integration_config_map):
    # Kubernetes deployment options:
    replicas = 1
    full_image_name = image_name
    if registry is not None:
        full_image_name = "/".join([registry, image_name])

    integration_name = utils.get_kubernetes_integration_name(name)
    entrypoint_name = utils.get_kubernetes_entrypoint_name(name)
    label_name = utils.get_kubernetes_label_name(name)

    # TODO: these deployment options work with a local Kubernetes cluster
    # with a local registry i.e. localhost:5000. Test with actual cluster.

    container = Container(image_name,
                          full_image_name,
                          image_pull_policy="Always")

    # Update integration file from host file.
    container.update_integration(integration_config_map)

    combined_configuration = []

    if with_job_launcher:
        # Service account for the job lunch permissions:
        service_account = ServiceAccount(utils.job_launcher_service_account,
                                         namespace)
        combined_configuration.append(service_account.configuration())

        # Create the cluster role specifying the resource type and the
        # allowable actions (verbs). By default all verbs are enabled if
        # none are specified.
        cluster_role = ClusterRole(utils.job_manager_role, namespace)
        cluster_role.add_rule("jobs")
        combined_configuration.append(cluster_role.configuration())

        # Create a cluster role binding between the service account and
        # the cluster role defined above.
        cluster_role_binding = ClusterRoleBinding(
            utils.job_launcher_cluster_role_binding, [service_account],
            cluster_role)
        combined_configuration.append(cluster_role_binding.configuration())

    # Assemble the pod that the deployment will be managing.
    managed_pod = Pod("managed_pod", namespace)

    # Ensure the pod has the ability to launch jobs by addint the service
    # account created above.
    if with_job_launcher:
        managed_pod.add_service_account(service_account)
    managed_pod.add_container(container)
    managed_pod.add_label("integration", label_name)

    # Create the deployment.
    deployment = Deployment(integration_name,
                            managed_pod,
                            namespace=namespace,
                            replicas=replicas)

    # Create a NodePort service to enable outside communication.
    node_port_spec = NodePortSpec()
    node_port_spec.add_selector("integration", label_name)
    node_port_spec.add_port(3000, 30001)
    service = Service(entrypoint_name, node_port_spec, namespace=namespace)
    # Add the service to the deployment.
    deployment.add_service(service)

    combined_configuration.append(deployment.configuration())

    # print("\n---\n".join(combined_configuration))
    return "\n---\n".join(combined_configuration)


def kubectl_create_configmap(name, namespace, embedded_file_path):
    command = ["kubectl", "create", "configmap", name]

    # Set the namespace:
    if namespace is not None:
        command.append("-n")
        command.append(namespace)

    # From file:
    command.append("--from-file")
    command.append(embedded_file_path)

    # Wait for kubectl command to finish before returning:
    outcome = subprocess.run(command)

    if outcome.returncode == 0:
        utils.PRINT(f"configmap object {name} created successfully.",
                    tag=kubernetes_tag)
    else:
        utils.PRINT(f"configmap object {name} creation failed.",
                    tag=kubernetes_tag)


def kubectl_get_yaml(entity_type, name, namespace):
    command = ["kubectl", "get", entity_type, name]

    # Namespace.
    if namespace is not None:
        command.append("-n")
        command.append(namespace)

    # From file:
    command.append("-o")
    command.append("yaml")

    # Wait for kubectl command to finish before returning:
    outcome = subprocess.run(command)
    if outcome.returncode == 0:
        utils.PRINT("Kubernetes get ended successfully.", tag=kubernetes_tag)
    else:
        utils.PRINT("Kubernetes get failed.", tag=kubernetes_tag)


class KubeEntity:
    def __init__(self, name, namespace=None, application=None):
        # Name of the Kubernetes entity, the name will be stored
        # as a piece of metadata information.
        self.name = name

        # The namespace in which the kubernetes entity will be launched.
        self.namespace = namespace
        self._metadata = {}
        self._metadata["name"] = name
        if namespace is not None:
            self._metadata["namespace"] = namespace
        self._labels = {}
        if application is not None:
            self._labels["app"] = application
        self.template = None

    def add_label(self, name, value):
        self._labels[name] = value

    def add_metadata(self, entry_name, entry_value):
        self._metadata[entry_name] = entry_value

    def app(self, application_name):
        self._labels["app"] = application_name

    def configuration(self):
        return yaml.dump(self._specification())

    def file(self):
        return file.File(self.name + ".yaml", contents=self.configuration())

    def _specification(self):
        raise RuntimeError("KubeEntity objects do not have a specification.")

    def create(self, k8s_client):
        import kubernetes.utils as kube_utils
        try:
            kube_utils.create_from_dict(k8s_client, self._specification())
        except kube_utils.FailToCreateError as creation_error:
            utils.PRINT(f"Failed to create kubernetes entity {creation_error}",
                        tag=kubernetes_tag)

    def _delete(self, api_method):
        namespace = self.namespace
        if self.namespace is None:
            namespace = "default"
        from kubernetes.client.rest import ApiException
        try:
            api_method(self.name, namespace)
        except ApiException as deletion_error:
            utils.PRINT(f"Failed to delete kubernetes entity {deletion_error}",
                        tag=kubernetes_tag)
        else:
            utils.PRINT(f"Kubernetes entity {self.name} deleted successfully",
                        tag=kubernetes_tag)

    def _exists(self, api_method):
        namespace = self.namespace
        if self.namespace is None:
            namespace = "default"
        from kubernetes.client.rest import ApiException
        try:
            api_response = api_method(namespace)
        except ApiException as check_error:
            utils.PRINT(
                f"Exception when fetching kubernetes entities {check_error}",
                tag=kubernetes_tag)
        return api_response


# apiVersion: v1
# kind: ConfigMap
# metadata:
#   creationTimestamp: 2017-12-27T18:36:28Z
#   name: game-config-env-file
#   namespace: default
#   resourceVersion: "809965"
#   uid: d9d1ca5b-eb34-11e7-887b-42010a8002b8
# data:
#   filename.ext: |+
# <file_contents>


class ConfigMap(KubeEntity):
    def __init__(self, embedded_file):
        KubeEntity.__init__(self, "config-map")
        self.api_version = "v1"
        self.kind = "ConfigMap"
        if file is not None and not isinstance(embedded_file, file.File):
            raise RuntimeError("Input file must be of File type.")
        self.embedded_file = embedded_file

    def _specification(self):
        raise RuntimeError("Not implemented yet for this kubernetes entity.")

    def create(self):
        self.embedded_file.emit()
        utils.PRINT(f"Create {self.name} in namespace {self.namespace}.",
                    tag=kubernetes_tag)
        kubectl_create_configmap(self.name, self.namespace,
                                 self.embedded_file.full_path)
        # kubectl_get_yaml("configmap", self.name, self.namespace)
        self.embedded_file.delete()

    def delete(self, k8s_client):
        from kubernetes import client
        api_instance = client.CoreV1Api(k8s_client)
        self._delete(api_instance.delete_namespaced_config_map)


#  apiVersion: v1
#  kind: Pod
#  metadata:
#    name: rss-site
#    labels:
#      app: web
#  spec:
#    containers:
#      - name: front-end
#        image: nginx
#        ports:
#          - containerPort: 80
#      - name: rss-reader
#        image: nickchase/rss-php-nginx:v1
#        ports:
#          - containerPort: 88

#   containers:
#   - image: k8s.gcr.io/test-webserver
#     name: test-container
#     volumeMounts:
#     - mountPath: /test-pd
#       name: test-volume
#   volumes:
#   - name: test-volume
#     hostPath:
#       # directory location on host
#       path: /data


class Volume:
    def __init__(self, name, namespace=None):
        self.name = name
        self.namespace = namespace
        self.kind = None
        self.host_file_path = None
        self.mount_file_path = None

    def _update_integration_file(self, integration_config_map):
        self.kind = "configMap"
        self.host_file_path = integration_config_map.embedded_file.full_path
        self.mount_file_path = docker.get_file_on_image(
            self.host_file_path.name)
        if isinstance(self.mount_file_path, str):
            self.mount_file_path = pathlib.Path(self.mount_file_path)
        # The configMap object inherits the name and namespace of the volume
        # it is included in. TODO: make it such that the volume inherits the
        # the name and namespace from the configMap.
        integration_config_map.name = self.name
        integration_config_map.namespace = self.namespace

    def _volume_specification(self):
        spec = {'name': self.name}
        volume_spec = {}
        if self.kind == "hostPath":
            volume_spec['path'] = str(self.host_file_path)
        if self.kind == "configMap":
            volume_spec['name'] = self.name
            item_spec = {
                'key': str(self.host_file_path.name),
                'path': str(self.host_file_path.name)
            }
            volume_spec['items'] = [item_spec]
        spec[self.kind] = volume_spec
        return spec

    def _volume_mount_specification(self):
        spec = {'name': self.name}
        if self.kind == "hostPath" or self.kind == "configMap":
            spec['mountPath'] = str(self.mount_file_path)
            if self.mount_file_path is not None:
                spec['subPath'] = str(self.mount_file_path.name)
        return spec

    def delete(self):
        self.config_map.delete()


class Container:
    def __init__(self, name, image, image_pull_policy=None):
        self.name = name
        self.image = image
        self.image_pull_policy = image_pull_policy
        self.command = None
        self._envvars = []
        self._ports = []
        self._volumes = []
        self._volume_mounted_count = 0

    def add_port(self, port_name, value):
        self._ports.append({port_name: value})

    def add_envvar(self, env_var_name, value):
        self._envvars.append({"name": env_var_name, "value": value})

    def update_integration(self, integration_config_map):
        volume = Volume(volume_base_name + "-" +
                        str(self._volume_mounted_count))
        volume._update_integration_file(integration_config_map)
        self._volumes.append(volume)
        self._volume_mounted_count += 1

    def _specification(self):
        spec = {'name': self.name, 'image': self.image}

        if len(self._ports) > 0:
            spec['ports'] = self._ports

        if len(self._envvars) > 0:
            spec['env'] = self._envvars

        if self.command is not None:
            spec['command'] = self.command

        if self.image_pull_policy is not None:
            spec['imagePullPolicy'] = self.image_pull_policy

        if len(self._volumes) > 0:
            volume_mounts_spec = []
            for volume in self._volumes:
                volume_mounts_spec.append(volume._volume_mount_specification())
            spec['volumeMounts'] = volume_mounts_spec

        return spec

    def _volumes_specifications(self):
        volume_specs = []
        for volume in self._volumes:
            volume_specs.append(volume._volume_specification())
        return volume_specs


class Pod(KubeEntity):
    def __init__(self, name, namespace=None):
        KubeEntity.__init__(self, name, namespace=namespace)
        self.api_version = "v1"
        self.kind = "Pod"
        self.containers = []
        self._service_account = None

    def add_container(self, container):
        self.containers.append(container)

    def add_service_account(self, service_account):
        self._service_account = service_account
        # TODO: when this Pod is launched, make sure that
        # the service account and the roles/bindings using
        # that service account are up and running as well.

    def _pod_specification(self):
        metadata = {'name': self.name}
        if self.namespace is not None:
            metadata['namespace'] = self.namespace

        if len(self._labels) > 0:
            metadata['labels'] = self._labels

        container_specs = []
        volume_specs = []
        for container in self.containers:
            if not isinstance(container, Container):
                raise RuntimeError("Invalid container used in pod.")
            container_specs.append(container._specification())
            volume_specs.extend(container._volumes_specifications())

        pod_spec = {}
        if self._service_account is not None:
            if not isinstance(self._service_account, ServiceAccount):
                raise RuntimeError(
                    "Invalid service account type, use ServiceAccount.")
            pod_spec['serviceAccountName'] = self._service_account.name
        pod_spec['containers'] = container_specs

        if len(volume_specs) > 0:
            pod_spec['volumes'] = volume_specs

        spec = {'metadata': metadata, 'spec': pod_spec}
        return spec

    def _specification(self):
        spec = {'apiVersion': self.api_version, 'kind': self.kind}
        spec.update(self._pod_specification())
        return spec


#           "apiVersion: batch/v1" + newLine
#         + "kind: Job" + newLine
#         + "metadata:" + newLine
#         + "  name: "+ jobName + newLine
#         + "spec:" + newLine
#         + "  template:" + newLine
#         + "    spec:" + newLine
#         + "      containers:" + newLine
#         + "      - name: " + jobName + "-container" + newLine
#         + "        image: adoptopenjdk/openjdk11:alpine" + newLine
#         + "        env:" + newLine
#         + "        - name: TEST_EVENT" + newLine
#         + "          value: \\\"" + eventContents + "\\\"" + newLine
#         + "        command: {job_command}" + newLine
#         + "      restartPolicy: Never" + newLine
#         + "  backoffLimit: 4" + newLine;


class Job(KubeEntity):
    def __init__(self, name, namespace=None):
        KubeEntity.__init__(self, name, namespace=namespace)
        self.api_version = "batch/v1"
        self.kind = "Job"
        self.containers = []
        self.restart_policy = "Never"
        self.backoff_limit = 4

    def add_container(self, container):
        self.containers.append(container)

    def _specification(self):
        metadata = {'name': self.name}
        if self.namespace is not None:
            metadata['namespace'] = self.namespace

        container_specs = []
        for container in self.containers:
            if not isinstance(container, Container):
                raise RuntimeError("Invalid container used in pod.")
            container_specs.append(container._specification())

        spec = {
            'apiVersion': self.api_version,
            'kind': self.kind,
            'metadata': metadata,
            'spec': {
                'template': {
                    'spec': {
                        'containers': container_specs
                    },
                    'restartPolicy': self.restart_policy
                },
                'backoffLimit': self.backoff_limit
            }
        }
        return spec


# apiVersion: v1
# kind: ServiceAccount
# metadata:
#   name: {job_launcher_service_account}
#   namespace: {namespace}


class ServiceAccount(KubeEntity):
    def __init__(self, name, namespace=None):
        KubeEntity.__init__(self, name, namespace=namespace)
        self.api_version = "v1"
        self.kind = "ServiceAccount"

    def _specification(self):
        metadata = {'name': self.name}
        if self.namespace is not None:
            metadata['namespace'] = self.namespace
        spec = {
            'apiVersion': self.api_version,
            'kind': self.kind,
            'metadata': metadata
        }
        return spec

    def exists(self, k8s_client):
        from kubernetes import client
        api_instance = client.CoreV1Api(k8s_client)
        service_account_list = KubeEntity._exists(
            self, api_instance.list_namespaced_service_account)
        for item in service_account_list.items:
            if item.metadata.name == self.name:
                return True
        return False

    def delete(self, k8s_client):
        self._delete(k8s_client.delete_namespaced_service_account)


# apiVersion: rbac.authorization.k8s.io/v1
# kind: ClusterRole
# metadata:
#   namespace: {namespace}
#   name: {job_manager_role}
# rules:
# - apiGroups: ["batch", "extensions"]
#   resources: ["jobs", "jobs/status", "jobs/exec", "jobs/log"]
#   verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]


class ClusterRoleRule:
    def __init__(self, resources, verbs):
        self.resources = resources
        self.verbs = verbs
        if len(verbs) == 0:
            self.verbs = all_verbs
        else:
            self._check_verbs()
        self.api_groups = []
        self._update_api_group()

    def add_resource(self, resource):
        self.resources.append(resource)
        self._update_api_group()

    def add_verb(self, verb):
        if verb is all_verbs and verb not in self.verbs:
            self.verbs.append(verb)

    def _update_api_group(self):
        for resource in self.resources:
            for api_group in api_groups[resource]:
                if api_group not in self.api_groups:
                    self.api_groups.append(api_group)

    def _check_verbs(self):
        for verb in self.verbs:
            if verb not in all_verbs:
                raise RuntimeError(f"Invalid verb {verb}.")


class ClusterRole(KubeEntity):
    def __init__(self, name, namespace=None):
        KubeEntity.__init__(self, name, namespace=namespace)
        self.api_version = "rbac.authorization.k8s.io/v1"
        self.kind = "ClusterRole"
        self.rules = []

    def add_rule(self, resources, verbs=[]):
        resources_list = resources
        if not isinstance(resources, list):
            resources_list = [resources]
        self.rules.append(ClusterRoleRule(resources_list, verbs))

    def _specification(self):
        metadata = {'name': self.name}
        if self.namespace is not None:
            metadata['namespace'] = self.namespace
        rules = []
        for rule in self.rules:
            rules.append(rule._specification())
        spec = {
            'apiVersion': self.api_version,
            'kind': self.kind,
            'metadata': metadata,
            'rules': rules
        }
        return spec

    def configuration(self):
        result = [" ".join(["apiVersion:", self.api_version])]
        result.append(" ".join(["kind:", self.kind]))
        result.append("metadata:")

        indent = "  "
        result.append(indent + " ".join(["name:", self.name]))
        result.append(indent + " ".join(["namespace:", self.namespace]))
        result.append("rules:")
        for rule in self.rules:
            result.append("- " + " ".join(
                ["apiGroups:",
                 output_list_of_strings(rule.api_groups)]))
            result.append(indent + " ".join(
                ["resources:",
                 output_list_of_strings(rule.resources)]))
            result.append(indent + " ".join(
                ["verbs:", output_list_of_strings(rule.verbs)]))
        return "\n".join(result)

    def file(self):
        return file.File(self.name + ".yaml",
                         contents=self.configuration(self))


# apiVersion: rbac.authorization.k8s.io/v1
# kind: ClusterRoleBinding
# metadata:
#   name: {job_launcher_cluster_role_binding}
# subjects:
# - kind: ServiceAccount
#   name: {job_launcher_service_account}
#   namespace: {namespace}
# roleRef:
#   kind: ClusterRole
#   name: {job_manager_role}
#   apiGroup: rbac.authorization.k8s.io


class ClusterRoleBinding(KubeEntity):
    def __init__(self, name, subjects, cluster_role):
        KubeEntity.__init__(self, name, namespace=None)
        self.api_version = "rbac.authorization.k8s.io/v1"
        self.kind = "ClusterRoleBinding"
        self.subjects = subjects
        self.cluster_role = cluster_role
        if not isinstance(cluster_role, ClusterRole):
            raise RuntimeError("Input role must be of ClusterRole type.")

    def _specification(self):
        metadata = {'name': self.name}
        subjects = []
        for subject in self.subjects:
            subject_spec = {}
            subject_spec['kind'] = subject.kind
            subject_spec['name'] = subject.name
            subject_spec['namespace'] = subject.namespace
            subjects.append(subject_spec)
        cluster_role = {}
        cluster_role['kind'] = self.cluster_role.kind
        cluster_role['name'] = self.cluster_role.name
        cluster_role['apiGroup'] = 'rbac.authorization.k8s.io'
        spec = {
            'apiVersion': self.api_version,
            'kind': self.kind,
            'metadata': metadata,
            'subjects': subjects,
            'roleRef': cluster_role
        }
        return spec


# apiVersion: v1
# kind: Service
# metadata:
#   name: {entrypoint_name}
#   namespace: {namespace}
# spec:
#   ttype: NodePort
#   selector:
#     integration: {label_name}
#   ports:
#   - port: 3000
#     targetPort: 3000
#     nodePort: 30001


class ServiceSpec:
    def __init__(self):
        pass


class NodePortSpec(ServiceSpec):
    def __init__(self):
        ServiceSpec.__init__(self)
        self.type = "NodePort"
        self.ports = []
        self.selectors = {}

    def add_selector(self, selector_name, label_name):
        self.selectors[selector_name] = label_name

    def add_port(self, port, node_port, target_port=None):
        ports = {}
        ports['port'] = port
        ports['nodePort'] = node_port
        if target_port is not None:
            ports['targetPort'] = target_port
        else:
            ports['targetPort'] = port
        self.ports.append(ports)

    def _specification(self):
        spec = {
            'type': self.type,
        }
        if len(self.selectors) > 0:
            spec['selector'] = self.selectors
        if len(self.ports) == 0:
            raise RuntimeError("NodePort service does not expose any ports.")
        spec['ports'] = self.ports
        return spec


class Service(KubeEntity):
    def __init__(self, name, spec, namespace=None):
        KubeEntity.__init__(self, name, namespace=namespace)
        self.api_version = "v1"
        self.kind = "Service"
        self.spec = spec

    def _specification(self):
        metadata = {'name': self.name}
        if self.namespace is not None:
            metadata['namespace'] = self.namespace

        service_spec = {}
        if isinstance(self.spec, dict):
            service_spec = self.spec
        elif isinstance(self.spec, ServiceSpec):
            service_spec = self.spec._specification()
        else:
            raise RuntimeError(
                "Invalid service specification type. Use dict or ServiceSpec")
        spec = {
            'apiVersion': self.api_version,
            'kind': self.kind,
            'metadata': metadata,
            'spec': service_spec
        }
        return spec


# apiVersion: apps/v1
# kind: Deployment
# metadata:
#   name: {integration_name}
#   namespace: {namespace}
# spec:
#   replicas: {replicas}
#   selector:
#     matchLabels:
#       integration: {label_name}
#   template:
#     metadata:
#       labels:
#         integration: {label_name}
#     spec: {container}


class Deployment(KubeEntity):
    def __init__(self, name, managed_pod, namespace=None, replicas=None):
        KubeEntity.__init__(self, name, namespace=namespace)
        self.api_version = "apps/v1"
        self.kind = "Deployment"
        self.replicas = replicas
        self.match_labels = {}
        self.managed_pod = managed_pod
        self.match_labels.update(managed_pod._labels)
        self._services = []

    def add_match_label(self, selector_name, label_name):
        self.match_labels[selector_name] = label_name

    def add_service(self, service):
        self._services.append(service)

    def _specification(self):
        metadata = {'name': self.name}
        if self.namespace is not None:
            metadata['namespace'] = self.namespace

        deployment_spec = {}

        # Replicas
        replicas = 1
        if self.replicas is not None:
            replicas = self.replicas
        deployment_spec['replicas'] = replicas

        # Select pods
        pod_selector = {"matchLabels": self.match_labels}
        if len(self.match_labels) > 0:
            deployment_spec['selector'] = pod_selector

        # Pod being deployed
        if not isinstance(self.managed_pod, Pod):
            raise RuntimeError("Deployment pod is not of type Pod.")
        deployment_spec['template'] = self.managed_pod._pod_specification()

        spec = {
            'apiVersion': self.api_version,
            'kind': self.kind,
            'metadata': metadata,
            'spec': deployment_spec
        }
        return spec

    def configuration(self):
        final_config = [yaml.dump(self._specification())]
        for deployment_service in self._services:
            final_config.append(deployment_service.configuration())
        return "\n---\n".join(final_config)


def output_list_of_strings(list_of_strings):
    list_components = []
    for entry in list_of_strings:
        list_components.append("'" + entry + "'")

    return "[" + ",".join(list_components) + "]"
