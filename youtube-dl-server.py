import sys, subprocess, stat

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates
from starlette.background import BackgroundTask

import uvicorn
from yt_dlp import YoutubeDL
from collections import ChainMap
import shutil
import os

templates = Jinja2Templates(directory="")

app_defaults = {
    "YDL_FORMAT": "bestvideo+bestaudio/best",
    "YDL_EXTRACT_AUDIO_FORMAT": None,
    "YDL_EXTRACT_AUDIO_QUALITY": "192",
    "YDL_RECODE_VIDEO_FORMAT": None,
    "YDL_SERVER_HOST": "0.0.0.0",
    "YDL_SERVER_PORT": 8080,
    "YDL_UPDATE_TIME": "True",
    "YDL_DEFAULT_PATH": "/usr/src/app/youtube-dl"
}


async def dl_queue_list(request):
    return templates.TemplateResponse("index.html", {"request": request})


async def q_put(request):
    form = await request.form()
    url = form.get("url").strip()
    name = form.get("name")
    path = form.get("path")

    if not url:
        return JSONResponse(
            {"success": False, "error": "/q called without a 'url' in form data"}
        )

    if name == "":
        name = "%(title).200s.%(ext)s"
    else:
        name = name.strip()
        if not name.endswith("." + form.get("format"))
            name = name + "." + form.get("format")

    if path is None:
        path = ""
    else:
        path = path.strip()

    if not path.startswith("/"):
        path = "/" + path

    if not path.endswith("/"):
        path = path + "/"

    options = {
        "format": form.get("format"),
        "tmp_path": "/tmp/youtube-dl" + path,
        "result_path": app_vars["YDL_DEFAULT_PATH"] + path,
        "name": name
    }

    print("Checking url...")
    ydl = YoutubeDL()
    with ydl:
        try:
            info = ydl.extract_info(url, download=False)
            if form.get("name") == "":
                options["downloadName"] = info["title"][:200] + "." + form.get("format")
            else:
                options["downloadName"] = options["name"] + "." + form.get("format")
        except Exception as e:
            print("URL not supported: " + url)

            return JSONResponse(
                {"success": False, "url": url, "options": options}, status_code=400
            )

    print("Check complete")

    task = BackgroundTask(download, url, options)

    print("Added url to the download queue")
    return JSONResponse(
        {"success": True, "url": url, "options": options}, background=task
    )


async def update_route(_scope, _receive, _send):
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

    requested_format = request_options.get("format", "bestaudio")

    if requested_format in ["aac", "mp3"]:
        request_vars["YDL_EXTRACT_AUDIO_FORMAT"] = requested_format
    elif requested_format == "bestaudio":
        request_vars["YDL_EXTRACT_AUDIO_FORMAT"] = "best"
    elif requested_format in ["mp4"]:
        request_vars["YDL_RECODE_VIDEO_FORMAT"] = requested_format

    print("[youtube-dl-server]" + requested_format)

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
        "outtmpl": request_options.get("tmp_path") + request_options.get("name"),
        "updatetime": ydl_vars["YDL_UPDATE_TIME"] == "True",
        "verbose": "true",
        "fragment_retries": 1,
    }


def download(url, request_options):
    with YoutubeDL(get_ydl_options(request_options)) as ydl:
        test = ydl.download([url])

        tmp_path = request_options.get("tmp_path") + request_options.get("downloadName")
        result_path = request_options.get("result_path") + request_options.get("downloadName")

        print("Download complete, move " + request_options.get("name") + " from " + tmp_path + " to " + result_path)
        os.makedirs(request_options.get("result_path"), exist_ok=True)
        shutil.move(tmp_path, result_path)


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
