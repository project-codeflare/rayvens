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
import rayvens.cli.file as file

all_verbs = ["get", "list", "watch", "create", "update", "patch", "delete"]
api_groups = {'jobs': ["batch", "extensions"]}


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


class Container:
    def __init__(self, name, image, image_pull_policy=None):
        self.name = name
        self.image = image
        self.image_pull_policy = image_pull_policy
        self.command = None
        self._envvars = []
        self._ports = []

    def add_port(self, port_name, value):
        self._ports.append({port_name: value})

    def add_envvar(self, env_var_name, value):
        self._envvars.append({"name": env_var_name, "value": value})

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

        return spec


class Pod(KubeEntity):
    def __init__(self, name, namespace=None):
        KubeEntity.__init__(self, name, namespace=namespace)
        self.api_version = "v1"
        self.kind = "Pod"
        self._service_account = None
        self.labels = {}
        self.containers = []

    def add_label(self, label_name, label_value):
        self.labels[label_name] = label_value

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

        if len(self.labels) > 0:
            metadata['labels'] = self.labels

        container_specs = []
        for container in self.containers:
            if not isinstance(container, Container):
                raise RuntimeError("Invalid container used in pod.")
            container_specs.append(container._specification())

        pod_spec = {}
        if self._service_account is not None:
            if not isinstance(self._service_account, ServiceAccount):
                raise RuntimeError(
                    "Invalid service account type, use ServiceAccount.")
            pod_spec['serviceAccountName'] = self._service_account.name
        pod_spec['containers'] = container_specs

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
        self.match_labels.update(managed_pod.labels)
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
