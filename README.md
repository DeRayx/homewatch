# HomeWatch

A home camera project using a Raspberry Pi Zero 2 W and Camera Module 3, inspired by Intellens.

The idea is simple: take a picture every five seconds, check for movement, and send changed images to GPT. If it detects a person while away mode is on, send an email with the picture.

The code and offline tests are in place. Testing on the Pi and checking real email delivery are still to do.

## Parts

- Raspberry Pi Zero 2 W
- Camera Module 3 and a Pi Zero camera cable
- microSD card, power supply, and Wi-Fi
- A mount to keep the camera still

The standard camera needs light to see the room.

## Setup

Install Raspberry Pi OS Lite. Connect the camera with the Pi powered off, then boot and check it:

```sh
sudo apt update
sudo apt install -y python3-picamera2 python3-venv python3-pip
rpicam-still -n -o camera-test.jpg
```

Put the project in `~/homewatch`:

```sh
cd ~/homewatch
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
```

Fill in `.env` with:

- An OpenAI API key and a model that supports images and structured output.
- Your SMTP server, login, sender address, and recipient address.

Use `ssl` with port 465 or `starttls` with port 587, depending on your email provider. Some providers require an app password. Separate multiple recipients with commas. `.env` is ignored by Git. OpenAI API calls are billed separately from ChatGPT.

## Run

Away mode is off by default. Start with a dry run, which makes no API calls and sends no emails:

```sh
.venv/bin/python -m homewatch arm
.venv/bin/python -m homewatch run --dry-run
```

Move in front of the camera and watch the motion percentages in the terminal. Stop with Ctrl+C. To use GPT and email:

```sh
.venv/bin/python -m homewatch run
```

Control away mode from another terminal in the project folder:

```sh
.venv/bin/python -m homewatch status
.venv/bin/python -m homewatch disarm
.venv/bin/python -m homewatch arm
```

Away mode is saved across restarts. `status` shows whether it is armed, not whether the process is running. Disarming stops new snapshots and alerts, but a network request already sent may still finish.

## Motion detection

Comparing every pixel exactly would trigger on small lighting changes and camera noise. Instead, the code shrinks each image to 320 x 240, converts it to grayscale, and applies a blur before comparing.

Defaults in `config.json`:

| Setting | Default |
| --- | --- |
| Capture interval | 5 seconds |
| Pixel brightness difference | 25 out of 255 |
| Changed area needed | 2% |
| Minimum time between GPT calls | 30 seconds |
| Minimum time between emails | 5 minutes |
| Maximum API attempts | 30 per rolling hour |

These values still need tuning on the actual camera.

GPT receives the previous and current images. The first image after arming is checked too, in case someone is already standing still. An email is sent only when GPT reports a person and does not mark the result uncertain. It does not identify who the person is.

Capture runs separately from the network calls. If analysis falls behind, only the newest waiting event is kept. API limits and the last successful email time are saved in `state/`.

## Limits

- Five-second gaps can miss short events. Shadows can trigger motion.
- GPT can get the scene wrong. Uncertain results are logged without an email.
- Failed requests and events skipped by rate limits are dropped. There is no offline queue or automatic retry. Partial email delivery can lead to duplicate alerts later.
- Pictures are kept in memory, not saved as a local archive. Uploaded pictures and emails are subject to the providers' retention policies. `store=False` does not guarantee zero retention.

## Start on boot

Edit the username and paths in `deploy/homewatch.service`, then run:

```sh
sudo cp deploy/homewatch.service /etc/systemd/system/homewatch.service
sudo systemctl daemon-reload
sudo systemctl enable --now homewatch
journalctl -u homewatch -f
```

Stop it with `sudo systemctl stop homewatch`.

## Tests

The tests run on a laptop without a camera or credentials. Use a normal virtual environment:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

They cover motion filtering, API limits, alert decisions, disarming during analysis, and dry runs. To compare two local pictures:

```sh
.venv/bin/python -m homewatch compare --images before.jpg after.jpg
```

## Docs used

- [Raspberry Pi camera setup](https://www.raspberrypi.com/documentation/accessories/camera.html)
- [Picamera2 and camera software](https://www.raspberrypi.com/documentation/computers/camera_software.html)
- [OpenAI image inputs](https://developers.openai.com/api/docs/guides/images-vision)
- [OpenAI structured output](https://developers.openai.com/api/docs/guides/structured-outputs)
