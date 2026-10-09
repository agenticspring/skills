# Inference Angels session reference

Verified project facts from the session:

- Repository: `jacklarmer/inference-angels`
- Working directory used: `/tmp/inference-angels`
- Chain: Robinhood Chain, chain ID `4663`
- Contract: `0xD982d8F175BD50B976F4Ad90562c9e38200091f9`
- RPC: `https://rpc.mainnet.chain.robinhood.com`
- Corpus fingerprint: `0x9021379e4749cfee971b6188492653e2d579975e7d1cf1a25154ea6ee7794489`
- Corpus: 7,777 angels, 19,291 trials, 77 bands; 11,514 sealed trials.
- `miner/mine.js` supports `status`, `show`, `check`, and `solve`; `check` is local/read-only and must pass before `solve`.
- Hunt puzzles can be solved by hashing `corpus/v3/public/wordlist.json` entries against the requested SHA-256 prefix.
- Final answer format is SHA-256 of `tokenId|answer1|answer2...`; the miner converts this to the on-chain form.
- Easy low-number hunt candidates were heavily contested: locally valid answers repeatedly failed pre-broadcast as `already claimed`. Treat this as a race, not a solver failure.
- A prior scanner mistakenly searched `/root` and unrelated Hashwood files. Always pin all operations to `/tmp/inference-angels`.
- A prior run created 100 wallet files, but only the original wallet had gas. Never conflate key-file count with funded-wallet count.
- No successful mint or TxHash was verified in the session.
