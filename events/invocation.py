import ray
import subprocess
import os
import signal

# Wrap invocation as actor.

@ray.remote
class KamelInvocationActor:
    def __init__(self, command, shell=True):
        # Command is normally a list of words.
        # When shell flag is true the command needs to be passed in as
        # a single string preceded by exec.
        execCommand = command
        if shell:
            execCommand = "exec " + " ".join(command)

        self.process = subprocess.Popen(execCommand,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            preexec_fn=os.setsid)

    def isKamelReady(self):
        # Check if kamel instance launched correctly.
        instantiationFailed = False
        while True:
            output = self.process.stdout.readline().decode("utf-8")

            # Log progress of kamel subprocess
            print("[Kamel subprocess]", output.strip())
            returnCode = self.process.poll()
            if returnCode is not None:
                instantiationFailed = True
                break
            # Some form of completion signal is received.
            # Use the Kamel output to decide when Kamel instance is
            # ready to receive requests.
            if "Installed features:" in output:
                break

        # Emit success/fail message.
        if instantiationFailed:
            print("Kamel instance failed.")
            return False
        else:
            print("Kamel instance is ready.")
            return True

    def kill(self):
        # Magic formula for terminating all processes in the group including
        # any subprocesses that the kamel command might have created.
        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
