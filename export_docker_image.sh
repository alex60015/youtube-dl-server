#!/usr/bin/env bash
set -eu

docker build . -t youtube-dl:local
DOCKER_ID=$(docker ps -aqf "name=youtube-dl")
docker export $DOCKER_ID -o youtube-dl.tar
