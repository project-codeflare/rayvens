#!/bin/sh

echo 'WARNING: This script gives cluster admin permissions to all service accounts.'
if [[ "$1" = '--yes' ]]; then
  echo 'WARNING: Automatic due to --yes.'
  REPLY='y'
else
  read -p 'WARNING: Do you wish to proceed (y/n)?'
fi

if [[ "$REPLY" == "y" ]]; then
  kubectl create clusterrolebinding serviceaccounts-cluster-admin --clusterrole=cluster-admin --group=system:serviceaccounts
fi
