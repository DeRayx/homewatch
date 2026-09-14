import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import queue
import threading

from PIL import Image, ImageDraw
from homewatch.app import Budget, Config, Assessment, motion_fraction, worker


class MotionTests(unittest.TestCase):
    def test_noise_ignored(self):
        self.assertEqual(motion_fraction(Image.new('RGB', (320, 240), (80, 80, 80)),
                                         Image.new('RGB', (320, 240), (84, 84, 84)), 25), 0)

    def test_object_detected(self):
        before = Image.new('RGB', (320, 240))
        after = before.copy()
        ImageDraw.Draw(after).rectangle((70, 50, 170, 200), fill='white')
        self.assertGreater(motion_fraction(before, after, 25), .02)

    def test_budget_persists_and_recovers(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'budget.json'
            budget = Budget(path, 2, 30)
            self.assertTrue(budget.reserve(100))
            self.assertFalse(budget.reserve(110))
            self.assertTrue(budget.reserve(140))
            self.assertFalse(Budget(path, 2, 30).reserve(180))
            self.assertTrue(budget.reserve(3800))

    def check_worker(self, assessment, dry=False, disarm=False):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder)
            (state / 'armed').write_text('generation')
            events, stop = queue.Queue(), threading.Event()
            events.put((b'before', b'after', 'timestamp', 'generation'))
            def analyze(*args):
                if disarm:
                    (state / 'armed').unlink()
                return assessment
            with patch('homewatch.app.analyze', side_effect=analyze) as analysis, \
                 patch('homewatch.app.send_email') as email, \
                 patch('openai.OpenAI'), patch.dict('os.environ', {'OPENAI_MODEL': 'test-model'}):
                thread = threading.Thread(target=worker, args=(events, stop, Config(), state, dry))
                thread.start()
                events.join()
                stop.set()
                thread.join(timeout=3)
                self.assertFalse(thread.is_alive())
                return analysis.call_count, email.call_count

    def test_person_alert(self):
        self.assertEqual(self.check_worker(Assessment(person_present=True, uncertain=False, explanation='Person visible')), (1, 1))

    def test_uncertain_no_email(self):
        self.assertEqual(self.check_worker(Assessment(person_present=True, uncertain=True, explanation='Obscured')), (1, 0))

    def test_disarm_during_analysis(self):
        self.assertEqual(self.check_worker(Assessment(person_present=True, uncertain=False, explanation='Person'), disarm=True), (1, 0))

    def test_dry_run_has_no_network(self):
        self.assertEqual(self.check_worker(None, dry=True), (0, 0))


if __name__ == '__main__':
    unittest.main()
