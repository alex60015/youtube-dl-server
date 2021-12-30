import sys
import subprocess
import uvicorn
import shutil
import os
from os.path import exists
from slugify import slugify
from yt_dlp import YoutubeDL
from yt_dlp.utils import ExtractorError, UnsupportedError, DownloadError
from collections import ChainMap

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates
from starlette.background import BackgroundTask

templates = Jinja2Templates(directory="")

app_defaults = {
    "YDL_FORMAT": "bestvideo+bestaudio/best",
    "YDL_EXTRACT_AUDIO_FORMAT": None,
    "YDL_EXTRACT_AUDIO_QUALITY": "192",
    "YDL_RECODE_VIDEO_FORMAT": None,
    "YDL_SERVER_HOST": "0.0.0.0",
    "YDL_SERVER_PORT": 8080,
    "YDL_UPDATE_TIME": "True",
    "YDL_DEFAULT_PATH": "/usr/src/app/youtube-dl",
    "YDL_TMP_PATH": "/tmp/youtube-dl",
}


async def dl_queue_list(request):
    return templates.TemplateResponse("index.html", {"request": request})


def validate_and_set_default_form_params(form):
    form_inputs = {
        "url": form.get("url").strip(),
        "format": None,
        "name": None,
        "path": None,
    }

    requested_format = form.get("format", "mp3")

    if not requested_format in ["aac", "mp3", "mp4"]:
        requested_format = "mp3"

    form_inputs["format"] = requested_format

    form_inputs["name"] = form.get("name", "%(title).200s.%(ext)s").strip()
    if form_inputs["name"].endswith("." + requested_format):
        form_inputs["name"] = form_inputs["name"].replace(requested_format, "")

    path = form.get("path", "/").strip()

    if not path.startswith("/"):
        path = "/" + path

    if not path.endswith("/"):
        path = path + "/"

    form_inputs["path"] = path

    return form_inputs


async def q_put(request):
    form = await request.form()

    form_inputs = validate_and_set_default_form_params(form)

    if not form_inputs["url"]:
        return JSONResponse(
            {"success": False, "error": "/q called without a 'url' in form data"}
        )

    # Empty string equals: fill out later when we have the info
    options = {
        "format": form_inputs.get("format"),
        "path": form_inputs["path"],
        "tmp_path": app_vars["YDL_TMP_PATH"] + form_inputs["path"],
        "result_path": app_vars["YDL_DEFAULT_PATH"] + form_inputs["path"],
        "name": "",
    }

    print("[youtube-dl-server] Checking url...")
    ydl = YoutubeDL()
    with ydl:
        try:
            info = ydl.extract_info(form_inputs["url"], download=False)
            if form_inputs["name"] == "%(title).200s.%(ext)s":
                options["name"] = slugify(info["title"][:200])
            else:
                options["name"] = slugify(form_inputs["name"])

        except (ExtractorError, UnsupportedError, DownloadError) as e:
            print("URL not supported: " + form_inputs["url"])

            return JSONResponse(
                {"success": False, "url": form_inputs["url"], "options": options}, status_code=400
            )

    print("[youtube-dl-server] Check complete")

    task = BackgroundTask(download, form_inputs["url"], options)

    print("[youtube-dl-server] Added url to the download queue")
    return JSONResponse(
        {"success": True, "url": form_inputs["url"], "options": options}, background=task
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

    print("[youtube-dl-server] " + requested_format)

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
        ydl.download([url])
        nameWithFormat = request_options.get("name") + "." + request_options["format"]

        tmp_path = request_options.get("tmp_path") + nameWithFormat
        result_path = request_options.get("result_path") + nameWithFormat

        print(
            "[youtube-dl-server] Download complete, move " + nameWithFormat +
            " from " + tmp_path + " to " + result_path
        )
        os.makedirs(request_options.get("result_path"), exist_ok=True)

        # I fucking hate the errors that the file is missing the format at the end...
        tmp_path_without_format = request_options.get("tmp_path") + request_options.get("name")
        if exists(tmp_path_without_format):
            shutil.move(tmp_path_without_format, result_path)
        else:
            shutil.move(tmp_path, result_path)


routes = [
    Route("/", endpoint=dl_queue_list),
    Route("/q", endpoint=q_put, methods=["POST"]),
    Route("/update", endpoint=update_route, methods=["PUT"]),
]

app = Starlette(debug=True, routes=routes)

print("[youtube-dl-server] Updating youtube-dl to the newest version")
update()

app_vars = ChainMap(os.environ, app_defaults)

if __name__ == "__main__":
    uvicorn.run(
        app, host=app_vars["YDL_SERVER_HOST"], port=int(app_vars["YDL_SERVER_PORT"])
    )
