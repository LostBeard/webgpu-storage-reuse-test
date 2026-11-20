# Does one WebGPU invocation read back what it just wrote?

**Live page:** https://lostbeard.github.io/webgpu-storage-reuse-test/ (`?selftest` adds a variant that is wrong on purpose)

One invocation (workgroup size 1, one workgroup) builds three canonical Huffman codes in a row, as a DEFLATE encoder does
(literal, distance and code-length codes). Each build zeroes 16 counters in a storage buffer, counts the code lengths into
them, and reads them back to compute the first code of each length. **All three builds use the same 16 counter slots.**
WGSL orders an invocation's own memory accesses, so every read must see that invocation's latest write. The page checks the
codes against the same computation in JavaScript. Plain WebGPU, no libraries.

| Variant | Kind | |
|---|---|---|
| A | test | the build inlined three times, shared counter slots (the shape a compiler that inlines produces) |
| B | test | one WGSL function called three times, shared counter slots |
| C | control | inlined, counters in a function-scope array (the "next code" slots stay in the storage buffer) |
| D | control | inlined, each build with its own counter slots |

When a later build's codes are wrong, the page also says whether they equal the codes built from the **first** build's
counts: the signature of reads returning stale values.

## Why

SpawnDev.Codecs' GPU DEFLATE encoder builds its Huffman codes this way (the three builds are one inlined helper). On an
AMD Radeon RX 590 (Windows, Chrome, WebGPU on D3D12) its PNGs did not decode: the distance and code-length codes were
exactly the ones the **literal** code's counts give. The same WGSL is right on an NVIDIA GPU, and the same kernel is
right on CUDA and OpenCL on the RX 590 itself. Codecs moved the counters to thread-private memory
(LostBeard/SpawnDev.Codecs#1).

## The replay: reproduced without SpawnDev code

**Replay page:** https://lostbeard.github.io/webgpu-storage-reuse-test/replay.html

`traces/png_first_encode_rx590.jsonl` is every WebGPU call of one PNG encode (a 512 x 512 photo) by SpawnDev.Codecs' GPU encoder
at commit f16ef38, recorded on the RX 590 with `tools/tracer.js` (the first 414 of 28,255 records; `tools/trim_trace.py`).
`replay.html` reissues those calls on a fresh device (`tools/replay.js`; no SpawnDev code, no .NET) and hands the PNG the GPU
wrote to the browser's own PNG decoder. The faulty kernel is `PlanKernel` in the recording (about 261 KB of WGSL): one thread
per DEFLATE block, building the three Huffman codes of the block in the same storage slots.

| GPU | Driver | Browser | Replay result |
|---|---|---|---|
| AMD Radeon RX 590 (gcn-4, 0x67df) | 31.0.21925.1001 | Chrome 157, D3D12 | **affected, 3 of 3 runs**: the PNG does not decode ("The source image could not be decoded."), 0 WebGPU errors, every readback equal to the recording (byte for byte) |
| AMD Radeon RX 590 (gcn-4, 0x67df) | 31.0.21925.1001 | Chrome 157, D3D12, DXC (`--enable-dawn-features=use_dxc`) | **affected**: does not decode, 0 errors, every readback equal to the recording |
| AMD Radeon RX 590 (gcn-4, 0x67df) | 31.0.21925.1001 | Chrome 157, D3D12, FXC (`--disable-dawn-features=use_dxc`; 'subgroups' not requested, no recorded shader uses it) | **affected**: does not decode, 0 errors; the PNG differs from the recording (broken differently) |
| NVIDIA RTX 4070 (lovelace) | | Chrome 157, D3D12 | not affected: the PNG decodes (512 x 512), 0 WebGPU errors; its PNG differs from the recorded one (same length) |

The same encoder is right on CUDA and OpenCL on the RX 590, and its WGSL is right on the NVIDIA GPU.
Both D3D shader compilers break it on the RX 590, and so does **Firefox**, whose WebGPU (wgpu) generates its own HLSL from the
WGSL instead of Dawn's. All of them write the **same broken PNG** (403,614 bytes, FNV-1a `ee572ce0`; its zlib stream fails with
"invalid bit length repeat": the code-length code is wrong). What they share is the **AMD D3D12 driver** (31.0.21925.1001);
NVIDIA is right with the same calls.

| GPU | Browser | Verdict (the PNG's zlib stream must inflate to 786,944 bytes) |
|---|---|---|
| AMD Radeon RX 590 | Chrome 157, D3D12, DXC (default) | **affected**: "invalid bit length repeat" after 0 bytes; PNG FNV-1a `ee572ce0` |
| AMD Radeon RX 590 | Firefox 143.0.1 (wgpu, D3D12; limits lowered to the adapter's) | **affected**: same error, **same PNG** `ee572ce0` (Firefox's image decoder still accepts it: why the page checks the zlib stream itself) |

Chrome on Vulkan is not an option on Windows (Chrome's WebGPU backend flag takes default / d3d11 / opengles / swiftshader), and
on D3D11 FXC fails to compile another kernel of the recording, so those were not compared.

## The simple page: results so far

| GPU | Browser | Result |
|---|---|---|
| NVIDIA RTX 4070 (lovelace) | Chrome 157, Windows 11 | not affected (all variants right; the self-test variant is caught) |
| AMD Radeon RX 590 (gcn-4), driver 31.0.21925.1001 | Chrome 157, Windows, D3D12 | **not affected** by this simple shape (all variants right; the self-test variant is caught), although the encoder kernel this mirrors fails on the same card |

So the access pattern alone does not trigger it on the RX 590; something else in the encoder kernel does. Next step: a
recording of that kernel's WebGPU calls (`tools/tracer.js` + `tools/trace_server.py`), replayed without the encoder
(`tools/replay.js`), as in [webgpu-device-hung-test](https://github.com/LostBeard/webgpu-device-hung-test).

Please open an issue with your page's report (it builds the text for you), affected or not.

## License

MIT
