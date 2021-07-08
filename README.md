[![Docker Stars Shield](https://img.shields.io/docker/stars/kmb32123/youtube-dl-server.svg?style=flat-square)](https://hub.docker.com/r/kmb32123/youtube-dl-server/)
[![Docker Pulls Shield](https://img.shields.io/docker/pulls/kmb32123/youtube-dl-server.svg?style=flat-square)](https://hub.docker.com/r/kmb32123/youtube-dl-server/)
[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](https://raw.githubusercontent.com/manbearwiz/youtube-dl-server/master/LICENSE)

# youtube-dl-server

Very spartan Web and REST interface for downloading youtube videos onto a server. [`starlette`](https://github.com/encode/starlette) + [`youtube-dl`](https://github.com/rg3/youtube-dl).

![screenshot][1]

## Running

### Docker CLI

This example uses the docker run command to create the container to run the app. Here we also use host networking for simplicity. Also note the `-v` argument. This directory will be used to output the resulting videos

```shell
docker run -d --net="host" --name youtube-dl -v /home/core/youtube-dl:/youtube-dl kmb32123/youtube-dl-server
```

### Docker Compose

This is an example service definition that could be put in `docker-compose.yml`. This service uses a VPN client container for its networking.

```yml
  youtube-dl:
    image: "kmb32123/youtube-dl-server"
    network_mode: "service:vpn"
    volumes:
      - /home/core/youtube-dl:/youtube-dl
    restart: always
```

### Python

If you have python ^3.6.0 installed in your PATH you can simply run like this, providing optional environment variable overrides inline.

```shell
YDL_SERVER_PORT=8123 YDL_UPDATE_TIME=False python3 -u ./youtube-dl-server.py
```

In this example, `YDL_UPDATE_TIME=False` is the same as the command line option `--no-mtime`.

## Usage

### Start a download remotely

Downloads can be triggered by supplying the `{{url}}` of the requested video through the Web UI or through the REST interface via curl, etc.

#### HTML

Just navigate to `http://{{host}}:8080/youtube-dl` and enter the requested `{{url}}`.

#### Curl

```shell
curl -X POST --data-urlencode "url={{url}}" http://{{host}}:8080/youtube-dl/q
```

#### Fetch

```javascript
fetch(`http://${host}:8080/youtube-dl/q`, {
  method: "POST",
  body: new URLSearchParams({
    url: url,
    format: "bestvideo"
  }),
});
```

#### Bookmarklet

Add the following bookmarklet to your bookmark bar so you can conviently send the current page url to your youtube-dl-server instance.

```javascript
javascript:!function(){fetch("http://${host}:8080/youtube-dl/q",{body:new URLSearchParams({url:window.location.href,format:"bestvideo"}),method:"POST"})}();
```

## Implementation

The server uses [`starlette`](https://github.com/encode/starlette) for the web framework and [`youtube-dl`](https://github.com/rg3/youtube-dl) to handle the downloading. The integration with youtube-dl makes use of their [python api](https://github.com/rg3/youtube-dl#embedding-youtube-dl).

This docker image is based on [`python:alpine`](https://registry.hub.docker.com/_/python/) and consequently [`alpine:3.8`](https://hub.docker.com/_/alpine/).

[1]:youtube-dl-server.png

# Export to NAS
## Synology

To export this project to your synology nas, you need to build the docker locally and export the image:

```shell
docker save youtube-dl > youtube-dl.tar
```

Then upload this file to your NAS and load the image via file import.

Set the output port to 8080 and a mount to /youtube-dl and you're ready to go.

# TODOS
- Add proper response of running downloads / status
  - Disable button for 2-5 Seconds fter clicking it
- Show error if file could not be downloaded (dry run/[simulate](https://github.com/ytdl-org/youtube-dl/blob/08250b69c29f8fc3bb73c6461363472197a86f03/youtube_dl/YoutubeDL.py#L160) beforehand?)
- Show error and path if file was already downloaded
  - Option to ignore it and download again?
- Make extended form more pretty
