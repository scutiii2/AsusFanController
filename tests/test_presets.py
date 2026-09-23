from asusfancontrol.presets import builtin_presets


class TestBuiltinPresets:
    def test_returns_four_named_levels(self):
        presets = builtin_presets(fan_count=2)
        assert [p.name for p in presets] == ["Silent", "Balanced", "Performance", "Turbo"]

    def test_all_builtin_presets_are_flagged_builtin(self):
        presets = builtin_presets(fan_count=2)
        assert all(p.builtin for p in presets)

    def test_speeds_cover_every_fan_id(self):
        presets = builtin_presets(fan_count=3)
        for preset in presets:
            assert set(preset.speeds) == {0, 1, 2}

    def test_zero_fan_count_yields_empty_speeds(self):
        presets = builtin_presets(fan_count=0)
        assert all(p.speeds == {} for p in presets)

    def test_turbo_is_full_speed_on_every_fan(self):
        presets = builtin_presets(fan_count=2)
        turbo = next(p for p in presets if p.name == "Turbo")
        assert all(pct == 100 for pct in turbo.speeds.values())
