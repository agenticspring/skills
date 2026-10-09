// Leading-zero-bits SHA-256 PoW miner (SHA-NI accelerated via OpenSSL SHA256_Transform).
//
// Built for the HashBroker layout, but the pattern generalises: any drop that asks for
// "sha256(fixed-prefix ‖ nonce ‖ fixed-suffix) has >= N leading zero bits" works by
// editing build_blocks() only.
//
// Build:  gcc -O3 -march=native -pthread -o hb_mine hb_mine.c -lcrypto
// Run:    ./hb_mine <addr_hex> <challenge_hex> <difficulty_bits> <threads> <max_seconds>
//         (max_seconds 0 = run forever)
//
// stdout: "FOUND <16-hex nonce> <bits>"  exit 0
// stderr: "STAT <hashes> <best_bits> <rate_mhs>" every ~3s, and "TIMEOUT ..." exit 2
//
// VERIFY BEFORE TRUSTING: run it against a known-successful on-chain proof
// (addr, challenge, nonce) and confirm the digest matches. The self-check in main()
// does exactly that for the reference vector.
#define OPENSSL_SUPPRESS_DEPRECATED 1
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
#include <pthread.h>
#include <stdatomic.h>
#include <openssl/sha.h>

// ---- message template (edit for a different drop) -------------------------------
// block1 = addr(20) ‖ 0x00*24 ‖ nonceHi(4 BE) ‖ nonceLo(4 BE) ‖ challenge[0:12]
// block2 = challenge[12:32] ‖ 0x80 ‖ 0x00*41 ‖ 0x02A0   (length = 84 bytes = 672 bits)
static uint8_t BLK1_TMPL[64];
static uint8_t BLK2[64];

static const uint32_t IV[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
                               0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};

static atomic_int      g_stop = 0;
static atomic_int      g_found = 0;
static atomic_ullong   g_found_nonce = 0;
static atomic_uint     g_found_bits = 0;
static atomic_ullong   g_total = 0;
static atomic_uint     g_best = 0;
static uint64_t        g_stride = 1;
static uint64_t        g_start = 0;
static int             g_target = 40;

static inline uint32_t lz32(uint32_t v) { return v ? (uint32_t)__builtin_clz(v) : 32u; }

// leading zero bits of the 32-byte digest held in ctx.h[0..7] (big-endian words)
static inline uint32_t leading_zero_bits(const SHA256_CTX *ctx) {
    uint32_t bits = 0;
    for (int i = 0; i < 8; i++) {
        uint32_t v = ctx->h[i];
        if (v == 0) { bits += 32; continue; }
        return bits + lz32(v);
    }
    return 256;
}

typedef struct { int id; int secs; } arg_t;

static void *worker(void *p) {
    arg_t *a = (arg_t *)p;
    SHA256_CTX ctx;
    uint8_t blk1[64];
    memcpy(blk1, BLK1_TMPL, 64);

    uint64_t nonce = g_start + (uint64_t)a->id;
    uint64_t n = 0;
    uint32_t localbest = 0;
    time_t t0 = time(NULL), tlast = t0;

    while (!atomic_load(&g_stop)) {
        for (int i = 0; i < 40000; i++) {
            // nonce as uint64, high 32 bits first
            blk1[44] = (uint8_t)(nonce >> 56); blk1[45] = (uint8_t)(nonce >> 48);
            blk1[46] = (uint8_t)(nonce >> 40); blk1[47] = (uint8_t)(nonce >> 32);
            blk1[48] = (uint8_t)(nonce >> 24); blk1[49] = (uint8_t)(nonce >> 16);
            blk1[50] = (uint8_t)(nonce >> 8);  blk1[51] = (uint8_t)(nonce);

            memcpy(ctx.h, IV, sizeof(IV));
            SHA256_Transform(&ctx, blk1);
            SHA256_Transform(&ctx, BLK2);

            uint32_t bits = leading_zero_bits(&ctx);
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
            fprintf(stderr, "STAT %llu %u %.2f\n", (unsigned long long)n,
                    atomic_load(&g_best), (double)n / (double)(now - t0 > 0 ? now - t0 : 1) / 1e6);
            fflush(stderr);
        }
        if (a->secs > 0 && now - t0 >= a->secs) break;
    }
    atomic_fetch_add(&g_total, n);
    return NULL;
}

