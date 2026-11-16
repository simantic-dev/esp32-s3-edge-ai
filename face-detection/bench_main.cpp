// Benchmark: the stock example's embedded photo through the detector 10 times, timed.
#include "dl_image_jpeg.hpp"
#include "esp_log.h"
#include "esp_timer.h"
#include "human_face_detect.hpp"

extern const uint8_t human_face_jpg_start[] asm("_binary_human_face_jpg_start");
extern const uint8_t human_face_jpg_end[] asm("_binary_human_face_jpg_end");
static const char *TAG = "bench";

extern "C" void app_main(void)
{
    dl::image::jpeg_img_t jpeg = {.data = (void *)human_face_jpg_start,
                                  .data_len = (size_t)(human_face_jpg_end - human_face_jpg_start)};
    auto img = dl::image::sw_decode_jpeg(jpeg, dl::image::DL_IMAGE_PIX_TYPE_RGB888);
    HumanFaceDetect *detect = new HumanFaceDetect();
    for (int i = 0; i < 10; i++) {
        int64_t t0 = esp_timer_get_time();
        auto &faces = detect->run(img);
        int us = (int)(esp_timer_get_time() - t0);
        const char *s = faces.empty() ? "none" : "face";
        if (!faces.empty()) {
            auto &f = faces.front();
            ESP_LOGI(TAG, "run %d: %d us, %s %.3f [%d %d %d %d]", i, us, s, f.score, f.box[0], f.box[1], f.box[2], f.box[3]);
        } else {
            ESP_LOGI(TAG, "run %d: %d us, none", i, us);
        }
    }
    ESP_LOGI(TAG, "done");
}
