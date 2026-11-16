# Edge AI on a simulated ESP32-S3

Espressif's TensorFlow Lite Micro examples, running on the ESP32-S3's vector instructions inside
the [Simantic](https://simantic.com) simulator. No board, no toolchain: the firmware images are
in this repo.

```sh
git clone https://github.com/simantic-dev/esp32-s3-edge-ai && cd esp32-s3-edge-ai && ./demo person
```

You need `sim` 0.10.1 or newer and a free account:

```sh
curl -fsSL https://simantic.com/install | sh
```

## The demos

| Command | What runs |
|---|---|
| `./demo person` | Person detection on ten test images. Prints each score and the inference time the firmware measured. |
| `./demo speech` | Keyword spotting. A simulated I2S microphone plays a spoken "yes" and "no" from WAV files. |
| `./demo live` | The same, from your computer's microphone. Say "yes" or "no". |

### `./demo person`

![person detection](media/person-detection.gif)

Espressif's `person_detection` example with no source edits. The model is TensorFlow's person
classifier (MobileNet v1, 96x96 grayscale, int8): person or no person, no boxes. A twelve-line
Python script on the other end of UART0 types `detect_image 0` to `detect_image 9` at the
firmware's console.

The image is built for an ESP32-S3 without PSRAM, and we ran this exact `flash.bin` on one:

| | Real chip | Simulator |
|---|---|---|
| Inference time | 49 ms | 50 ms |
| Depthwise conv / conv layers | 20 ms / 28 ms | 20 ms / 28 ms |
| Scores, ten images | identical | identical |

Image 3 is a monkey and image 7 is a portrait; the model gets both wrong, on the chip too. If
you have the board, flash it and compare: `esptool.py write_flash 0x0 person-detection/flash.bin`.

### `./demo speech`

![keyword spotting](media/keyword-spotting.gif)

Espressif's `micro_speech` example, also unedited. It has no test mode: it configures I2S0 at
16 kHz and listens to a microphone. `keyword-spotting/mic.py` is that microphone, a Python
script on the I2S data line that plays the example's own test clips. Four seconds of audio take
a couple of seconds to run, because firmware that is waiting for samples costs almost nothing to
simulate.

This one has not been run on a board. The detections are the simulator's.

### `./demo live`

Needs `ffmpeg` (`brew install ffmpeg`) and any microphone your computer can see: built-in,
headset, webcam. `./demo live` records one second first and tells you if it hears nothing, so
you find out about a missing microphone or a blocked permission before the chip boots. Then wait
for `Audio Recording started` and speak.

- Wrong microphone? `./demo mics` lists them, `MIC=1 ./demo live` picks one.
- Too quiet? `MIC_GAIN=4 ./demo live`.
- The model knows two words, "yes" and "no".
- The stock example classifies back-to-back one-second windows, so a word that straddles two
  windows can be missed. Say it again.

`./demo live 300` runs for five minutes instead of one. `MIC_CMD` replaces the capture command
entirely (anything that writes 16 kHz mono s16le to stdout). Linux uses PulseAudio and has not
been tried.

## How it is wired

Each demo is one `sim` command (read `demo`, it is 30 lines): a chip, a firmware image and a
board file. The board file names the parts on the chip's pins. Here the parts are Python:

```
mic: Sound.ScriptedI2sPeer @ none
    i2s: i2s0
    file: "mic.py"
```

Change the script and you have changed the hardware. `mic.py` is where you would put your own
recordings; `console_peer.py` is where you would type different commands.

## Rebuilding the firmware

`person-detection/build.sh` and `keyword-spotting/build.sh` are the exact recipes, on ESP-IDF
v5.4.4. Useful things to try on the person detector, all of which we checked against the board:

| Change in `sdkconfig` | Real chip | Simulator |
|---|---|---|
| none | 49 ms | 50 ms |
| `CONFIG_NN_ANSI_C=y` (plain C kernels, no vector instructions) | 439 ms | 447 ms |
| `CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ_160=y` | 71 ms | 71 ms |
| `CONFIG_ESP32S3_DATA_CACHE_32KB=y` | 49 ms | 50 ms |
| `CONFIG_COMPILER_OPTIMIZATION_SIZE=y` | 49 ms | 50 ms |

With the tensor arena in quad PSRAM (an ESP32-S3R2) the chip takes 61 to 62 ms and the simulator
says 57, so on PSRAM builds trust the ranking more than the number.

## Licenses

Scripts and board files: MIT. Firmware images and audio clips: builds and copies of Apache-2.0
work by Espressif and the TensorFlow authors; see `NOTICE`. The simulator itself is a commercial
product and is not part of this repository.
