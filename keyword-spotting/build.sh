#!/usr/bin/env bash
# Build flash.bin from Espressif's micro_speech example (espressif/esp-tflite-micro v1.4.3,
# esp-nn 1.5.0 on its default CONFIG_NN_OPTIMIZED, ESP-IDF v5.4.4) with its sources unedited:
# the stock audio_provider reads the I2S microphone. The only change is the esp-nn version pin
# in the component manifest, . Also copies the three test clips the
# example ships (test_data/*.wav), which mic.py plays.
# Usage: source $IDF_PATH/export.sh (v5.4.4), then ./build.sh [out.elf]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -n "${IDF_PATH:-}" ] || { echo "error: source ESP-IDF v5.4.4 export.sh first" >&2; exit 2; }

W="$(mktemp -d)"
trap 'rm -rf "$W"' EXIT
git clone -q --depth 1 --branch v1.4.3 https://github.com/espressif/esp-tflite-micro.git "$W/esp-tflite-micro"
cd "$W/esp-tflite-micro/examples/micro_speech"
sed -i.bak 's|^  espressif/esp-tflite-micro:|  espressif/esp-nn: "==1.5.0"\n&|' main/idf_component.yml
grep -q 'espressif/esp-nn: "==1.5.0"' main/idf_component.yml
idf.py set-target esp32s3
idf.py build
idf.py merge-bin -o merged-flash.bin
cp build/merged-flash.bin "$HERE/flash.bin"
cp test_data/yes_1000ms.wav test_data/no_1000ms.wav test_data/silence_1000ms.wav "$HERE/"
[ -z "${1:-}" ] || cp build/micro_speech.elf "$1"
echo "built $HERE/flash.bin"
