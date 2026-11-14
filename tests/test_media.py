from pathlib import Path

from highlights import media


def graph(cmd: list[str]) -> str:
    return cmd[cmd.index("-filter_complex") + 1]


def test_every_segment_is_tagged_sdr_bt709():
    # The final join copies segments as they are; one HDR or full-range segment turns the
    # video black in players from that point on.
    segs = [media.Segment("photo", Path("p.jpg"), 0, 3.5),
            media.Segment("clip", Path("c.mp4"), 1, 3, has_audio=True),
            media.Segment("clip", Path("h.mov"), 1, 3, hdr=True)]
    for seg in segs:
        cmd = media.segment_command("ffmpeg", seg, Path("o.mp4"), "libx264")
        assert media._TAGS in graph(cmd)
        assert cmd[cmd.index("-color_trc") + 1] == "bt709"
        assert cmd[cmd.index("-color_range") + 1] == "tv"


def test_only_hdr_clips_are_tone_mapped():
    sdr = media.segment_command("ffmpeg", media.Segment("clip", Path("c.mp4"), 0, 3),
                                Path("o.mp4"), "libx264")
    hdr = media.segment_command("ffmpeg", media.Segment("clip", Path("h.mov"), 0, 3, hdr=True),
                                Path("o.mp4"), "libx264")
    assert "tonemap" not in graph(sdr) and "out_range=tv" in graph(sdr)
    assert "tonemap=tonemap=hable" in graph(hdr)


def test_quick_sync_gets_its_device_before_the_inputs_and_nv12():
    seg = media.Segment("clip", Path("c.mp4"), 1, 3, has_audio=True)
    cmd = media.segment_command("ffmpeg", seg, Path("o.mp4"), "h264_qsv", "/dev/dri/renderD129")
    assert cmd[1:3] == ["-init_hw_device", "qsv=hw:/dev/dri/renderD129"]
    assert cmd.index("-init_hw_device") < cmd.index("-i")
    assert cmd[cmd.index("-c:v") + 1] == "h264_qsv"
    assert cmd[cmd.index("-pix_fmt") + 1] == "nv12"


def test_software_and_nvenc_need_no_device_and_stay_yuv420p():
    seg = media.Segment("photo", Path("p.jpg"), 0, 3.5)
    for encoder in ("libx264", "h264_nvenc"):
        cmd = media.segment_command("ffmpeg", seg, Path("o.mp4"), encoder)
        assert "-init_hw_device" not in cmd
        assert cmd.count("-pix_fmt") == 1 and cmd[cmd.index("-pix_fmt") + 1] == "yuv420p"


def test_no_window_flag_is_only_set_on_windows():
    import os
    assert (media.NO_WINDOW != 0) == (os.name == "nt")


def test_quick_sync_is_skipped_without_its_device(monkeypatch):
    tried = []

    def failing_run(cmd, timeout=0):
        tried.append(cmd)
        raise RuntimeError("no encoder")

    monkeypatch.setattr(media, "run", failing_run)
    assert media.detect_encoder("ffmpeg", "/no/such/device") == "libx264"
    assert all("h264_qsv" not in c for c in tried)
