import os
import unittest
from unittest.mock import Mock, patch

from app.model_runtime import B2FitModel, get_fit_model


class FitModelRuntimeTest(unittest.TestCase):
    def tearDown(self):
        get_fit_model.cache_clear()

    def test_frozen_b2_loads_and_predicts_all_four_classes(self):
        model = B2FitModel()
        prediction = model.classify(["Маломерит на размер"])[0]

        self.assertEqual(model.backend, "b2")
        self.assertEqual(prediction.label, "runs_small")
        self.assertEqual(
            set(prediction.probabilities),
            {"no_signal", "runs_large", "runs_small", "true_to_size"},
        )

    def test_backend_defaults_to_b2(self):
        environment = {key: value for key, value in os.environ.items() if key != "FIT_MODEL_BACKEND"}
        with patch.dict(os.environ, environment, clear=True):
            get_fit_model.cache_clear()
            self.assertEqual(get_fit_model().backend, "b2")

    def test_unknown_backend_is_rejected(self):
        with patch.dict(os.environ, {"FIT_MODEL_BACKEND": "unknown"}):
            get_fit_model.cache_clear()
            with self.assertRaisesRegex(RuntimeError, "FIT_MODEL_BACKEND"):
                get_fit_model()

    def test_zero_shot_backend_can_be_selected(self):
        fallback = Mock(backend="zero_shot")
        with (
            patch.dict(os.environ, {"FIT_MODEL_BACKEND": "zero_shot"}),
            patch("app.model_runtime.ZeroShotFitModel", return_value=fallback),
        ):
            get_fit_model.cache_clear()
            self.assertIs(get_fit_model(), fallback)


if __name__ == "__main__":
    unittest.main()
