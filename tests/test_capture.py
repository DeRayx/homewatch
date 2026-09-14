import io
import subprocess
import unittest
from unittest.mock import patch, MagicMock

from PIL import Image
from homewatch.capture import take_photo
from homewatch.app import analyze, Assessment, send_email


class CaptureTests(unittest.TestCase):
    def test_jpeg_capture(self):
        output = io.BytesIO()
        Image.new('RGB', (80, 60), 'red').save(output, 'JPEG')
        with patch('homewatch.capture.subprocess.run') as run:
            run.return_value.stdout = output.getvalue()
            image = take_photo(1000)
        self.assertEqual(image.size, (80, 60))
        self.assertEqual(image.mode, 'RGB')
        args = run.call_args.args[0]
        self.assertEqual(args[0], 'rpicam-still')
        self.assertEqual(args[args.index('-o') + 1], '-')
        self.assertEqual(args[args.index('--timeout') + 1], '1000')
        self.assertTrue(run.call_args.kwargs['check'])
        self.assertGreater(run.call_args.kwargs['timeout'], 1)

    def test_camera_failure(self):
        with patch('homewatch.capture.subprocess.run', side_effect=subprocess.CalledProcessError(1, ['rpicam-still'])):
            with self.assertRaisesRegex(RuntimeError, 'rpicam-still failed'):
                take_photo()

    def test_camera_timeout(self):
        with patch('homewatch.capture.subprocess.run', side_effect=subprocess.TimeoutExpired('rpicam-still', 11)):
            with self.assertRaisesRegex(RuntimeError, 'timed out'):
                take_photo()

    def test_two_images_sent_for_analysis(self):
        client = MagicMock()
        expected = Assessment(person_present=True, uncertain=False, explanation='A person is at the door.')
        client.responses.parse.return_value.output_parsed = expected
        self.assertEqual(analyze(client, 'test-model', b'before', b'after'), expected)
        request = client.responses.parse.call_args.kwargs
        images = request['input'][0]['content'][1:]
        self.assertEqual(len(images), 2)
        self.assertEqual(images[1]['image_url'], 'data:image/jpeg;base64,YWZ0ZXI=')
        self.assertFalse(request['store'])

    def test_gmail_self_delivery_with_attachment(self):
        env = {'SMTP_HOST':'smtp.gmail.com', 'SMTP_PORT':'465', 'SMTP_SECURITY':'ssl',
               'SMTP_USER':'example@gmail.com', 'SMTP_PASSWORD':'test-only',
               'EMAIL_FROM':'example@gmail.com', 'EMAIL_TO':'example@gmail.com'}
        with patch.dict('os.environ', env), patch('homewatch.app.smtplib.SMTP_SSL') as smtp:
            connection = smtp.return_value
            connection.send_message.return_value = {}
            send_email(b'jpeg-data', 'test timestamp', Assessment(person_present=True, uncertain=False, explanation='A person is at the door.'))
            message = connection.send_message.call_args.args[0]
            self.assertEqual(message['From'], message['To'])
            self.assertIn('A person is at the door.', message.get_body().get_content())
            self.assertEqual(next(message.iter_attachments()).get_payload(decode=True), b'jpeg-data')
            connection.login.assert_called_once_with('example@gmail.com', 'test-only')
