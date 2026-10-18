# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Tests for inline format keyboards."""

import pytest

from tg_bot_ytdl.extractor import VideoFormat
from tg_bot_ytdl.keyboards import (
    CALLBACK_PREFIX,
    MAX_FORMAT_BUTTONS,
    MENU_DOWNLOAD,
    MENU_HELP,
    MENU_SUBSCRIPTIONS,
    MORE_BUTTON_TEXT,
    MORE_CALLBACK_PREFIX,
    SECTION_CALLBACK_PREFIX,
    SUBSCRIPTION_CALLBACK_PREFIX,
    SUBSCRIPTION_DELETE_PREFIX,
    VIDEO_CALLBACK_PREFIX,
    build_channel_sections_keyboard,
    build_formats_keyboard,
    build_main_menu_keyboard,
    build_more_keyboard,
    build_subscription_actions_keyboard,
    build_subscriptions_keyboard,
    build_video_keyboard,
    channel_button_label,
    format_button_label,
    format_filesize,
    select_formats,
)


def _fmt(
    format_id: str = "137",
    ext: str = "mp4",
    resolution: str | None = "1280x720",
    filesize: int | None = None,
    note: str | None = None,
    height: int | None = 720,
    has_video: bool = True,
    has_audio: bool = True,
) -> VideoFormat:
    return VideoFormat(
        format_id=format_id,
        ext=ext,
        resolution=resolution,
        filesize=filesize,
        note=note,
        height=height,
        has_video=has_video,
        has_audio=has_audio,
    )


def test_build_returns_none_for_empty() -> None:
    assert build_formats_keyboard([]) is None


def test_build_creates_button_per_format() -> None:
    markup = build_formats_keyboard([_fmt("137"), _fmt("22")])
    assert markup is not None
    assert len(markup.inline_keyboard) == 2


def test_button_callback_data_has_prefix() -> None:
    markup = build_formats_keyboard([_fmt("137")])
    assert markup is not None
    button = markup.inline_keyboard[0][0]
    assert button.callback_data == f"{CALLBACK_PREFIX}137"


def test_build_limits_button_count() -> None:
    formats = [_fmt(format_id=str(i)) for i in range(MAX_FORMAT_BUTTONS + 5)]
    markup = build_formats_keyboard(formats)
    assert markup is not None
    assert len(markup.inline_keyboard) == MAX_FORMAT_BUTTONS


def test_button_label_includes_resolution_ext_and_size() -> None:
    label = format_button_label(_fmt(filesize=5 * 1024 * 1024))
    assert "1280x720" in label
    assert "mp4" in label
    assert "5.0 MB" in label


def test_button_label_falls_back_to_note() -> None:
    label = format_button_label(_fmt(resolution=None, note="audio only"))
    assert label.startswith("audio only")


@pytest.mark.parametrize(
    ("size", "expected"),
    [(None, ""), (0, ""), (512 * 1024, "512 KB"), (2 * 1024 * 1024, "2.0 MB")],
)
def test_format_filesize(size: int | None, expected: str) -> None:
    assert format_filesize(size) == expected


def test_select_formats_drops_storyboards() -> None:
    storyboard = _fmt("sb0", ext="mhtml", has_video=False, has_audio=False)
    selected = select_formats([storyboard, _fmt()])
    assert [fmt.format_id for fmt in selected] == ["137", "mp3"]


def test_select_formats_deduplicates_same_quality() -> None:
    small = _fmt("137", filesize=1000)
    large = _fmt("399", filesize=2000)
    selected = select_formats([small, large])
    assert [fmt.format_id for fmt in selected] == ["399", "mp3"]


def test_select_formats_orders_video_before_audio() -> None:
    audio = _fmt(
        "140", ext="m4a", resolution="audio only", height=None, has_video=False
    )
    video = _fmt("137", height=1080, resolution="1920x1080")
    selected = select_formats([audio, video])
    assert [fmt.format_id for fmt in selected] == ["137", "mp3"]
    assert selected[-1].ext == "mp3"


