// SHA-256 PoW kernel for the non-keccak "leading zero bits" mint variant.
//
// Message layout (verified against real winning txs — do NOT assume, re-verify per contract):
//   msg = address(20) || zeros(24) || nonceHi(4 BE) || nonceLo(4 BE) || challenge[0:12] || challenge[12:32]
//   win when sha256(msg) has >= difficulty LEADING ZERO BITS
// Address is msg.sender, so a proof is bound to the minter and cannot be stolen.
// Block 2 (challenge[12:32] + padding + bit length) is CONSTANT per challenge.
//
// Build (SHA-NI path via OpenSSL; ~10 MH/s per core on a CPU with sha_ni):
//   gcc -O3 -march=native -pthread -o hb_mine sha256_pow_sa_miner.c -lcrypto
//
// Usage:
//   ./hb_mine <addr_hex> <challenge_hex> <difficulty> <threads> <max_seconds>
//   stdout: "FOUND <nonce_hex> <bits>"   exit 0
//   stderr: "STAT <hashes> <bestbits> <MH/s>" every ~3 s; "TIMEOUT ..." exit 2
//
// ALWAYS self-check first: run with a real winning (address, challenge, nonce) triple and
// confirm the printed digest matches an independent implementation before mining for real.
#define OPENSSL_SUPPRESS_DEPRECATED 1
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include <pthread.h>
#include <stdatomic.h>
#include <openssl/sha.h>

static uint8_t BLK1_TMPL[64];
static uint8_t BLK2[64];
static int g_target = 41;
static atomic_int g_stop = 0;
static atomic_int g_found = 0;
static atomic_ullong g_found_nonce = 0;
static atomic_uint g_found_bits = 0;
static atomic_ullong g_total = 0;
static atomic_uint g_best = 0;
static uint64_t g_stride = 1;
static uint64_t g_start = 0;

static const uint32_t IV[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
                               0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};

static inline uint32_t lz32(uint32_t v) { return v ? (uint32_t)__builtin_clz(v) : 32u; }

typedef struct { int id; int secs; } arg_t;

static void *worker(void *p) {
    arg_t *a = (arg_t *)p;
    SHA256_CTX ctx;
    uint8_t blk1[64];
    memcpy(blk1, BLK1_TMPL, 64);
    uint64_t nonce = g_start + (uint64_t)a->id;
    uint64_t n = 0;
    time_t t0 = time(NULL);
    time_t tlast = t0;
    uint32_t localbest = 0;

    while (!atomic_load(&g_stop)) {
        for (int i = 0; i < 40000; i++) {
            // nonce occupies bytes 44..51 of block 1, big-endian
            blk1[44] = (uint8_t)(nonce >> 56); blk1[45] = (uint8_t)(nonce >> 48);
            blk1[46] = (uint8_t)(nonce >> 40); blk1[47] = (uint8_t)(nonce >> 32);
            blk1[48] = (uint8_t)(nonce >> 24); blk1[49] = (uint8_t)(nonce >> 16);
            blk1[50] = (uint8_t)(nonce >> 8);  blk1[51] = (uint8_t)(nonce);

            // 2 blocks per candidate; reset state to IV, transform block1 then the constant block2
            memcpy(ctx.h, IV, sizeof(IV));
            SHA256_Transform(&ctx, blk1);
            SHA256_Transform(&ctx, BLK2);

            uint32_t h0 = ctx.h[0], bits;
            if (h0) bits = lz32(h0);
            else {
                bits = 32; uint32_t h1 = ctx.h[1];
                if (h1) bits += lz32(h1);
                else {
                    bits = 64; uint32_t h2 = ctx.h[2];
                    if (h2) bits += lz32(h2);
                    else { bits = 96; uint32_t h3 = ctx.h[3]; bits += h3 ? lz32(h3) : 32; }
                }
            }
            if (bits > localbest) {
                localbest = bits;
                if (bits > atomic_load(&g_best)) atomic_store(&g_best, bits);
            }
            if (bits >= (uint32_t)g_target) {
                if (atomic_load(&g_found) == 0) {
                    atomic_store(&g_found_nonce, nonce);
                    atomic_store(&g_found_bits, bits);
                    atomic_store(&g_found, 1);
                }
                atomic_store(&g_stop, 1);
                break;
            }
            nonce += g_stride;
            n++;
        }
        time_t now = time(NULL);
        if (now - tlast >= 3) {
            tlast = now;
            uint64_t el = (uint64_t)(now - t0 ? now - t0 : 1);
            fprintf(stderr, "STAT %llu %u %.2f\n", (unsigned long long)n,
                    atomic_load(&g_best), (double)n / (double)el / 1e6);
            fflush(stderr);
        }
        if (a->secs > 0 && now - t0 >= a->secs) break;
    }
    atomic_fetch_add(&g_total, n);
    return NULL;
}

int main(int argc, char **argv) {
    if (argc < 6) {
        fprintf(stderr, "usage: %s <addr_hex> <challenge_hex> <difficulty> <threads> <max_seconds>\n", argv[0]);
        return 1;
    }
    g_target = atoi(argv[3]);
    int threads = atoi(argv[4]);
    int secs = atoi(argv[5]);

    uint8_t addr[20], ch[32];
    for (int i = 0; i < 20; i++) sscanf(argv[1] + 2 * i, "%2hhx", &addr[i]);
    for (int i = 0; i < 32; i++) sscanf(argv[2] + 2 * i, "%2hhx", &ch[i]);

    memset(BLK1_TMPL, 0, 64);
    memcpy(BLK1_TMPL, addr, 20);        // bytes 0..19
    memcpy(BLK1_TMPL + 52, ch, 12);     // bytes 52..63 = challenge[0:12]
    memset(BLK2, 0, 64);
    memcpy(BLK2, ch + 12, 20);          // bytes 0..19 = challenge[12:32]
    BLK2[20] = 0x80;                    // padding
    BLK2[62] = 0x02; BLK2[63] = 0xA0;   // 672 bits total message length

    g_stride = (uint64_t)threads;
    // scattered start so several instances don't duplicate work
    g_start = ((uint64_t)time(NULL) * 2654435761ULL) ^ ((uint64_t)getpid() << 17);

    pthread_t th[64]; arg_t ar[64];
    for (int i = 0; i < threads; i++) { ar[i].id = i; ar[i].secs = secs; pthread_create(&th[i], NULL, worker, &ar[i]); }
    for (int i = 0; i < threads; i++) pthread_join(th[i], NULL);

    if (atomic_load(&g_found)) {
        printf("FOUND %016llx %u\n", (unsigned long long)atomic_load(&g_found_nonce), atomic_load(&g_found_bits));
        fflush(stdout);
        return 0;
    }
    fprintf(stderr, "TIMEOUT %llu hashes, best %u bits\n",
            (unsigned long long)atomic_load(&g_total), atomic_load(&g_best));
    return 2;
}
