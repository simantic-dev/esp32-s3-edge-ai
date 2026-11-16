#!/usr/bin/env bash
# Rebuild flash.bin from Espressif's person_detection example (esp-tflite-micro v1.4.3, esp-nn 1.5.0,
# ESP-IDF v5.4.4). No source file of the example is edited. Two build inputs differ from stock:
#   - main/idf_component.yml: the esp32-camera dependency is swapped for a pin of esp-nn. With no
#     camera driver in the build the example selects its console mode (README, "Using CLI for
#     inferencing"): ten embedded 96x96 images, one per `detect_image <n>`.
#   - PSRAM is turned off, so the image runs on an ESP32-S3 without PSRAM (model ESP32-S3FN8) and
#     the tensor arena sits in internal RAM.
# Usage: source $IDF_PATH/export.sh (v5.4.4), then ./build.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -n "${IDF_PATH:-}" ] || { echo "error: source ESP-IDF v5.4.4 export.sh first" >&2; exit 2; }

W="$(mktemp -d)"
trap 'rm -rf "$W"' EXIT
git clone -q --depth 1 --branch v1.4.3 https://github.com/espressif/esp-tflite-micro.git "$W/esp-tflite-micro"
cd "$W/esp-tflite-micro/examples/person_detection"
sed -i.bak 's|^  espressif/esp32-camera:.*|  espressif/esp-nn: "==1.5.0"|' main/idf_component.yml
grep -q 'espressif/esp-nn: "==1.5.0"' main/idf_component.yml
printf 'CONFIG_SPIRAM=n\nCONFIG_ESP32S3_SPIRAM_SUPPORT=n\n' > sdkconfig.nopsram

idf.py -D "SDKCONFIG_DEFAULTS=sdkconfig.defaults;sdkconfig.nopsram" set-target esp32s3
idf.py build
idf.py merge-bin -o merged-flash.bin
cp build/merged-flash.bin "$HERE/flash.bin"
echo "built $HERE/flash.bin"
