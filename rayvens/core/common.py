from rayvens.core import kubernetes


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
