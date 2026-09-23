from asusfancontrol.ui.main_window import MAX_FAN_RPM, estimate_pct_from_rpm


class TestEstimatePctFromRpm:
    def test_zero_rpm_is_zero_percent(self):
        assert estimate_pct_from_rpm(0) == 0

    def test_max_rpm_is_full_percent(self):
        assert estimate_pct_from_rpm(MAX_FAN_RPM) == 100

    def test_half_max_rpm_is_half_percent(self):
        assert estimate_pct_from_rpm(MAX_FAN_RPM // 2) == 50

    def test_rpm_above_max_clamps_to_100(self):
        assert estimate_pct_from_rpm(MAX_FAN_RPM * 2) == 100
