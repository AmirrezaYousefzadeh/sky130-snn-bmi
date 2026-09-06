#!/usr/bin/env python3
"""Integer streaming SNN decoder — the exact arithmetic implemented by the RTL (bmi_snn_top.v).

Model (per 4 ms bin t, inputs x_t in {0,1}^96):
  v[j] += sum_{c: x_t[c]=1} W1[c][j] + W1[96][j]        (bias row 96; saturating int20)
  vl    = v - (v >> K1)                                 (arithmetic shift = floor(v / 2^K1))
  s[j]  = vl[j] >= THETA ; v[j] = 0 if s[j] else vl[j]  (zero reset)
  o[i]  = (o[i] - (o[i] >> K2)) + sum_j s[j] * W2[j][i]  (saturating int24, non-spiking readout)
  y_t   = o                                              (chip output, two int24 words)
Prediction (host-side post-map, part of the model definition):
  vhat_t[i] = G[i] * y_t[i] / 2^12 + B[i]   (in normalised velocity units; de-normalise with mean/std)

Weights: W1 int8 [97][H] (row 96 = bias), W2 int8 [H][2].
Memory map (32-bit words, little-endian byte lanes):
  W1[c][4w+l]  -> word c*16 + w, byte l          (c = 0..96, w = 0..15, l = 0..3)      [0 .. 1551]
  W2[j][i]     -> word 1600 + j, byte i                                                 [1600 .. 1663]
"""
from __future__ import annotations
import numpy as np

N_IN = 96
V_BITS, O_BITS = 20, 24
V_MAX, O_MAX = 2 ** (V_BITS - 1) - 1, 2 ** (O_BITS - 1) - 1
W2_BASE = 1600


def sat(x, m):
    return np.clip(x, -m - 1, m)


class IntSNN:
    def __init__(self, W1: np.ndarray, W2: np.ndarray, theta: int, k1: int, k2: int):
        assert W1.shape[0] == N_IN + 1 and W1.dtype == np.int64 or W1.dtype == np.int8
        self.W1 = W1.astype(np.int64)
        self.W2 = W2.astype(np.int64)
        self.H = W1.shape[1]
        self.theta, self.k1, self.k2 = int(theta), int(k1), int(k2)
        self.reset()

    def reset(self):
        self.v = np.zeros(self.H, dtype=np.int64)
        self.o = np.zeros(2, dtype=np.int64)

    def step(self, active_channels):
        """One bin. active_channels: iterable of channel ids that fired. Returns (y[2], n_hidden_spikes)."""
        v = self.v
        for c in active_channels:                       # sequential, as the hardware does
            v = sat(v + self.W1[c], V_MAX)
        v = sat(v + self.W1[N_IN], V_MAX)               # bias row
        vl = v - (v >> self.k1)
        s = vl >= self.theta
        self.v = np.where(s, 0, vl)
        o = self.o - (self.o >> self.k2)
        o = sat(o + (self.W2[s].sum(axis=0) if s.any() else 0), O_MAX)
        self.o = o
        return o.copy(), int(s.sum())

    def run(self, spikes_bool: np.ndarray):
        """spikes_bool: (T, 96) bool. Returns y (T,2) int64, hidden spike counts (T,)."""
        T = spikes_bool.shape[0]
        Y = np.zeros((T, 2), dtype=np.int64)
        S = np.zeros(T, dtype=np.int64)
        for t in range(T):
            Y[t], S[t] = self.step(np.flatnonzero(spikes_bool[t]))
        return Y, S

    # ---- export helpers ---------------------------------------------------------------------
    def memory_words(self) -> np.ndarray:
        """2048 x uint32 memory image."""
        mem = np.zeros(2048, dtype=np.uint32)
        W1u = (self.W1 & 0xFF).astype(np.uint32)
        for c in range(N_IN + 1):
            for w in range(self.H // 4):
                word = 0
                for l in range(4):
                    word |= int(W1u[c, 4 * w + l]) << (8 * l)
                mem[c * 16 + w] = word
        W2u = (self.W2 & 0xFF).astype(np.uint32)
        for j in range(self.H):
            mem[W2_BASE + j] = int(W2u[j, 0]) | (int(W2u[j, 1]) << 8)
        return mem


def r2_neurobench(pred: np.ndarray, label: np.ndarray) -> float:
    """NeuroBench R2: mean over the two axes of 1 - SSres / (N * var_pop(label))."""
    r = []
    for i in range(2):
        ss = np.sum((label[:, i] - pred[:, i]) ** 2)
        den = label[:, i].var() * len(label)
        r.append(1.0 - ss / den)
    return float(np.mean(r))
