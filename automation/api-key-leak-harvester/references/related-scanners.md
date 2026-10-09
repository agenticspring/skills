# Related scanners vs api-key-leak

## Our tool
`/root/api-key-leak` = continuous **provider-targeted** public harvest + **balance validation** + Discord + captcha ranking for product bots.

## TruffleHog (trufflesecurity/trufflehog)
- Class: secret discovery / classification / verification security engine
- Strength: 800+ detectors, git history, filesystem/S3/docker, mature verify
- Weak for our goal: not a 24/7 captcha-key farmer; no first-class “balance rank into bot .env”
- Use: on-demand deep scan of a hot repo URL the harvester surfaces

## shhgit (eth0izzle/shhgit)
- Class: near-real-time public GitHub/GitLab/Bitbucket secret scanner
- Strength historically: events firehose + signatures + entropy + local mode
- **README: no longer maintained** — do not rebuild our core on it
- Steal concepts only:
  1. events-first freshness
  2. signature/keyword lists
  3. shallow deep scan of interesting repos/files
  4. multi-source (gist/public streams)

## Decision rule
```
Need more Capsolver/2captcha for Webnovel CF/reCAPTCHA?
  → improve api-key-leak (tokens, queries, gist, hot-repo, rank)
Need audit of one repo / history / non-captcha secret class?
  → TruffleHog on-demand
Need rewrite from shhgit?
  → No
```
