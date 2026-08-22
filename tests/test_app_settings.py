import sys

from PyQt6.QtCore import QSettings

from infrastructure.app_settings import create_user_settings


def test_user_settings_use_platform_native_storage():
    settings = create_user_settings()

    assert settings.format() == QSettings.Format.NativeFormat
    assert settings.scope() == QSettings.Scope.UserScope
    if sys.platform == "win32":
        assert "HKEY_CURRENT_USER" in settings.fileName()
    elif sys.platform.startswith("linux"):
        assert settings.fileName().endswith("GeoShelter/GeoShelter.conf")
