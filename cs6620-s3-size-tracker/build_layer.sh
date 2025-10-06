#!/bin/bash
set -e
IMAGE=cs6620-matplotlib-layer-build
CONTAINER_OUTPUT=/tmp/matplotlib_layer.zip

docker build -t $IMAGE .
# run a container to copy the output zip
CID=$(docker create $IMAGE)
docker cp ${CID}:/opt/matplotlib_layer.zip ${CONTAINER_OUTPUT}
docker rm ${CID}
echo "Layer zip is at ${CONTAINER_OUTPUT}. Upload to AWS Lambda Layers via console or CLI."