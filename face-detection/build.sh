#!/usr/bin/env bash
# Rebuild flash.bin (or bench.bin) from ESP-DL's human_face_detect example (esp-dl v3.3.14, ESP-IDF v5.4.4).
# Two changes from stock:
#   - main/app_main.cpp is replaced by ours: frames come from UART1 instead of an embedded JPEG.
#   - The default model is ESPDET_PICO_224_224_FACE instead of the two-stage MSR+MNP, which found
#     no face in webcam frames where a person looked down at the laptop.
# ./build.sh bench builds bench.bin instead: bench_main.cpp times the stock embedded photo ten times,
# for an ESP32-S3 with 2 MB quad PSRAM (N8R2), code run from flash (CONFIG_SPIRAM_XIP_FROM_PSRAM=n:
# the 1.6 MB app does not fit in 2 MB PSRAM beside the model).
# Usage: source $IDF_PATH/export.sh (v5.4.4), then ./build.sh [bench]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -n "${IDF_PATH:-}" ] || { echo "error: source ESP-IDF v5.4.4 export.sh first" >&2; exit 2; }

W="$(mktemp -d)"
trap 'rm -rf "$W"' EXIT
git clone -q --depth 1 --branch v3.3.14 https://github.com/espressif/esp-dl.git "$W/esp-dl"
cd "$W/esp-dl/examples/human_face_detect"
printf 'CONFIG_FLASH_HUMAN_FACE_DETECT_MSRMNP_S8_V1=n\nCONFIG_FLASH_ESPDET_PICO_224_224_FACE=y\nCONFIG_ESPDET_PICO_224_224_FACE=y\n' > sdkconfig.espdet
DEFAULTS="sdkconfig.defaults;sdkconfig.defaults.esp32s3;sdkconfig.espdet"

if [ "${1:-}" = bench ]; then
  cp "$HERE/bench_main.cpp" main/app_main.cpp
  printf 'CONFIG_SPIRAM_MODE_QUAD=y\nCONFIG_SPIRAM_MODE_OCT=n\nCONFIG_SPIRAM_XIP_FROM_PSRAM=n\n' > sdkconfig.quad
  DEFAULTS="$DEFAULTS;sdkconfig.quad"
  OUT=bench.bin
else
  cp "$HERE/app_main.cpp" main/app_main.cpp
  OUT=flash.bin
fi

idf.py -D "SDKCONFIG_DEFAULTS=$DEFAULTS" set-target esp32s3
idf.py build
idf.py merge-bin -o merged-flash.bin
cp build/merged-flash.bin "$HERE/$OUT"
echo "built $HERE/$OUT"
