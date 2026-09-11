/* Hand-tuned software implementation of the integer streaming SNN decoder for sky130_vex2_soc (referee experiment E4).
 * Same event-driven algorithm and the same outputs as bmi_snn_sw.c, with the inner loop reduced to what the arithmetic
 * needs: the per-synapse saturation of the 20-bit reference (satv) is replaced by an unclamped 32-bit add plus one range
 * check per bin. The check verifies after every tick that no membrane can reach the 20-bit limit within the next bin
 * (|v| < 2^19 - 128 x 24, i.e. 24 events of the largest weight), so the outputs are provably identical to the saturating
 * reference on any stream for which the check passes; a failing check is reported (tohost = 0xC0) instead of silently
 * differing. The weights stay int8 in memory (the 8 KB data SRAM holds no wider copy).
 * Schedule (matches tb_fw_mnist.v): init -> sleep -> wake -> decode N_BINS bins -> gpio_done -> sleep -> wake -> halt
 * PASS: tohost = 1 when all outputs match the reference; else 0xE0 | first mismatching bin; 0xC0 if the range check failed.
 */
#include <stdint.h>
#include "soc.h"
#include "bmi_weights.h"

#define O_MAX  ((int32_t)8388607)
#define O_MIN  ((int32_t)-8388608)
#define V_GUARD ((int32_t)(524288 - 128 * 24))   /* 2^19 minus 24 events of |w| = 128 */

static int32_t v[BMI_H];
static int32_t o0, o1;

static inline int32_t sato(int32_t x) { return x > O_MAX ? O_MAX : (x < O_MIN ? O_MIN : x); }

static inline void add_row(const int8_t *restrict row)
{
  int32_t *restrict m = v;
  for (int j = 0; j < BMI_H; j += 8) {         /* eight independent load-add-store chains per iteration */
    m[j]     += row[j];     m[j + 1] += row[j + 1]; m[j + 2] += row[j + 2]; m[j + 3] += row[j + 3];
    m[j + 4] += row[j + 4]; m[j + 5] += row[j + 5]; m[j + 6] += row[j + 6]; m[j + 7] += row[j + 7];
  }
}

static int tick(void)
{
  add_row(&W1[BMI_NIN * BMI_H]);              /* bias row */
  o0 = o0 - (o0 >> BMI_K2);
  o1 = o1 - (o1 >> BMI_K2);
  int32_t maxabs = 0;
  for (int j = 0; j < BMI_H; j++) {
    int32_t x = v[j];
    int32_t vl = x - (x >> BMI_K1);
    if (vl >= BMI_THETA) {
      vl = 0;
      o0 = sato(o0 + (int32_t)W2[2 * j]);
      o1 = sato(o1 + (int32_t)W2[2 * j + 1]);
    }
    v[j] = vl;
    int32_t a = vl < 0 ? -vl : vl;
    if (a > maxabs) maxabs = a;
  }
  return maxabs < V_GUARD;
}

int main(void)
{
  gpio_set_done(0);
  for (int j = 0; j < BMI_H; j++) v[j] = 0;
  o0 = 0; o1 = 0;
  sleep_until_wake();

  int bin = 0, fail = -1, range_fail = 0;
  const uint8_t *tok = STREAM, *end = STREAM + BMI_NTOK;
  while (tok < end) {
    uint8_t t = *tok++;
    if (t == 0xFF) {
      if (!tick()) range_fail = 1;
      if (fail < 0 && (o0 != EXPECT[2 * bin] || o1 != EXPECT[2 * bin + 1]))
        fail = bin;
      bin++;
    } else {
      add_row(&W1[(int)t * BMI_H]);
    }
  }
  gpio_set_done(1);
  sleep_until_wake();
  if (range_fail) return 0xC0;
  if (fail < 0 && bin == BMI_NBINS)
    return 1;
  return 0xE0 | (fail & 0x1F);
}
