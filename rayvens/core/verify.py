from rayvens.core import kamel
from rayvens.core.mode import mode


def verify_log(integration_name, message):
    _outcome(kamel.log(mode, integration_name, message) is not None)


def _outcome(success):
    log = "SUCCESS"
    if not success:
        log = "FAIL"
    print("[LOG CHECK]:", log)
