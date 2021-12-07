from pathlib import Path
from typing import List

from pytube import YouTube


def yt_download(url: str, name: str, path=None) -> Path:
    yt = YouTube(url).streams.filter(file_extension='mp4', progressive=True).last().download(output_path=path, filename=name)
    print(f"video downloaded {yt}")
    return Path(yt)


def yt_download_from_list_file(list_file: str, save_folder: str) -> List[Path]:
    files = []
    with open(list_file, "r") as f:
        for i, line in enumerate(f):
            file = yt_download(line, f"{i}.mp4", save_folder)
            files.append(file)
    return files
