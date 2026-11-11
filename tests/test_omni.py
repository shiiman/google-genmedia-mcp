"""Omni（Gemini Omni / Interactions API）のユニットテスト."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
import requests

from google_genmedia_mcp.core.errors import (
    AuthError,
    GenerationError,
    UnsupportedAuthMethodError,
)
from google_genmedia_mcp.core.models import GenMediaConfig, get_omni_constraints
from google_genmedia_mcp.services.omni import (
    INTERACTIONS_API_REVISION,
    OmniService,
    _media_part,
    _parse_response,
)
from tests.test_services import _make_config

VIDEO_BYTES = b"\x00\x00\x00\x18ftypmp42-fake-video"
VIDEO_B64 = base64.b64encode(VIDEO_BYTES).decode()


def _ok_response(videos: int = 1, text: str | None = "done") -> dict[str, Any]:
    """成功時の Interaction レスポンス（Omni の steps 形式）を生成する."""
    content: list[dict[str, Any]] = [
        {"type": "video", "mime_type": "video/mp4", "data": VIDEO_B64} for _ in range(videos)
    ]
    if text:
        content.append({"type": "text", "text": text})
    return {
        "status": "completed",
        "steps": [
            {"type": "thought"},
            {"type": "model_output", "content": content},
        ],
    }


def _http(status: int = 200, payload: Any = None, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = payload
    resp.text = text
    return resp


def _make_service(
    tmp_path: Path, *, auth_method: str = "vertex_ai"
) -> tuple[OmniService, MagicMock, MagicMock]:
    """OmniService と、モックした client / storage を返す."""
    config = _make_config(auth_method=auth_method)
    client = MagicMock()
    client.has_cloud_credentials = auth_method in ("vertex_ai", "oauth")
    storage = MagicMock()
    counter = {"n": 0}

    def _save(_data: bytes, prefix: str = "video") -> str:
        counter["n"] += 1
        return str(tmp_path / f"{prefix}_{counter['n']}.mp4")

    storage.save_video_from_bytes.side_effect = _save
    return OmniService(client, config, storage), client, storage


class TestOmniConfig:
    """Omni のモデル設定・制約のテスト."""

    def test_default_config(self) -> None:
        cfg = GenMediaConfig().tools.generate_video_omni
        assert cfg.default_model == "Omni"
        assert cfg.request_timeout == 600
        assert [m.id for m in cfg.models] == ["gemini-omni-1.2-flash"]

    @pytest.mark.parametrize("alias", ["Omni", "Omni 1.2", "omni", "gemini-omni-1.2-flash"])
    def test_resolve_alias(self, alias: str) -> None:
        cfg = GenMediaConfig().tools.generate_video_omni
        assert cfg.resolve_model(alias) == "gemini-omni-1.2-flash"
        assert cfg.resolve_model(None) == "gemini-omni-1.2-flash"

    def test_unknown_model_rejected(self) -> None:
        from google_genmedia_mcp.core.errors import ModelNotFoundError

        with pytest.raises(ModelNotFoundError):
            GenMediaConfig().tools.generate_video_omni.resolve_model("unknown")

    def test_constraints_prefix_match(self) -> None:
        c = get_omni_constraints("gemini-omni-1.2-flash")
        assert c is not None
        assert (c.min_duration, c.max_duration) == (3, 15)
        assert get_omni_constraints("veo-3.1-generate-001") is None


class TestOmniValidate:
    """入力契約の検証テスト."""

    def _gen(self, tmp_path: Path, **kwargs: Any) -> Any:
        service, _client, _storage = _make_service(tmp_path)
        with patch.object(service, "_create_interaction", return_value=_ok_response()):
            return service.generate(**kwargs)

    def test_prompt_required_without_task(self, tmp_path: Path) -> None:
        with pytest.raises(GenerationError, match="prompt"):
            self._gen(tmp_path, prompt="  ")

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"sample_count": 0},
            {"sample_count": 4},
            {"temperature": 2.1},
            {"top_p": -0.1},
            {"resolution": "480p"},
            {"aspect_ratio": "1:1"},
            {"duration_seconds": 2},
            {"duration_seconds": 16},
        ],
    )
    def test_invalid_values(self, tmp_path: Path, kwargs: dict[str, Any]) -> None:
        with pytest.raises(GenerationError) as exc:
            self._gen(tmp_path, prompt="p", **kwargs)
        assert exc.value.debug_code == "INVALID_PARAMETER"

    def test_too_many_inputs(self, tmp_path: Path) -> None:
        with pytest.raises(GenerationError, match="images"):
            self._gen(tmp_path, prompt="p", images=["gs://b/a.png"] * 11)
        with pytest.raises(GenerationError, match="videos"):
            self._gen(tmp_path, prompt="p", videos=["gs://b/a.mp4"] * 4)

    def test_unknown_task(self, tmp_path: Path) -> None:
        # 制約テーブルが対応するモデルでは supported_tasks で弾かれる
        with pytest.raises(GenerationError, match="task"):
            self._gen(tmp_path, prompt="p", task="image_to_video")

    @pytest.mark.parametrize("task", ["extend", "upscale"])
    def test_extend_upscale_require_exactly_one_video(self, tmp_path: Path, task: str) -> None:
        prompt = None if task == "upscale" else "続き"
        with pytest.raises(GenerationError, match="1 本"):
            self._gen(tmp_path, prompt=prompt, task=task)
        with pytest.raises(GenerationError, match="1 本"):
            self._gen(tmp_path, prompt=prompt, task=task, videos=["gs://b/1.mp4", "gs://b/2.mp4"])

    @pytest.mark.parametrize("task", ["extend", "upscale"])
    def test_extend_upscale_reject_images_and_format(self, tmp_path: Path, task: str) -> None:
        prompt = None if task == "upscale" else "続き"
        videos = ["gs://b/1.mp4"]
        with pytest.raises(GenerationError, match="images"):
            self._gen(tmp_path, prompt=prompt, task=task, videos=videos, images=["gs://b/a.png"])
        with pytest.raises(GenerationError, match="aspect_ratio"):
            self._gen(tmp_path, prompt=prompt, task=task, videos=videos, aspect_ratio="16:9")
        with pytest.raises(GenerationError, match="duration_seconds"):
            self._gen(tmp_path, prompt=prompt, task=task, videos=videos, duration_seconds=5)

    def test_upscale_rejects_prompt(self, tmp_path: Path) -> None:
        with pytest.raises(GenerationError, match="prompt"):
            self._gen(tmp_path, prompt="x", task="upscale", videos=["gs://b/1.mp4"])

    def test_reference_to_video_contract(self, tmp_path: Path) -> None:
        with pytest.raises(GenerationError, match="prompt"):
            self._gen(tmp_path, task="reference_to_video", images=["gs://b/a.png"])
        with pytest.raises(GenerationError, match="参照画像"):
            self._gen(tmp_path, prompt="p", task="reference_to_video")
        with pytest.raises(GenerationError, match="videos"):
            self._gen(
                tmp_path,
                prompt="p",
                task="reference_to_video",
                images=["gs://b/a.png"],
                videos=["gs://b/1.mp4"],
            )

    def test_api_key_auth_unsupported(self, tmp_path: Path) -> None:
        service, _client, _storage = _make_service(tmp_path, auth_method="api_key")
        with pytest.raises(UnsupportedAuthMethodError):
            service.generate(prompt="p")


class TestOmniBuildRequest:
    """リクエスト構築のテスト."""

    def test_minimal_text_to_video(self, tmp_path: Path) -> None:
        service, client, _storage = _make_service(tmp_path)
        session = client.authorized_session
        session.post.return_value = _http(payload=_ok_response())

        service.generate(prompt="猫が走る")

        _, kwargs = session.post.call_args
        assert session.post.call_args.args[0] == (
            "https://aiplatform.googleapis.com/v1beta1/projects/test-project"
            "/locations/global/interactions"
        )
        assert kwargs["headers"]["Api-Revision"] == INTERACTIONS_API_REVISION
        assert kwargs["headers"]["x-goog-user-project"] == "test-project"
        assert kwargs["timeout"] == 600
        body = kwargs["json"]
        assert body == {
            "model": "gemini-omni-1.2-flash",
            "response_modalities": ["text", "video"],
            "input": [{"type": "user_input", "content": [{"type": "text", "text": "猫が走る"}]}],
            "store": False,
        }

    def test_full_options(self, tmp_path: Path) -> None:
        service, client, _storage = _make_service(tmp_path)
        session = client.authorized_session
        session.post.return_value = _http(payload=_ok_response())

        service.generate(
            prompt="p",
            images=["gs://b/first.png", "gs://b/last.jpg"],
            resolution="720p",
            aspect_ratio="9:16",
            duration_seconds=8,
            temperature=0.5,
            top_p=0.9,
        )

        body = session.post.call_args.kwargs["json"]
        content = body["input"][0]["content"]
        # テキスト → 画像（指定順）の順で並ぶ（最初/最後のフレームは順序で決まる）
        assert [c["type"] for c in content] == ["text", "image", "image"]
        assert content[1] == {"type": "image", "mime_type": "image/png", "uri": "gs://b/first.png"}
        assert content[2]["uri"] == "gs://b/last.jpg"
        assert body["generation_config"] == {"temperature": 0.5, "top_p": 0.9}
        assert body["response_format"] == [
            {"type": "video", "resolution": "720p", "aspect_ratio": "9:16", "duration": "8s"}
        ]

    def test_task_sent_in_video_config(self, tmp_path: Path) -> None:
        service, client, _storage = _make_service(tmp_path)
        session = client.authorized_session
        session.post.return_value = _http(payload=_ok_response())

        service.generate(task="upscale", videos=["gs://b/v.mp4"], resolution="4k")

        body = session.post.call_args.kwargs["json"]
        assert body["generation_config"] == {"video_config": {"task": "upscale"}}
        assert body["input"][0]["content"] == [
            {"type": "video", "mime_type": "video/mp4", "uri": "gs://b/v.mp4"}
        ]
        assert body["response_format"] == [{"type": "video", "resolution": "4k"}]

    def test_request_timeout_from_config(self, tmp_path: Path) -> None:
        service, client, _storage = _make_service(tmp_path)
        service._config.tools.generate_video_omni.request_timeout = 30
        session = client.authorized_session
        session.post.return_value = _http(payload=_ok_response())
        service.generate(prompt="p")
        assert session.post.call_args.kwargs["timeout"] == 30


class TestOmniGenerate:
    """生成フロー全体のテスト."""

    def test_saves_video_and_returns_text(self, tmp_path: Path) -> None:
        service, client, storage = _make_service(tmp_path)
        client.authorized_session.post.return_value = _http(payload=_ok_response())

        result = service.generate(prompt="p", duration_seconds=5)

        storage.save_video_from_bytes.assert_called_once_with(VIDEO_BYTES, "omni")
        assert len(result.videos) == 1
        assert result.videos[0].model == "gemini-omni-1.2-flash"
        assert result.videos[0].duration_seconds == 5.0
        assert result.text == "done"
        assert result.model == "gemini-omni-1.2-flash"

    def test_duration_unknown_when_not_specified(self, tmp_path: Path) -> None:
        service, client, _storage = _make_service(tmp_path)
        client.authorized_session.post.return_value = _http(payload=_ok_response(text=None))
        result = service.generate(prompt="p")
        assert result.videos[0].duration_seconds is None
        assert result.text is None

    def test_sample_count_calls_sequentially(self, tmp_path: Path) -> None:
        service, client, storage = _make_service(tmp_path)
        session = client.authorized_session
        session.post.return_value = _http(payload=_ok_response())

        result = service.generate(prompt="p", sample_count=3)

        assert session.post.call_count == 3
        assert storage.save_video_from_bytes.call_count == 3
        assert len(result.videos) == 3
        assert result.text == "done\ndone\ndone"

    def test_sample_failure_reports_index(self, tmp_path: Path) -> None:
        service, client, _storage = _make_service(tmp_path)
        client.authorized_session.post.side_effect = [
            _http(payload=_ok_response()),
            _http(status=500, text="boom"),
        ]
        with pytest.raises(GenerationError, match=r"2/2") as exc:
            service.generate(prompt="p", sample_count=2)
        assert exc.value.debug_code == "OMNI_API_ERROR"

    def test_http_error_includes_body_and_hint(self, tmp_path: Path) -> None:
        service, client, _storage = _make_service(tmp_path)
        client.authorized_session.post.return_value = _http(status=404, text="model not found")
        with pytest.raises(GenerationError) as exc:
            service.generate(prompt="p")
        assert "404" in exc.value.user_message
        assert "model not found" in exc.value.user_message
        assert "global" in exc.value.hint

    def test_long_error_body_truncated(self, tmp_path: Path) -> None:
        service, client, _storage = _make_service(tmp_path)
        client.authorized_session.post.return_value = _http(status=400, text="x" * 10000)
        with pytest.raises(GenerationError) as exc:
            service.generate(prompt="p")
        assert len(exc.value.user_message) < 2500

    def test_timeout(self, tmp_path: Path) -> None:
        service, client, _storage = _make_service(tmp_path)
        client.authorized_session.post.side_effect = requests.exceptions.ReadTimeout()
        with pytest.raises(GenerationError) as exc:
            service.generate(prompt="p")
        assert exc.value.debug_code == "OMNI_TIMEOUT"

    def test_connection_error_wrapped(self, tmp_path: Path) -> None:
        service, client, _storage = _make_service(tmp_path)
        client.authorized_session.post.side_effect = requests.exceptions.ConnectionError("dns")
        with pytest.raises(GenerationError) as exc:
            service.generate(prompt="p")
        assert exc.value.debug_code == "OMNI_REQUEST_ERROR"

    def test_auth_error_propagates(self, tmp_path: Path) -> None:
        service, client, _storage = _make_service(tmp_path)
        type(client).authorized_session = PropertyMock(side_effect=AuthError("no creds"))
        with pytest.raises(AuthError):
            service.generate(prompt="p")

    def test_non_json_response(self, tmp_path: Path) -> None:
        service, client, _storage = _make_service(tmp_path)
        resp = _http()
        resp.json.side_effect = ValueError("bad json")
        client.authorized_session.post.return_value = resp
        with pytest.raises(GenerationError) as exc:
            service.generate(prompt="p")
        assert exc.value.debug_code == "OMNI_INVALID_RESPONSE"

    def test_missing_project(self, tmp_path: Path) -> None:
        service, _client, _storage = _make_service(tmp_path)
        service._config.auth.vertex_ai.project = ""
        with pytest.raises(GenerationError) as exc:
            service.generate(prompt="p")
        assert exc.value.debug_code == "AUTH_NO_PROJECT"


class TestParseResponse:
    """レスポンス解析のテスト."""

    def test_nested_steps(self) -> None:
        videos, text = _parse_response(_ok_response(videos=2))
        assert videos == [VIDEO_BYTES, VIDEO_BYTES]
        assert text == "done"

    def test_flat_outputs_fallback(self) -> None:
        resp = {
            "status": "completed",
            "outputs": [{"type": "video", "mime_type": "video/mp4", "data": VIDEO_B64}],
        }
        videos, text = _parse_response(resp)
        assert videos == [VIDEO_BYTES]
        assert text == ""

    def test_video_detected_by_mime_type_only(self) -> None:
        resp = {"steps": [{"content": [{"mime_type": "video/webm", "data": VIDEO_B64}]}]}
        videos, _ = _parse_response(resp)
        assert videos == [VIDEO_BYTES]

    def test_thought_steps_ignored(self) -> None:
        resp = _ok_response()
        resp["steps"].insert(0, {"type": "thought", "text": "考え中"})
        _, text = _parse_response(resp)
        assert text == "done"

    def test_no_video(self) -> None:
        with pytest.raises(GenerationError) as exc:
            _parse_response({"status": "completed", "steps": []})
        assert exc.value.debug_code == "OMNI_NO_VIDEO"

    def test_invalid_base64(self) -> None:
        resp = {"steps": [{"content": [{"type": "video", "data": "!!!not-base64"}]}]}
        with pytest.raises(GenerationError) as exc:
            _parse_response(resp)
        assert exc.value.debug_code == "OMNI_INVALID_RESPONSE"

    def test_failed_status_with_errors(self) -> None:
        resp = {
            "status": "failed",
            "errors": [{"message": "unsafe prompt", "code": "invalid_request"}],
        }
        with pytest.raises(GenerationError) as exc:
            _parse_response(resp)
        assert "unsafe prompt" in exc.value.user_message
        assert "invalid_request" in exc.value.user_message
        assert "failed" in exc.value.user_message

    def test_failed_status_without_details(self) -> None:
        with pytest.raises(GenerationError, match="cancelled"):
            _parse_response({"status": "cancelled"})

    def test_singular_error_is_fatal_even_if_completed(self) -> None:
        resp = _ok_response()
        resp["error"] = {"message": "quota", "code": 429}
        with pytest.raises(GenerationError, match="quota"):
            _parse_response(resp)

    def test_plural_errors_diagnostic_when_completed(self) -> None:
        resp = _ok_response()
        resp["errors"] = [{"message": "minor warning"}]
        videos, _ = _parse_response(resp)
        assert videos == [VIDEO_BYTES]


class TestMediaPart:
    """入力メディア Part 生成のテスト."""

    def test_gcs_image(self) -> None:
        assert _media_part("image", "gs://b/x.WEBP") == {
            "type": "image",
            "mime_type": "image/webp",
            "uri": "gs://b/x.WEBP",
        }

    def test_gcs_video_default_mime(self) -> None:
        assert _media_part("video", "gs://b/x")["mime_type"] == "video/mp4"
        assert _media_part("video", "gs://b/x.mov")["mime_type"] == "video/quicktime"

    def test_local_file_inline(self, tmp_path: Path) -> None:
        f = tmp_path / "a.png"
        f.write_bytes(b"png-bytes")
        part = _media_part("image", str(f))
        assert part["mime_type"] == "image/png"
        assert base64.b64decode(part["data"]) == b"png-bytes"
        assert "uri" not in part

    def test_local_file_missing(self, tmp_path: Path) -> None:
        with pytest.raises(GenerationError) as exc:
            _media_part("image", str(tmp_path / "none.png"))
        assert exc.value.debug_code == "FILE_NOT_FOUND"

    def test_local_file_too_large(self, tmp_path: Path) -> None:
        f = tmp_path / "big.mp4"
        f.write_bytes(b"0")
        with (
            patch("google_genmedia_mcp.services.omni.MAX_INLINE_BYTES", 0),
            pytest.raises(GenerationError) as exc,
        ):
            _media_part("video", str(f))
        assert exc.value.debug_code == "FILE_TOO_LARGE"

    def test_invalid_input_fails_before_api_call(self, tmp_path: Path) -> None:
        service, client, _storage = _make_service(tmp_path)
        with pytest.raises(GenerationError):
            service.generate(prompt="p", images=[str(tmp_path / "missing.png")])
        client.authorized_session.post.assert_not_called()
