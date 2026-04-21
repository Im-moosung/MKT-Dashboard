from importlib import reload

import pytest

import New_Data_flow.common.secret_manager as secret_manager


def test_secret_manager_module_is_importable_without_package(monkeypatch):
    monkeypatch.setattr(secret_manager, "secretmanager", None)

    with pytest.raises(ModuleNotFoundError):
        secret_manager.build_secret_manager_client()


def test_access_secret_dict_not_needed_for_env_only_runtime():
    reloaded = reload(secret_manager)
    assert hasattr(reloaded, "access_secret_dict")
