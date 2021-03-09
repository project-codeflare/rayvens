set -eu

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
popd
