from app.services.media_volume import commit_media_volume, configure_media_volume


def test_media_volume_commit_is_noop_when_not_running_on_modal():
    configure_media_volume()
    commit_media_volume()


def test_media_volume_commit_calls_injected_modal_callback():
    calls = []
    configure_media_volume(commit=lambda: calls.append("commit"))
    commit_media_volume()
    assert calls == ["commit"]
    configure_media_volume()
