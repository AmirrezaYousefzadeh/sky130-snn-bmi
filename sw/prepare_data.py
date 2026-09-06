#!/usr/bin/env python3
"""Prepare the NeuroBench primate-reaching (Indy) sessions for streaming decoding.

Replicates neurobench.datasets.PrimateReaching with the benchmark settings used by the
NeuroBench primate-reaching baselines:
    num_steps=1, train_ratio=0.5, bin_width=0.004, biological_delay=0,
    remove_segments_inactive=False, spike_sorting=False, split_num=1, stride=0.004

Output per session (data/prepared/<session>.npz):
    spikes   uint8 (T, 96)  binary: channel fired in the 4 ms bin (units OR-ed, hash unit included)
    vel      float32 (T, 2) cursor velocity = torch.gradient(cursor_pos) along time (NeuroBench labels)
    ind_train / ind_val / ind_test  int64 bin indices (NeuroBench segment-based split)
    t        float64 (T,) bin time stamps
"""
from __future__ import annotations
import argparse, math, sys
from pathlib import Path
import numpy as np, h5py, torch

SAMPLING_RATE = 4e-3

def get_flag_index(target_pos):
    target_diff = np.diff(target_pos, axis=1, append=target_pos[:, -1].reshape(2, 1))
    return np.nonzero(np.sum(np.abs(target_diff), axis=0))[0]

def split_into_segments(indices, last_idx):
    indices = np.insert(indices, 0, 0)
    indices = np.append(indices, [last_idx])
    return np.transpose(np.array([indices[:-1], indices[1:]]))

def prepare(mat_path: Path, out_dir: Path, bin_width=0.004, train_ratio=0.5, split_num=1, stride=0.004):
    print(f"Loading {mat_path.name}")
    f = h5py.File(mat_path, "r")
    spikes = f["spikes"][()]           # (units, channels) of HDF5 refs
    cursor_pos = f["cursor_pos"][()]   # (2, T)
    target_pos = f["target_pos"][()]   # (2, T)
    t = np.squeeze(f["t"][()])
    new_t = np.arange(t[0] - bin_width, t[-1], SAMPLING_RATE)
    ratio = int(np.round(bin_width / SAMPLING_RATE))
    assert ratio == 1, "streaming setting expects 4 ms bins"

    seg_idx = np.array(get_flag_index(target_pos))
    time_segments = np.array(split_into_segments(seg_idx, target_pos.shape[1]))

    spike_train = np.zeros((*spikes.shape, len(new_t)), dtype=np.int8)
    for u in range(spikes.shape[0]):
        for c in range(spikes.shape[1]):
            el = spikes[u, c]
            arr = el if isinstance(el, np.ndarray) else f[el][()]
            bins, _ = np.histogram(arr, bins=new_t.squeeze())
            idx = np.nonzero(bins)[0] + 1
            spike_train[u, c, idx] = 1
    spike_train = np.bitwise_or.reduce(spike_train, axis=0)   # (channels, T_bins)
    # NeuroBench: samples = binned_spike_train (channels x timesteps) — with ratio 1 the
    # length is len(new_t); labels come from cursor_pos (T). __getitem__ indexes both with the
    # same bin index, so we truncate to the common length.
    T = min(spike_train.shape[1], cursor_pos.shape[1])
    spike_train = spike_train[:, :T]
    labels = torch.gradient(torch.from_numpy(cursor_pos).float(), dim=1)[0].numpy()[:, :T]

    # split (split_num=1, stride 4 ms)
    total_segments = time_segments.shape[0]
    sub_length = int(total_segments / split_num)
    stride_i = int(stride / SAMPLING_RATE)
    train_len = math.floor(train_ratio * sub_length)
    val_len = math.floor((sub_length - train_len) / 2)
    ind_train, ind_val, ind_test = [], [], []
    for split_no in range(split_num):
        for i in range(sub_length):
            s, e = time_segments[split_no * sub_length + i]
            rng = list(np.arange(s, e, stride_i))
            if i < train_len:
                ind_train += rng
            elif train_len <= i < train_len + val_len:
                ind_val += rng
            else:
                ind_test += rng
    ind_train, ind_val, ind_test = (np.array(x, dtype=np.int64) for x in (ind_train, ind_val, ind_test))
    # guard against indices beyond common length
    ind_train, ind_val, ind_test = (x[x < T] for x in (ind_train, ind_val, ind_test))

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / (mat_path.stem + ".npz")
    np.savez_compressed(out, spikes=spike_train.T.astype(np.uint8), vel=labels.T.astype(np.float32),
                        ind_train=ind_train, ind_val=ind_val, ind_test=ind_test, t=t[:T],
                        n_segments=total_segments)
    ev_per_bin = spike_train.sum(0)
    print(f"  T={T} bins ({T*0.004/60:.1f} min), segments={total_segments}, "
          f"train/val/test bins = {len(ind_train)}/{len(ind_val)}/{len(ind_test)}")
    print(f"  active channels per bin: mean {ev_per_bin.mean():.2f}, max {ev_per_bin.max()}, "
          f"sparsity {(1-ev_per_bin.mean()/96)*100:.1f}%  -> {out}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mats", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "data" / "prepared")
    a = ap.parse_args()
    for m in a.mats:
        prepare(m, a.out)
