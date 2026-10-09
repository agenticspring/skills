# Practical Commands (Hermes-native arsenal)

No war-room/npm dependency. Use system tools.

## Preflight

```bash
command -v nmap nuclei ffuf gobuster httpx subfinder dig whois curl jq nikto sqlmap
nmap --version | head -1
nuclei -version 2>/dev/null || true
```

## Recon

```bash
# DNS
dig +short example.com A
dig +short example.com ANY
whois example.com | head -50

# Subdomains
subfinder -d example.com -silent

# HTTP probe
httpx -u https://example.com -title -tech-detect -status-code
curl -sI https://example.com

# Ports
nmap -sV -T4 --top-ports 100 example.com
nmap -sV -sC -p 80,443 example.com
```

## Scan / candidates

```bash
nuclei -u https://example.com -silent -o evidence/nuclei.txt
ffuf -u https://example.com/FUZZ -w /usr/share/wordlists/dirb/common.txt -mc 200,204,301,302,403 -o evidence/ffuf.json
gobuster dir -u https://example.com -w /usr/share/wordlists/dirb/common.txt -q
nikto -h https://example.com
```

## Validation (authorized only)

```bash
# targeted request proof
curl -sS -D- 'https://example.com/path?q=test' -o evidence/body.txt

# SQL injection testing only in scope
sqlmap -u 'https://example.com/item?id=1' --batch --level=1 --risk=1
```

## Evidence hygiene

```bash
mkdir -p evidence
# save command + output
{ date -u; echo "CMD: nmap ..."; nmap ...; } | tee evidence/nmap.txt
```

Redact secrets before sharing:

```bash
sed -E 's/(authorization:).*/\1 [REDACTED]/Ig; s/(cookie:).*/\1 [REDACTED]/Ig'
```

## Optional missing tools

Only if user asks to install:

```bash
# examples; pick package source appropriate to host
# apt/pipx/go install ...
```

Do not pretend a missing binary exists.
