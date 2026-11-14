from dataclasses import replace
from pathlib import Path

from highlights.config import Settings


def settings(tmp_path):
    return replace(Settings(), data_dir=tmp_path)


def test_new_paths_are_stored_relative(tmp_path):
    s = settings(tmp_path)
    final = tmp_path / "work" / "event-3" / "Trip.mp4"
    assert s.to_stored(final) == "work/event-3/Trip.mp4"
    assert s.from_stored("work/event-3/Trip.mp4") == final


def test_old_windows_paths_follow_the_data_folder(tmp_path):
    # Rows written before the move to Linux hold absolute Windows paths.
    s = settings(tmp_path)
    old = r"E:\Highlights\work\event-7\Beach · May 2022.mp4"
    assert s.from_stored(old) == tmp_path / "work" / "event-7" / "Beach · May 2022.mp4"


def test_old_absolute_posix_paths_follow_the_data_folder(tmp_path):
    s = settings(tmp_path)
    assert s.from_stored("/srv/old/work/event-1/a.mp4") == tmp_path / "work" / "event-1" / "a.mp4"


def test_empty_stored_path():
    assert Settings().from_stored(None) is None and Settings().from_stored("") is None


def test_ffmpeg_falls_back_to_path(tmp_path):
    s = replace(Settings(), ffmpeg_dir=None)
    assert s.ffmpeg == "ffmpeg" and s.ffprobe == "ffprobe"
    (tmp_path / "ffmpeg").write_text("")
    assert replace(Settings(), ffmpeg_dir=tmp_path).ffmpeg == str(Path(tmp_path) / "ffmpeg")
