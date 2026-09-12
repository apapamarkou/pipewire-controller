"""Tests for configuration persistence."""

import json

import pipewire_controller.config as cfg


class TestConfigLoad:
    def test_returns_defaults_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path / "config")
        monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config" / "config.json")
        result = cfg.load()
        assert "presets" in result
        assert "Default" in result["presets"]

    def test_loads_existing_file(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        data = {
            "schema_version": 1,
            "active_preset": "Default",
            "presets": {
                "Default": {
                    "name": "Default",
                    "description": "test",
                    "samplerate": 96000,
                    "quantum": 256,
                    "force_rate": True,
                    "force_quantum": False,
                    "panel_width": 340,
                    "panel_docked": True,
                    "always_on_top": False,
                    "pinned": False,
                    "auto_load": False,
                    "accordion_state": {},
                    "friendly_names": {},
                    "channel_names": {},
                    "meter_mode": "Peak",
                    "master_mode": "Stereo",
                    "master_channel_map": {},
                }
            },
            "window": {"width": 340, "docked": True, "always_on_top": False, "pinned": False},
        }
        config_file.write_text(json.dumps(data))
        monkeypatch.setattr(cfg, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(cfg, "CONFIG_FILE", config_file)
        result = cfg.load()
        assert result["presets"]["Default"]["samplerate"] == 96000

    def test_returns_defaults_on_corrupt_file(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text("not valid json {{{")
        monkeypatch.setattr(cfg, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(cfg, "CONFIG_FILE", config_file)
        result = cfg.load()
        assert "presets" in result

    def test_migrates_v0_config(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        # Old flat format
        old = {"samplerate": 44100, "buffer_size": 256}
        config_file.write_text(json.dumps(old))
        monkeypatch.setattr(cfg, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(cfg, "CONFIG_FILE", config_file)
        result = cfg.load()
        preset = cfg.active_preset(result)
        assert preset["samplerate"] == 44100
        assert preset["quantum"] == 256


class TestConfigSave:
    def test_saves_and_reloads(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "config"
        config_file = config_dir / "config.json"
        monkeypatch.setattr(cfg, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(cfg, "CONFIG_FILE", config_file)
        data = cfg.load()
        data["presets"]["Default"]["samplerate"] = 192000
        assert cfg.save(data) is True
        reloaded = cfg.load()
        assert reloaded["presets"]["Default"]["samplerate"] == 192000


class TestPresetOperations:
    def _base(self):
        return cfg._deep_copy(cfg._DEFAULT_CONFIG)

    def test_get_preset(self):
        config = self._base()
        p = cfg.get_preset(config, "Default")
        assert p is not None
        assert p["name"] == "Default"

    def test_get_missing_preset(self):
        config = self._base()
        assert cfg.get_preset(config, "Nonexistent") is None

    def test_save_preset(self):
        config = self._base()
        preset = cfg._deep_copy(config["presets"]["Default"])
        preset["name"] = "Studio"
        preset["samplerate"] = 88200
        cfg.save_preset(config, preset)
        assert "Studio" in config["presets"]
        assert config["presets"]["Studio"]["samplerate"] == 88200

    def test_delete_preset(self):
        config = self._base()
        preset = cfg._deep_copy(config["presets"]["Default"])
        preset["name"] = "ToDelete"
        cfg.save_preset(config, preset)
        assert cfg.delete_preset(config, "ToDelete") is True
        assert "ToDelete" not in config["presets"]

    def test_cannot_delete_active_preset(self):
        config = self._base()
        assert cfg.delete_preset(config, "Default") is False

    def test_rename_preset(self):
        config = self._base()
        preset = cfg._deep_copy(config["presets"]["Default"])
        preset["name"] = "OldName"
        cfg.save_preset(config, preset)
        assert cfg.rename_preset(config, "OldName", "NewName") is True
        assert "NewName" in config["presets"]
        assert "OldName" not in config["presets"]

    def test_rename_active_preset_updates_active(self):
        config = self._base()
        config["active_preset"] = "Default"
        cfg.rename_preset(config, "Default", "Renamed")
        assert config["active_preset"] == "Renamed"

    def test_rename_to_existing_name_fails(self):
        config = self._base()
        preset = cfg._deep_copy(config["presets"]["Default"])
        preset["name"] = "Second"
        cfg.save_preset(config, preset)
        assert cfg.rename_preset(config, "Default", "Second") is False
