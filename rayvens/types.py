from enum import Enum

# Enum for capturing the location of the Kamel execution.


class CamelOperatorMode(Enum):
    # The Kamel operator can only be run on the Ray head node.
    HEAD_NODE = 1

    # Kamel operator can run anywhere in the cluster.
    ANY_NODE = 2

    # No Kamel operator needed just kamel running local command in a container.
    CONTAINERIZED = 3
