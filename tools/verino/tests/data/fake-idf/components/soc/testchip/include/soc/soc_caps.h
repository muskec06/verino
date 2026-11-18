/* Synthetic header for tests. */
#pragma once
#define SOC_GPIO_PIN_COUNT      (10)
// Pins 3 and 4 do not exist; pin 9 is input only.
#define SOC_GPIO_VALID_GPIO_MASK         (0x3FFULL & ~(0ULL | BIT3 | BIT4))
#define SOC_GPIO_VALID_OUTPUT_GPIO_MASK  (SOC_GPIO_VALID_GPIO_MASK & ~(BIT9))
#define SOC_I2C_NUM                             (2U)
#define SOC_UART_NUM                (3)
#define SOC_UART_HP_NUM             (3)
#define SOC_SPI_PERIPH_NUM                  3
#define SOC_LEDC_TIMER_NUM               (4)
#define SOC_LEDC_CHANNEL_NUM             (8)
#define SOC_ADC_PERIPH_NUM                      (2)
#define SOC_RTCIO_PIN_COUNT   3
#define SOC_TWAI_CONTROLLER_NUM         1U
#define SOC_ADC_CHANNEL_NUM(PERIPH_NUM)         (10)
#define SOC_LONG_MACRO \
        (1 << 2)
