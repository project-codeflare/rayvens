from events import kamel_utils

# Method to install kamel in a cluster.
# The cluster needs to be already started. An operator image, and a registry
# that Camel-K can use to publish newly created images to are needed.
def kamelInstall(kamelImage, publishRegistry,
        localCluster=False, usingKind=False,
        insecureRegistry=False):
    # Enforce local cluster, for now.
    # TODO: make this work in an actual cluster.
    if not localCluster:
        raise RuntimeError('only local clusters are supported')

    # If running a local cluster (i.e. cluster running on local machine)
    # then only the kind cluster is supported.
    # TODO: enable this for other cluster types.
    if localCluster and not usingKind:
        raise RuntimeError('locally, only kind cluster is supported')

    command = ["install"]

    # Add kamel operator image.
    command.append("--operator-image")
    command.append(kamelImage)

    # Add registry that kamel can use for image publication.
    command.append("--registry")

    # Kind cluster starts with a registry.
    if usingKind:
        command.append(publishRegistry)

    # Local registry used to publish newly constructed images is insecure.
    # TODO: support secure registries.
    if (insecureRegistry):
        command.append("--registry-insecure")

    # Force installation.
    command.append("--force")

    kamel_utils.invokeReturningCmd(command)

# Invoke kamel uninstall, no arguments are required.
def kamelUninstall():
    kamel_utils.invokeReturningCmd(["uninstall"])

# Invoke kamel local run on a given list of integration files.
# TODO: Explore merging topics and invocation actors. Listen on a topic and attach an external source/sink to it.
def kamelLocalRun(integrationFiles):
    command = ["local", "run", " ".join(integrationFiles)]
    return kamel_utils.invokeLocalOngoingCmd(command)
