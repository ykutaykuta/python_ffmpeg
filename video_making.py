import shutil
import subprocess
from pathlib import Path

OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080
TIME_SPLIT = "00:00:30"

REPLACE_AUDIO = True
ADD_PHOTO = True
ADD_INTRO_OUTRO = True

ff_add_slient_audio = 'ffmpeg -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 -i "{}" -c:v h264 -c:a aac -shortest "{}" -y'
ff_transcode = 'ffmpeg {} -i "{}" -map 0:v:0 -map 0:a:0 -r 30 -g 60 -s {}x{} -ar 44100 -c:v h264 -c:a aac "{}" -y'
ff_concat = 'ffmpeg -f concat -safe 0 -i "{}" -c copy "{}" -y'
ff_split = 'ffmpeg -i "{}" -c copy -map 0 -segment_time {} -f segment -reset_timestamps 1 tmp/segment%03d.mp4 -y'
ff_add_audio = 'ffmpeg -i "{}" -stream_loop -1 -i "{}" -shortest -map 0:v -map 1:a -ar 44100 -c:v copy -c:a aac "{}" -y'
ff_photo = 'ffmpeg -i "{}" -i "{}" -filter_complex "overlay=10:10" "{}" -y'
ffprobe = 'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{}"'


def get_length(filename: str) -> float:
    cmd = ffprobe.format(filename)
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    duration = float(result.stdout)
    print(f"video {filename} with duration {duration}s")
    return duration


def do_command(cmd: str):
    print("\n\n" + cmd + "\n")
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, shell=True)
    while True:
        output = p.stdout.readline()
        print(output)
        if output == '' and p.poll() is not None:
            break


def main():
    curr_dir = Path.cwd().absolute()
    tmp_dir = curr_dir.joinpath("tmp")
    if not tmp_dir.exists():
        tmp_dir.mkdir(parents=True, exist_ok=True)

    lists = tmp_dir.joinpath("lists.txt")
    transition_video = curr_dir.joinpath("transition.mp4")
    intro_video = curr_dir.joinpath("intro.mp4")
    outro_video = curr_dir.joinpath("outro.mp4")
    replaced_audio = curr_dir.joinpath("audio.mp3")
    photo = curr_dir.joinpath("logo.png")
    video_dir = curr_dir.joinpath("videos")

    final_video = curr_dir.joinpath("final.mp4")

    files = []
    for file in video_dir.glob("**/*"):
        if file.is_file() and file.suffix.lower() == ".mp4":
            files.append(file)
    if len(files) == 0:
        exit(0)

    # rescale video input
    idx = 0
    with open(str(lists), "w") as f:
        for file in files:
            duration = get_length(str(file))
            duration = f"-t {duration-5}"
            new_file = tmp_dir.joinpath(f"{idx}.mp4")
            cmd = ff_transcode.format(duration, str(file), OUTPUT_WIDTH, OUTPUT_HEIGHT, str(new_file))
            do_command(cmd)
            f.write(f"file '{str(new_file)}'\n")
            idx += 1

    # assemble
    cmd = ff_concat.format(str(lists), str(final_video))
    do_command(cmd)

    # clear tmp directory
    for file in tmp_dir.glob("**/*"):
        if file.is_file():
            file.unlink()

    # split
    cmd = ff_split.format(str(final_video), TIME_SPLIT)
    do_command(cmd)

    # transcode transition and concat transition
    files = []
    for file in tmp_dir.glob("**/*"):
        if file.is_file() and file.suffix.lower() == ".mp4":
            files.append(file)
    new_file = tmp_dir.joinpath("transition.mp4")
    cmd = ff_transcode.format(" ", str(transition_video), OUTPUT_WIDTH, OUTPUT_HEIGHT, str(new_file))
    do_command(cmd)
    transition_video = new_file
    idx = 0
    tmp = []
    for file in files:
        new_file = tmp_dir.joinpath(f"{idx}.mp4")
        with open(str(lists), "w") as f:
            f.write(f"file '{str(file)}'\n")
            f.write(f"file '{str(transition_video)}'\n")
        cmd = ff_concat.format(str(lists), str(new_file))
        do_command(cmd)
        tmp.append(new_file)
        idx += 1
    files = tmp

    # concat to full video
    with open(str(lists), "w") as f:
        for file in files:
            f.write(f"file '{str(file)}'\n")
    cmd = ff_concat.format(str(lists), str(final_video))
    do_command(cmd)

    # add photo
    if ADD_PHOTO:
        new_file = final_video.with_name("tmp.mp4")
        cmd = ff_photo.format(str(final_video), str(photo), str(new_file))
        do_command(cmd)
        final_video.unlink()
        new_file.rename(final_video)

    # add custom audio
    if REPLACE_AUDIO:
        new_file = final_video.with_name("tmp.mp4")
        cmd = ff_add_audio.format(str(final_video), str(replaced_audio), str(new_file))
        do_command(cmd)
        final_video.unlink()
        new_file.rename(final_video)

    # normalize intro and outro
    if ADD_INTRO_OUTRO:
        new_file = tmp_dir.joinpath("intro.mp4")
        cmd = ff_add_slient_audio.format(str(intro_video), str(new_file))
        do_command(cmd)
        intro_video = new_file
        new_file = tmp_dir.joinpath("outro.mp4")
        cmd = ff_add_slient_audio.format(str(outro_video), str(new_file))
        do_command(cmd)
        outro_video = new_file

        with open(str(lists), "w") as f:
            f.write(f"file '{str(intro_video)}'\n")
            f.write(f"file '{str(final_video)}'\n")
            f.write(f"file '{str(outro_video)}'\n")
        new_file = final_video.with_name("tmp.mp4")
        cmd = ff_concat.format(str(lists), str(new_file))
        do_command(cmd)
        final_video.unlink()
        new_file.rename(final_video)

    # clear
    lists.unlink()
    shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    main()