static void build_blocks(const char *addr_hex, const char *ch_hex) {
    uint8_t addr[20], ch[32];
    for (int i = 0; i < 20; i++) sscanf(addr_hex + 2 * i, "%2hhx", &addr[i]);
    for (int i = 0; i < 32; i++) sscanf(ch_hex + 2 * i, "%2hhx", &ch[i]);

    memset(BLK1_TMPL, 0, 64);
    memcpy(BLK1_TMPL, addr, 20);          // bytes 0..19
    // bytes 20..43 stay zero, 44..51 = nonce (patched per iteration), 52..63 = challenge[0:12]
    memcpy(BLK1_TMPL + 52, ch, 12);

    memset(BLK2, 0, 64);
    memcpy(BLK2, ch + 12, 20);            // challenge[12:32]
    BLK2[20] = 0x80;                      // pad
    BLK2[62] = 0x02; BLK2[63] = 0xA0;     // 672 bits
}

int main(int argc, char **argv) {
    if (argc < 6) {
        fprintf(stderr, "usage: %s <addr_hex> <challenge_hex> <difficulty> <threads> <max_seconds>\n", argv[0]);
        return 1;
    }
    const char *addr_hex = argv[1], *ch_hex = argv[2];
    g_target = atoi(argv[3]);
    int threads = atoi(argv[4]);
    int secs = atoi(argv[5]);

    build_blocks(addr_hex, ch_hex);

    // self-check against a known-successful proof (addr/challenge/nonce -> expected digest)
    {
        static const char *V_ADDR = "8f2daf3a56f42127695ad21215601e3cc87a7a2f";
        static const char *V_CH   = "96f611702febc5376a0056b33d448e27d000390be94bf3350107eb249607ad6d";
        static const uint64_t V_NONCE = 0xcae298007226ba59ULL;
        uint8_t save1[64], save2[64];
        memcpy(save1, BLK1_TMPL, 64); memcpy(save2, BLK2, 64);
        build_blocks(V_ADDR, V_CH);
        SHA256_CTX ctx;
        memcpy(ctx.h, IV, sizeof(IV));
        uint8_t b1[64]; memcpy(b1, BLK1_TMPL, 64);
        b1[44] = (uint8_t)(V_NONCE >> 56); b1[45] = (uint8_t)(V_NONCE >> 48);
        b1[46] = (uint8_t)(V_NONCE >> 40); b1[47] = (uint8_t)(V_NONCE >> 32);
        b1[48] = (uint8_t)(V_NONCE >> 24); b1[49] = (uint8_t)(V_NONCE >> 16);
        b1[50] = (uint8_t)(V_NONCE >> 8);  b1[51] = (uint8_t)(V_NONCE);
        SHA256_Transform(&ctx, b1);
        SHA256_Transform(&ctx, BLK2);
        fprintf(stderr, "SELFCHECK %08x%08x%08x%08x%08x%08x%08x%08x bits=%u (expect 0000000003b323e7... bits=38)\n",
                ctx.h[0], ctx.h[1], ctx.h[2], ctx.h[3], ctx.h[4], ctx.h[5], ctx.h[6], ctx.h[7],
                leading_zero_bits(&ctx));
        memcpy(BLK1_TMPL, save1, 64); memcpy(BLK2, save2, 64);
    }

    g_stride = (uint64_t)threads;
    g_start = ((uint64_t)time(NULL) * 2654435761ULL) ^ ((uint64_t)getpid() << 17);

    pthread_t th[64];
    arg_t ar[64];
    for (int i = 0; i < threads; i++) { ar[i].id = i; ar[i].secs = secs; pthread_create(&th[i], NULL, worker, &ar[i]); }
    for (int i = 0; i < threads; i++) pthread_join(th[i], NULL);

    if (atomic_load(&g_found)) {
        printf("FOUND %016llx %u\n", (unsigned long long)atomic_load(&g_found_nonce),
               atomic_load(&g_found_bits));
        fflush(stdout);
        return 0;
    }
    fprintf(stderr, "TIMEOUT %llu hashes, best %u bits\n",
            (unsigned long long)atomic_load(&g_total), atomic_load(&g_best));
    return 2;
}
