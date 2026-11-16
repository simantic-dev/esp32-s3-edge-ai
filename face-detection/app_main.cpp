// Replaces app_main.cpp of ESP-DL's human_face_detect example (build.sh). The detector is the
// stock one; only the image source changes: frames arrive on UART1 instead of an embedded JPEG.
// Protocol on UART1 (camera.py is the other end):
//   chip -> "F\n"                       ask for a frame
//   host -> W*H*3 bytes                 RGB888, row-major
//   chip -> "B x1 y1 x2 y2 score\n" ... one line per face, then "E <ms>\n"
#include <cstdio>
#include "driver/uart.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "human_face_detect.hpp"

#define CAM_UART UART_NUM_1
#define CAM_BAUD 2000000   // must match baudRate in camera.board
#define CAM_TX 17
#define CAM_RX 18
#define W 160              // the model resizes to its own 224x224 input on chip
#define H 120

static const char *TAG = "face_cam";

extern "C" void app_main(void)
{
    uart_config_t cfg = {};
    cfg.baud_rate = CAM_BAUD;
    cfg.data_bits = UART_DATA_8_BITS;
    cfg.parity = UART_PARITY_DISABLE;
    cfg.stop_bits = UART_STOP_BITS_1;
    cfg.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
    cfg.source_clk = UART_SCLK_DEFAULT;
    ESP_ERROR_CHECK(uart_driver_install(CAM_UART, 16384, 0, 0, NULL, 0));
    ESP_ERROR_CHECK(uart_param_config(CAM_UART, &cfg));
    ESP_ERROR_CHECK(uart_set_pin(CAM_UART, CAM_TX, CAM_RX, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));

    auto *buf = (uint8_t *)heap_caps_malloc(W * H * 3, MALLOC_CAP_SPIRAM);
    dl::image::img_t img = {.data = buf, .width = W, .height = H, .pix_type = dl::image::DL_IMAGE_PIX_TYPE_RGB888};
    HumanFaceDetect *detect = new HumanFaceDetect();
    char line[64];

    for (;;) {
        uart_write_bytes(CAM_UART, "F\n", 2);
        int got = 0;
        while (got < W * H * 3) {
            int n = uart_read_bytes(CAM_UART, buf + got, W * H * 3 - got, pdMS_TO_TICKS(2000));
            if (n <= 0) {   // host stalled or a byte was lost: drop the partial frame, ask again
                ESP_LOGW(TAG, "frame timeout at %d bytes", got);
                break;
            }
            got += n;
        }
        if (got < W * H * 3) {
            uart_flush_input(CAM_UART);
            continue;
        }

        int64_t t0 = esp_timer_get_time();
        auto &faces = detect->run(img);
        int ms = (int)((esp_timer_get_time() - t0) / 1000);

        for (const auto &f : faces) {
            int n = snprintf(line, sizeof line, "B %d %d %d %d %.2f\n", f.box[0], f.box[1], f.box[2], f.box[3], f.score);
            uart_write_bytes(CAM_UART, line, n);
        }
        int n = snprintf(line, sizeof line, "E %d\n", ms);
        uart_write_bytes(CAM_UART, line, n);
        ESP_LOGI(TAG, "%d face(s), %d ms", (int)faces.size(), ms);
    }
}
