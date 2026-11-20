# -*- coding: utf-8 -*-
"""Run real gevent socket tests in isolation from Django's synchronous runner."""
import os
from pathlib import Path
import subprocess
import sys
from unittest import TestCase


class AIEngineWSGILifecycleTests(TestCase):
    # capability_id: console.ai-engine.downstream-cancellation
    def test_real_downstream_disconnect_cancels_silent_upstream(self):
        repo = Path(__file__).resolve().parents[2]
        env = dict(os.environ, DJANGO_SETTINGS_MODULE="goodrain_web.test_settings")
        result = subprocess.run([sys.executable, str(repo / "console/tests/fixtures/ai_engine_wsgi_probe.py")],
                                cwd=repo,
                                env=env,
                                text=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("all downstream lifecycle checks passed", result.stdout)

    def test_real_disconnect_before_upstream_headers(self):
        repo = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            [sys.executable, str(repo / "console/tests/fixtures/ai_engine_wsgi_probe.py"), "preheaders"],
            cwd=repo,
            env=dict(os.environ, DJANGO_SETTINGS_MODULE="goodrain_web.test_settings"),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=35)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("all pre-header lifecycle checks passed", result.stdout)
