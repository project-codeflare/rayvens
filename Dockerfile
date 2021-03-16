FROM rayproject/ray:6d5511-py38

COPY --from=docker.io/apache/camel-k:1.3.1 /usr/local/bin/kamel /usr/local/bin/

RUN sudo apt-get update -qq \
    && sudo apt-get install -y -qq --no-install-recommends openjdk-11-jdk maven \
    && sudo rm -rf /var/lib/apt/lists/* \
    && sudo apt-get clean

COPY setup.py rayvens/
COPY rayvens rayvens/rayvens/

RUN sudo chown -R ray:users rayvens

RUN pip install confluent_kafka==1.6.0
RUN pip install -e ./rayvens
