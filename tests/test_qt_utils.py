from PySide6.QtCore import QObject

from asusfancontrol.ui.qt_utils import block_signals


class TestBlockSignals:
    def test_blocks_signals_during_the_with_block(self, qtbot):
        obj = QObject()
        with block_signals(obj):
            assert obj.signalsBlocked() is True

    def test_restores_unblocked_state_after_the_with_block(self, qtbot):
        obj = QObject()
        with block_signals(obj):
            pass
        assert obj.signalsBlocked() is False

    def test_always_unblocks_on_exit_matching_the_original_inline_pattern(self, qtbot):
        # Mirrors the blockSignals(True)/.../blockSignals(False) pattern this
        # replaced: it always unblocks on exit rather than restoring whatever
        # blocked state existed before entry (no caller in this codebase
        # nests these, so that distinction has never mattered in practice).
        obj = QObject()
        obj.blockSignals(True)
        with block_signals(obj):
            pass
        assert obj.signalsBlocked() is False

    def test_unblocks_even_if_the_body_raises(self, qtbot):
        obj = QObject()
        try:
            with block_signals(obj):
                raise ValueError("boom")
        except ValueError:
            pass
        assert obj.signalsBlocked() is False
