set -eu

KAMEL_VERSION=1.3.1
KIND_VERSION=v0.10.0
KUBECTL_VERSION=v1.18.8


# Download and install command line tools
pushd /tmp
  # kubectl
  echo 'installing kubectl'
  curl -Lo ./kubectl https://storage.googleapis.com/kubernetes-release/release/$KUBECTL_VERSION/bin/linux/amd64/kubectl
  chmod +x kubectl
  sudo cp kubectl /usr/local/bin/kubectl

  # kind
  echo 'installing kind'
  curl -Lo ./kind https://github.com/kubernetes-sigs/kind/releases/download/$KIND_VERSION/kind-linux-amd64
  chmod +x kind
  sudo cp kind /usr/local/bin/kind

  # kamel
  echo 'installing kamel'
  curl -L https://github.com/apache/camel-k/releases/download/v1.3.1/camel-k-client-$KAMEL_VERSION-linux-64bit.tar.gz | tar zx ./kamel
  sudo cp kamel /usr/local/bin/kamel

popd
