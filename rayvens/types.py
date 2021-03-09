from enum import Enum

# Enum for capturing the location of the Kamel execution.


class KamelOperatorMode(Enum):
    # The Kamel operator can only be run on the Ray head node.
    OPERATOR_ON_HEAD_NODE = 1

    # Kamel operator can run anywhere in the cluster.
    OPERATOR_ANYWHERE = 2

    # No Kamel operator needed just kamel running local command in a container.
    CONTAINERIZED = 3


class RayKamelExecLocation(Enum):
    # Ray and Kamel running locally.
    LOCAL = 1

    # Ray running locally, Kamel running in the cluster.
    MIXED = 2

    # Ray and Kamel running in the cluster.
    CLUSTER = 3
