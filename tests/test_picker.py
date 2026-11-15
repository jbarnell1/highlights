import json

import pytest

from highlights import picker


def test_parse_structured_output():
    out = json.dumps({"is_error": False, "structured_output": {
        "clips": [{"ref": "V1", "start": 1, "duration": 4, "why": "x"}], "photos": [], "notes": "n"}})
    picks = picker.parse_cli_output(out)
    assert picks.clips[0].ref == "V1"


def test_parse_falls_back_to_fenced_result_text():
    body = {"clips": [], "photos": [{"ref": "P3", "why": "y"}], "notes": "n"}
    out = json.dumps({"is_error": False, "result": "```json\n" + json.dumps(body) + "\n```"})
    assert picker.parse_cli_output(out).photos[0].ref == "P3"


def test_not_logged_in_explains_the_fix():
    out = json.dumps({"is_error": True, "result": "Not logged in · Please run /login"})
    with pytest.raises(RuntimeError, match="setup-token"):
        picker.parse_cli_output(out)


def test_garbage_output_is_reported():
    with pytest.raises(RuntimeError, match="didn't answer"):
        picker.parse_cli_output("", "boom")


def test_prompt_writes_every_sheet(tmp_path):
    content = picker.build_content(
        "Trip", 60, [picker.SheetVideo("V1", "a", 30, b"\xff\xd8jpeg")],
        [picker.SheetPhotos([("P1", "b")], b"\xff\xd8jpeg2")])
    prompt = picker.ClaudeCode._prompt(content, tmp_path)
    sheets = sorted(tmp_path.glob("sheet-*.jpg"))
    assert len(sheets) == 2 and all(f"./{s.name}" in prompt for s in sheets)
    assert "V1: video, 30 seconds long" in prompt


def test_target_seconds_bounds():
    assert picker.target_seconds(0, 10) == 45
    assert picker.target_seconds(5000, 43) == 300


def test_child_env_drops_app_settings_and_secrets():
    env = picker.child_env({
        "PATH": "/usr/bin", "HOME": "/home/highlights", "LANG": "C.UTF-8",
        "IMMICH_API_KEY": "k", "IMMICH_URL": "http://immich", "HL_DATA_DIR": "/data",
        "ANTHROPIC_API_KEY": "sk", "ANTHROPIC_AUTH_TOKEN": "t", "CLAUDE_CODE_OAUTH_TOKEN": "old",
        "SOME_PASSWORD": "p", "DISABLE_AUTOUPDATER": "1",
    })
    assert env == {"PATH": "/usr/bin", "HOME": "/home/highlights", "LANG": "C.UTF-8",
                   "DISABLE_AUTOUPDATER": "1"}


def test_read_is_scoped_to_the_working_folder():
    assert picker.ALLOWED == "Read(./**)"
    assert "Glob" in picker.DISALLOWED and "Bash" in picker.DISALLOWED
