#!/bin/bash
set -eu

echo "Starting test container for youtube-dl-server..."
CURRENT_PATH=`pwd`
docker build -t yt-dlp:test .
CONTAINER_ID=$(docker run -d --net="host" --name youtube-dl -v /home/aheine/dev/youtube-dl-server/test/:/youtube-dl yt-dlp:test)

echo "Starting complete, sending test requests in 5 seconds..."
sleep 5
echo "Format: MP3"
# Rasputin vs Stalin. Epic Rap Battles of History
curl -X POST --data-urlencode "url=http://youtube.com/watch?v=ZT2z0nrsQ8o" \
  --data-urlencode "name=Rasputin vs Stalin" \
  --data-urlencode "format=mp3" \
  --data-urlencode "path=mp3Folder" \
  http://localhost:8080/q

echo ""

echo "Format: AAC"
echo ""
# Rasputin vs Stalin. Epic Rap Battles of History
curl -X POST --data-urlencode "url=http://youtube.com/watch?v=ZT2z0nrsQ8o" \
  --data-urlencode "name=Rasputin vs Stalin" \
  --data-urlencode "format=aac" \
  --data-urlencode "path=aacFolder" \
  http://localhost:8080/q

echo ""

echo "Format: MP4"
# Rasputin vs Stalin. Epic Rap Battles of History
curl -X POST --data-urlencode "url=http://youtube.com/watch?v=ZT2z0nrsQ8o" \
  --data-urlencode "name=Rasputin vs Stalin" \
  --data-urlencode "format=mp4" \
  --data-urlencode "path=mp4Folder" \
  http://localhost:8080/q

echo ""
echo "Waiting for the download (60 Sec)..."
echo "Container id: $CONTAINER_ID"

sleep 60

if [[ ! -f "$CURRENT_PATH/test/mp3Folder/Rasputin vs Stalin.mp3" ]]; then
    echo "MP3 download failed."
fi

if [[ ! -f "$CURRENT_PATH/test/aacFolder/Rasputin vs Stalin.aac" ]]; then
    echo "AAC download failed."
fi

if [[ ! -f "$CURRENT_PATH/test/mp4Folder/Rasputin vs Stalin.mp4" ]]; then
    echo "MP4 download failed."
fi

echo "All tests runned, killing container"
docker container kill $CONTAINER_ID
docker container rm $CONTAINER_ID
echo "Done"