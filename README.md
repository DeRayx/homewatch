# HomeWatch

A separate hobby surveillance project inspired by Intellens. Raspberry Pi Zero 2 W + Camera Module 3 → capture every five seconds → local motion filtering → GPT image assessment → email when a person is visible while away mode is enabled.

## Hardware

- Raspberry Pi Zero 2 W, microSD card, stable power supply, Wi-Fi.
- Camera Module 3 and the **standard-to-mini / Pi Zero camera cable**.
- A stable mount and suitable enclosure. The standard Module 3 needs visible light; dark-room operation requires an appropriate lighting/camera setup.

## Raspberry Pi installation

Use a current Raspberry Pi OS Lite image. Connect the camera with power disconnected, then boot and verify it:

```sh
sudo apt update
sudo apt install -y python3-picamera2 python3-venv python3-pip
rpicam-still -n -o camera-test.jpg
```

Copy this project to `~/homewatch`, then:

```sh
cd ~/homewatch
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
```

Edit `.env` locally. Supply an OpenAI API key and a model available to your API project that accepts image inputs and structured outputs. API usage has its own billing. Configure your email provider's SMTP host, credentials (often an app password), sender, and recipient. Multiple recipients may be comma-separated. Use `SMTP_SECURITY=ssl` with port 465, or `starttls` with port 587 as supported by your provider. Never commit `.env`.

## First run

The project starts **disarmed**. Test motion on the Pi without uploads or emails:

```sh
.venv/bin/python -m homewatch arm
.venv/bin/python -m homewatch run --dry-run
```

Move through the scene and inspect the changed-pixel percentage. Stop with Ctrl+C. Once credentials and thresholds are configured, run live:

```sh
.venv/bin/python -m homewatch run
```

From another terminal in the same project:

```sh
.venv/bin/python -m homewatch status
.venv/bin/python -m homewatch disarm
.venv/bin/python -m homewatch arm
```

Away mode persists across restarts. Disarming stops new event processing; requests already in flight cannot be recalled. The camera remains initialized, but the application does not request snapshots while disarmed. `status` reports away mode, not service health.

## Behavior and tuning

`config.json` controls the interval, pixel threshold (0–255 scale), minimum changed fraction, analysis/email cooldowns, and rolling hourly API limit. Defaults: five seconds, 25 brightness levels, 2% changed pixels, 30 seconds between analyses, five minutes between emails, 30 API attempts/hour. Tune using your actual scene; these are starting values, not calibrated detection guarantees.

Images are reduced to 320×240 grayscale and blurred for comparison. Meaningful changes enqueue the previous and current JPEGs. The first capture after arming is also assessed, so an already-still person can be detected. The background worker keeps camera capture independent of API/SMTP latency. Only the latest waiting event is retained; overload replaces stale waiting images. Events suppressed by cooldown or budget are dropped.

GPT reports person presence, uncertainty, and visible evidence using structured output. Code sends email only for `person_present=true` and `uncertain=false`, while the same away session remains active. It does not identify people or infer criminal intent. The email includes the event image and a UTC capture timestamp. An uncertain result is logged and does not send email.

API attempts and successful email timestamps persist in `state/`, including across restarts. No automatic API retries are used. API/SMTP errors are logged and the event is dropped; later motion can trigger another attempt. There is no offline backlog or guaranteed delivery. A partially accepted SMTP message can result in duplicates on a subsequent event. A process lock prevents two local capture processes sharing this state directory.

Images stay in memory and are sent only for eligible events; this app does not maintain a local image archive. `store=False` is passed to OpenAI, but that is not a promise of zero provider retention. Email copies remain with your email provider. Capture every five seconds can miss brief events; lighting changes can trigger false motion. This is an experimental notification tool, not a certified alarm.

## Start on boot

Edit `deploy/homewatch.service`, replacing `YOUR_USER` and paths to match your Pi. Then:

```sh
sudo cp deploy/homewatch.service /etc/systemd/system/homewatch.service
sudo systemctl daemon-reload
sudo systemctl enable --now homewatch
journalctl -u homewatch -f
```

Use `sudo systemctl stop homewatch` to stop capture. Away mode still uses the commands above. Systemd restarts the process after failures; logs show API errors and camera failures.

## Offline development

On a laptop, use a normal Python virtual environment; Picamera2 is imported only by `run`. No Pi, API credentials, or SMTP server are needed for tests:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m homewatch compare --images before.jpg after.jpg
```

Tests cover motion filtering, persistent rate limiting, person/uncertainty alert decisions, disarming during analysis, and dry-run network isolation. Hardware capture and live API/email delivery still require testing on your configured Pi.

## References

- [Raspberry Pi camera hardware](https://www.raspberrypi.com/documentation/accessories/camera.html)
- [Raspberry Pi camera software and Picamera2](https://www.raspberrypi.com/documentation/computers/camera_software.html)
- [OpenAI image inputs](https://developers.openai.com/api/docs/guides/images-vision)
- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
