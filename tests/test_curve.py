from asusfancontrol.curve import FanCurve, CurveController


class TestFanCurveInterpolate:
    def test_exact_breakpoint_returns_its_value(self):
        curve = FanCurve([(30, 20), (50, 50), (70, 100)])
        assert curve.interpolate(50) == 50

    def test_interpolates_linearly_between_breakpoints(self):
        curve = FanCurve([(30, 20), (50, 60)])
        assert curve.interpolate(40) == 40

    def test_below_lowest_breakpoint_clamps_to_first_value(self):
        curve = FanCurve([(30, 20), (70, 100)])
        assert curve.interpolate(10) == 20

    def test_above_highest_breakpoint_clamps_to_last_value(self):
        curve = FanCurve([(30, 20), (70, 100)])
        assert curve.interpolate(90) == 100

    def test_unsorted_input_points_are_sorted_by_temp(self):
        curve = FanCurve([(70, 100), (30, 20)])
        assert curve.interpolate(30) == 20
        assert curve.interpolate(70) == 100

    def test_single_point_curve_returns_constant(self):
        curve = FanCurve([(50, 40)])
        assert curve.interpolate(0) == 40
        assert curve.interpolate(100) == 40


class TestCurveControllerFloor:
    def test_result_never_below_minimum_floor(self):
        curve = FanCurve([(30, 0), (70, 10)])
        controller = CurveController(curve, min_floor=20, hysteresis=0, sustain_ticks=1)
        assert controller.next_speed(30) == 20

    def test_result_above_floor_passes_through(self):
        curve = FanCurve([(30, 50)])
        controller = CurveController(curve, min_floor=20, hysteresis=0, sustain_ticks=1)
        assert controller.next_speed(30) == 50


class TestCurveControllerHysteresis:
    def test_first_call_always_applies(self):
        curve = FanCurve([(30, 50)])
        controller = CurveController(curve, min_floor=0, hysteresis=5, sustain_ticks=1)
        assert controller.next_speed(30) == 50

    def test_small_change_within_threshold_is_suppressed(self):
        curve = FanCurve([(30, 50), (31, 53)])
        controller = CurveController(curve, min_floor=0, hysteresis=5, sustain_ticks=1)
        controller.next_speed(30)
        assert controller.next_speed(31) is None

    def test_change_beyond_threshold_applies(self):
        curve = FanCurve([(30, 50), (40, 80)])
        controller = CurveController(curve, min_floor=0, hysteresis=5, sustain_ticks=1)
        controller.next_speed(30)
        assert controller.next_speed(40) == 80

    def test_upward_change_beyond_threshold_applies_immediately_without_sustain(self):
        curve = FanCurve([(30, 20), (40, 80)])
        controller = CurveController(curve, min_floor=0, hysteresis=5, sustain_ticks=3)
        controller.next_speed(30)
        assert controller.next_speed(40) == 80


class TestCurveControllerSustain:
    def test_downward_change_not_applied_until_sustained(self):
        curve = FanCurve([(30, 80), (70, 20)])
        controller = CurveController(curve, min_floor=0, hysteresis=0, sustain_ticks=2)
        controller.next_speed(30)
        assert controller.next_speed(70) is None
        assert controller.next_speed(70) == 20

    def test_downward_sustain_resets_if_temp_bounces_back_up(self):
        curve = FanCurve([(30, 80), (70, 20)])
        controller = CurveController(curve, min_floor=0, hysteresis=0, sustain_ticks=2)
        controller.next_speed(30)
        assert controller.next_speed(70) is None
        assert controller.next_speed(30) is None
        assert controller.next_speed(70) is None
        assert controller.next_speed(70) == 20
