FROM rayproject/ray:6d5511-py38

COPY --from=docker.io/apache/camel-k:1.3.1 /usr/local/bin/kamel /usr/local/bin/

COPY setup.py ./
COPY rayvens rayvens/
COPY misc/ misc/

RUN pip install rayvens
