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
        controller = CurveController(curve, min_floor=0, hysteresis=0, sustain_ticks=2, max_step_down=10)
        controller.next_speed(30)
        assert controller.next_speed(70) is None
        # sustained now, but a 60-point drop eases in <=10-point steps
        # rather than jumping straight to the target
        assert controller.next_speed(70) == 70

    def test_downward_sustain_resets_if_temp_bounces_back_up_before_sustained(self):
        curve = FanCurve([(30, 80), (70, 20)])
        controller = CurveController(curve, min_floor=0, hysteresis=0, sustain_ticks=2, max_step_down=10)
        controller.next_speed(30)
        assert controller.next_speed(70) is None
        assert controller.next_speed(30) is None
        assert controller.next_speed(70) is None
        assert controller.next_speed(70) == 70


class TestCurveControllerEasingDown:
    def test_sudden_drop_glides_down_in_max_step_down_increments(self):
        curve = FanCurve([(30, 90), (70, 20)])
        controller = CurveController(curve, min_floor=0, hysteresis=0, sustain_ticks=1, max_step_down=10)
        controller.next_speed(30)  # establishes last_applied = 90
        # sustain_ticks=1, so the very next low reading starts easing
        assert controller.next_speed(70) == 80
        assert controller.next_speed(70) == 70
        assert controller.next_speed(70) == 60
        assert controller.next_speed(70) == 50
        assert controller.next_speed(70) == 40
        assert controller.next_speed(70) == 30
        assert controller.next_speed(70) == 20
        # reached the target: stays there, no further change emitted
        assert controller.next_speed(70) is None

    def test_glide_continues_without_resustaining_each_step(self):
        curve = FanCurve([(30, 90), (70, 20)])
        controller = CurveController(curve, min_floor=0, hysteresis=0, sustain_ticks=3, max_step_down=10)
        controller.next_speed(30)  # last_applied = 90
        assert controller.next_speed(70) is None  # sustain count 1
        assert controller.next_speed(70) is None  # sustain count 2
        assert controller.next_speed(70) == 80  # sustain count 3: easing starts
        # no re-sustaining needed for subsequent steps of the same glide
        assert controller.next_speed(70) == 70
        assert controller.next_speed(70) == 60

    def test_small_total_drop_completes_in_one_step_once_sustained(self):
        curve = FanCurve([(30, 50), (70, 45)])
        controller = CurveController(curve, min_floor=0, hysteresis=0, sustain_ticks=1, max_step_down=10)
        controller.next_speed(30)  # last_applied = 50
        assert controller.next_speed(70) == 45

    def test_rising_temp_cancels_the_glide_and_responds_immediately(self):
        curve = FanCurve([(30, 90), (50, 20), (70, 90)])
        controller = CurveController(curve, min_floor=0, hysteresis=0, sustain_ticks=1, max_step_down=10)
        controller.next_speed(30)  # last_applied = 90
        assert controller.next_speed(50) == 80  # easing down begins
        assert controller.next_speed(50) == 70  # still easing
        # temp jumps back up mid-glide: respond immediately, don't keep easing
        assert controller.next_speed(70) == 90
