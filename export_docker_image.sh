#!/usr/bin/env bash
set -eu

docker build . -t youtube-dl:latest
DOCKER_ID=$(docker ps -aqf "name=youtube-dl:latest")
docker tag youtube-dl:latest alex60015/youtube-dl:latest
docker push alex60015/youtube-dl:latest
