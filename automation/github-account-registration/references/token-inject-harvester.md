# Inject minted GitHub PATs into api-key-leak

After `login_ok` + classic PAT no-exp:

1. Append `ghp_…` / `github_pat_…` to `/root/github-autoreg/tokens.txt`
2. Append the same to `/root/api-key-leak/data/tokens.txt`
3. **Normalize** tokens file: one token per line, strip tabs/meta descriptions
4. **Restart** harvester (boot-load only — no hot reload):
   ```bash
   /usr/bin/screen -S api-key-leak -X quit 2>/dev/null || true
   pkill -f './harvester --loop' 2>/dev/null || true
   /usr/bin/screen -dmS api-key-leak /bin/bash -lc 'cd /root/api-key-leak && exec ./start.sh'
   ```
5. Verify log: `Loaded N GitHub token(s) for rotation`  
   Session proof: was **4**, after github-autoreg batch inject+restart became **16**
6. Do not claim high search/core limits for brand-new accounts (often search 10 / core 60)

Related skill: `api-key-leak-harvester`
