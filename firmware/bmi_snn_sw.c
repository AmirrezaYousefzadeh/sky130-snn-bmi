/* Software implementation of the integer streaming SNN decoder (sw/snn_int.py) for sky130_vex2_soc.
 * Same event-driven algorithm as bmi_snn_top.v (only rows of channels that fired are visited).
 * Schedule (matches tb_fw_mnist.v): init -> sleep -> wake -> decode N_BINS bins -> gpio_done -> sleep -> wake -> halt
 * PASS: tohost = 1 when all outputs match the reference; else 0xE0 | first mismatching bin.
 */
#include <stdint.h>
#include "soc.h"
#include "bmi_weights.h"

#define V_MAX  ((int32_t)524287)
#define V_MIN  ((int32_t)-524288)
#define O_MAX  ((int32_t)8388607)
#define O_MIN  ((int32_t)-8388608)

static int32_t v[BMI_H];
static int32_t o0, o1;

static inline int32_t satv(int32_t x) { return x > V_MAX ? V_MAX : (x < V_MIN ? V_MIN : x); }
static inline int32_t sato(int32_t x) { return x > O_MAX ? O_MAX : (x < O_MIN ? O_MIN : x); }

static void add_row(const int8_t *row)
{
  for (int j = 0; j < BMI_H; j++)
    v[j] = satv(v[j] + (int32_t)row[j]);
}

static void tick(void)
{
  add_row(&W1[BMI_NIN * BMI_H]);              /* bias row */
  o0 = o0 - (o0 >> BMI_K2);
  o1 = o1 - (o1 >> BMI_K2);
  for (int j = 0; j < BMI_H; j++) {
    int32_t vl = v[j] - (v[j] >> BMI_K1);
    if (vl >= BMI_THETA) {
      v[j] = 0;
      o0 = sato(o0 + (int32_t)W2[2 * j]);
      o1 = sato(o1 + (int32_t)W2[2 * j + 1]);
    } else {
      v[j] = vl;
    }
  }
}

int main(void)
{
  gpio_set_done(0);
  sleep_until_wake();

  int bin = 0, fail = -1;
  for (int i = 0; i < BMI_NTOK; i++) {
    uint8_t tok = STREAM[i];
    if (tok == 0xFF) {
      tick();
      if (fail < 0 && (o0 != EXPECT[2 * bin] || o1 != EXPECT[2 * bin + 1]))
        fail = bin;
      bin++;
    } else {
      add_row(&W1[(int)tok * BMI_H]);
    }
  }
  gpio_set_done(1);
  sleep_until_wake();
  if (fail < 0 && bin == BMI_NBINS)
    return 1;
  return 0xE0 | (fail & 0x1F);
}
