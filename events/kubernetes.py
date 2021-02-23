from events import kubernetes_utils

# Wait for pod to reach running state.
def getPodRunningStatus(podBaseName):
    # TODO: adapt this to support multiple namespaces.
    command = ["get", "pods", "-w", "--all-namespaces"]
    return kubernetes_utils.getPodStatusCmd(command, podBaseName)