def test_select_formats_offers_only_mp4_video_and_mp3_audio() -> None:
    webm = _fmt("248", ext="webm", height=1080, resolution="1920x1080")
    m4a = _fmt("140", ext="m4a", resolution="audio only", height=None, has_video=False)
    mp4 = _fmt("137", height=1080, resolution="1920x1080")
    selected = select_formats([webm, m4a, mp4])
    assert [fmt.format_id for fmt in selected] == ["137", "mp3"]


def test_select_formats_adds_audio_option_without_video() -> None:
    m4a = _fmt("140", ext="m4a", resolution="audio only", height=None, has_video=False)
    selected = select_formats([m4a])
    assert [fmt.format_id for fmt in selected] == ["mp3"]


def test_select_formats_limits_to_max() -> None:
    formats = [_fmt(str(i), height=i + 1, resolution=f"{i + 1}p") for i in range(30)]
    assert len(select_formats(formats)) == MAX_FORMAT_BUTTONS


def test_label_marks_audio_only() -> None:
    label = format_button_label(
        _fmt(
            "140",
            ext="m4a",
            resolution="audio only",
            height=None,
            has_video=False,
            note="medium",
        )
    )
    assert label.startswith("аудио medium")


def test_main_menu_keyboard_has_three_buttons() -> None:
    markup = build_main_menu_keyboard()
    buttons = [button.text for row in markup.keyboard for button in row]
    assert buttons == [MENU_DOWNLOAD, MENU_SUBSCRIPTIONS, MENU_HELP]


def test_subscriptions_keyboard_returns_none_for_empty() -> None:
    assert build_subscriptions_keyboard([]) is None


def test_subscriptions_keyboard_uses_ids_in_callback() -> None:
    markup = build_subscriptions_keyboard([(5, "NASA"), (7, "ESA")])
    assert markup is not None
    assert len(markup.inline_keyboard) == 2
    assert (
        markup.inline_keyboard[0][0].callback_data == f"{SUBSCRIPTION_CALLBACK_PREFIX}5"
    )
    assert (
        markup.inline_keyboard[1][0].callback_data == f"{SUBSCRIPTION_CALLBACK_PREFIX}7"
    )


def test_actions_keyboard_deletes_subscription() -> None:
    markup = build_subscription_actions_keyboard(3)
    assert (
        markup.inline_keyboard[0][0].callback_data == f"{SUBSCRIPTION_DELETE_PREFIX}3"
    )


def test_channel_button_label_truncates() -> None:
    assert channel_button_label("  NASA   TV ") == "NASA TV"
    assert channel_button_label("") == "Канал"
    assert len(channel_button_label("x" * 100)) == 40


def test_sections_keyboard_has_sections_and_delete() -> None:
    markup = build_channel_sections_keyboard(4)
    rows = markup.inline_keyboard

    assert len(rows) == 4
    assert rows[0][0].callback_data == f"{SECTION_CALLBACK_PREFIX}4:videos"
    assert rows[1][0].callback_data == f"{SECTION_CALLBACK_PREFIX}4:shorts"
    assert rows[2][0].callback_data == f"{SECTION_CALLBACK_PREFIX}4:streams"
    assert rows[3][0].callback_data == f"{SUBSCRIPTION_DELETE_PREFIX}4"


def test_video_keyboard_has_download_button() -> None:
    markup = build_video_keyboard("dQw4w9WgXcQ")

    assert (
        markup.inline_keyboard[0][0].callback_data
        == f"{VIDEO_CALLBACK_PREFIX}dQw4w9WgXcQ"
    )


def test_more_keyboard_has_more_button() -> None:
    markup = build_more_keyboard(4, "videos", 5)
    button = markup.inline_keyboard[0][0]

    assert button.text == MORE_BUTTON_TEXT
    assert button.callback_data == f"{MORE_CALLBACK_PREFIX}4:videos:5"
