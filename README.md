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

## Results so far

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
