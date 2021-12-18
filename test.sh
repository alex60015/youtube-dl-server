#!/bin/bash
set -eu

check_download_format () {
  format=$1

  echo "Download and check $format"
  # Rasputin vs Stalin. Epic Rap Battles of History
  curl -X POST --data-urlencode "url=http://youtube.com/watch?v=ZT2z0nrsQ8o" \
    --data-urlencode "name=Rasputin vs Stalin $format" \
    --data-urlencode "format=$format" \
    --data-urlencode "path=$format-Folder" \
    http://localhost:8080/q

  echo ""

  while true
  do
    echo "Checking..."
    sleep 10s
    if docker logs "$CONTAINER_ID" 2>&1 | grep -q "Download complete, move Rasputin vs Stalin $format"
    then
      echo "$format Download complete"
      break
    fi
  done

  sleep 5s
  if [ -f "$(pwd)/test/$format-Folder/Rasputin vs Stalin $format.$format" ]; then
      echo "$format download WORKED"
  else
      ls -la "$(pwd)/test/$format-Folder/Rasputin vs Stalin $format.$format"
      echo "$(pwd)/test/$format-Folder/Rasputin vs Stalin $format.$format"
      echo "$format download FAILED."
      exit 1
  fi

  return 0
}

main () {
  echo "Starting test container for youtube-dl-server..."
  CURRENT_PATH="$(pwd)"
  docker build -t yt-dlp:test .
  CONTAINER_ID="$(docker run -d --net="host" --name youtube-dl -v "$CURRENT_PATH/test":/usr/src/app/youtube-dl yt-dlp:test)"

  echo "Starting complete, sending test requests in 5 seconds..."
  sleep 5
  check_download_format "mp3"
  check_download_format "aac"
  check_download_format "mp4"

  echo "All tests ran, doing cleanup"
  echo "Synology doesn't care about permissions, so the files belong to root and we need to delete them"
  sudo rm -rf ./test/*
  docker container kill "$CONTAINER_ID"
  docker container rm "$CONTAINER_ID"
  echo "Done"
  return 0
}

main
