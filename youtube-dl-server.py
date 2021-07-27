import os, sys, subprocess

from starlette.applications import Starlette
from starlette.staticfiles import StaticFiles
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.templating import Jinja2Templates
from starlette.background import BackgroundTask

import uvicorn
from youtube_dl import YoutubeDL
from collections import ChainMap
import shutil
import os

templates = Jinja2Templates(directory="")

app_defaults = {
    "YDL_FORMAT": "bestvideo+bestaudio/best",
    "YDL_EXTRACT_AUDIO_FORMAT": None,
    "YDL_EXTRACT_AUDIO_QUALITY": "192",
    "YDL_RECODE_VIDEO_FORMAT": None,
    "YDL_ARCHIVE_FILE": "/usr/src/app/youtube-dl/youtube-dl_archive_file",
    "YDL_SERVER_HOST": "0.0.0.0",
    "YDL_SERVER_PORT": 8080,
    "YDL_UPDATE_TIME": "True",
}


async def dl_queue_list(request):
    return templates.TemplateResponse("index.html", {"request": request})

async def q_put(request):
    form = await request.form()
    url = form.get("url").strip()
    name = form.get("name").strip()
    path = form.get("path").strip()

    if not url:
        return JSONResponse(
            {"success": False, "error": "/q called without a 'url' in form data"}
        )

    if name == "":
        name = "%(title)s.%(ext)s"

    if not path.startswith("/"):
        path = "/" + path

    if not path.endswith("/"):
        path = path + "/"

    tmpPath = "/tmp/youtube-dl" + path
    resultPath = "/usr/src/app/youtube-dl" + path

    options = {"format": form.get("format"), "tmpPath": tmpPath, "resultPath": resultPath, "name": name}
    task = BackgroundTask(download, url, options)

    print("Added url " + url + " to the download queue")
    return JSONResponse(
        {"success": True, "url": url, "options": options}, background=task
    )


async def update_route(scope, receive, send):
    task = BackgroundTask(update)

    return JSONResponse({"output": "Initiated package update"}, background=task)


def update():
    try:
        output = subprocess.check_output(
            [sys.executable, "-m", "pip", "install", "--upgrade", "youtube-dl"]
        )

        print(output.decode("ascii"))
    except subprocess.CalledProcessError as e:
        print(e.output)

def get_ydl_options(request_options):
    request_vars = {
        "YDL_EXTRACT_AUDIO_FORMAT": None,
        "YDL_RECODE_VIDEO_FORMAT": None,
    }

    requested_format = request_options.get("format", "bestvideo")

    if requested_format in ["aac", "mp3"]:
        request_vars["YDL_EXTRACT_AUDIO_FORMAT"] = requested_format
    elif requested_format == "bestaudio":
        request_vars["YDL_EXTRACT_AUDIO_FORMAT"] = "best"
    elif requested_format in ["mp4"]:
        request_vars["YDL_RECODE_VIDEO_FORMAT"] = requested_format

    ydl_vars = ChainMap(request_vars, os.environ, app_defaults)

    postprocessors = []

    if ydl_vars["YDL_EXTRACT_AUDIO_FORMAT"]:
        postprocessors.append(
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": ydl_vars["YDL_EXTRACT_AUDIO_FORMAT"],
                "preferredquality": ydl_vars["YDL_EXTRACT_AUDIO_QUALITY"],
            }
        )

    if ydl_vars["YDL_RECODE_VIDEO_FORMAT"]:
        postprocessors.append(
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": ydl_vars["YDL_RECODE_VIDEO_FORMAT"],
            }
        )

    return {
        "format": ydl_vars["YDL_FORMAT"],
        "postprocessors": postprocessors,
        "outtmpl": request_options.get("tmpPath") + request_options.get("name"),
        "download_archive": ydl_vars["YDL_ARCHIVE_FILE"],
        "updatetime": ydl_vars["YDL_UPDATE_TIME"] == "True",
    }

def download(url, request_options):
    with YoutubeDL(get_ydl_options(request_options)) as ydl:
        ydl.download([url])

        format = request_options.get("format")
        name = request_options.get("name")
        tmpPath = request_options.get("tmpPath") + name + "." + format
        resultPath = request_options.get("resultPath") + name + "." + format

        print("Download complete, move " + name + " from " + tmpPath + " to " + resultPath)
        os.makedirs(request_options.get("resultPath"))
        shutil.move(tmpPath, resultPath)

routes = [
    Route("/", endpoint=dl_queue_list),
    Route("/q", endpoint=q_put, methods=["POST"]),
    Route("/update", endpoint=update_route, methods=["PUT"]),
]

app = Starlette(debug=True, routes=routes)

print("Updating youtube-dl to the newest version")
update()

app_vars = ChainMap(os.environ, app_defaults)

if __name__ == "__main__":
    uvicorn.run(
        app, host=app_vars["YDL_SERVER_HOST"], port=int(app_vars["YDL_SERVER_PORT"])
    )
