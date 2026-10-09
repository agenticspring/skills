package main

import (
	"crypto/ecdsa"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"math/big"
	"math/rand"
	"net/http"
	"os"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"golang.org/x/crypto/sha3"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/crypto"
)

const (
	RPC_URL    = "https://your-private-rpc.example.com/v2/YOUR_KEY"
	CONTRACT   = "0xD69be8d7c6d0e8216Dc2C151834E4150313260Cc" // Hashwood contract
	MINT_PRICE = 50000000000000                                // 0.00005 ETH
	GAS_LIMIT  = 60000
	CHAIN_ID   = 4663 // Robinhood Chain
	THREADS    = 6
)

var httpClient = &http.Client{Timeout: 10 * time.Second}
var contractAddr = common.HexToAddress(CONTRACT)
var gpCacheHex string
var lastGasUpdate time.Time
var gpMu sync.Mutex

func rpc(method string, params []interface{}) (json.RawMessage, error) {
	req := map[string]interface{}{
		"jsonrpc": "2.0", "method": method, "params": params, "id": 1,
	}
	data, _ := json.Marshal(req)
	resp, err := httpClient.Post(RPC_URL, "application/json", strings.NewReader(string(data)))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	var rpcResp struct {
		Result json.RawMessage       `json:"result"`
		Error  *struct{ Message string } `json:"error"`
	}
	json.Unmarshal(body, &rpcResp)
	if rpcResp.Error != nil {
		return nil, fmt.Errorf(rpcResp.Error.Message)
	}
	return rpcResp.Result, nil
}

func getWork() ([32]byte, [32]byte) {
	var ch, tg [32]byte
	c, _ := ethCall("0x8ae0368b") // challengeNumber()
	t, _ := ethCall("0x8a769d35") // miningTarget()
	if len(c) > 2 { b, _ := hex.DecodeString(c[2:]); copy(ch[:], b[:32]) }
	if len(t) > 2 { b, _ := hex.DecodeString(t[2:]); copy(tg[:], b[:32]) }
	return ch, tg
}

func ethCall(data string) (string, error) {
	params := []interface{}{
		map[string]interface{}{"to": CONTRACT, "data": data}, "latest",
	}
	res, err := rpc("eth_call", params)
	if err != nil { return "", err }
	var s string
	json.Unmarshal(res, &s)
	return s, nil
}

func checkValid(nonce [32]byte, addr common.Address) bool {
	// checkMintSolution(uint256,address) — FREE eth_call, no gas cost
	data := "0x9d7a7cc6" + common.Bytes2Hex(nonce[:]) + "000000000000000000000000" + common.Bytes2Hex(addr.Bytes())
	r, err := ethCall(data)
	return err == nil && len(r) > 66 && r[len(r)-1] == '1'
}

func keccak256(data []byte) []byte {
	h := sha3.NewLegacyKeccak256()
	h.Write(data)
	return h.Sum(nil)
}

func minerThread(id int, challenge, target [32]byte, addrHex string,
	found *int32, outNonce, outDigest *[32]byte, wg *sync.WaitGroup) {
	defer wg.Done()

	msg := make([]byte, 84)
	copy(msg[:32], challenge[:])
	addr, _ := hex.DecodeString(addrHex[2:])
	copy(msg[32:52], addr)

	rng := rand.New(rand.NewSource(time.Now().UnixNano() + int64(id)*9999))
	start := rng.Uint64() % 1e17

	for nonce := start; nonce < start+1000000/uint64(THREADS); nonce++ {
		if atomic.LoadInt32(found) == 1 { return }
		// uint256 big-endian: nonce value in last 8 bytes, zeros before
		for i := 52; i < 76; i++ { msg[i] = 0 }
		msg[76] = byte(nonce >> 56)
		msg[77] = byte(nonce >> 48)
		msg[78] = byte(nonce >> 40)
		msg[79] = byte(nonce >> 32)
		msg[80] = byte(nonce >> 24)
		msg[81] = byte(nonce >> 16)
		msg[82] = byte(nonce >> 8)
		msg[83] = byte(nonce)

		hash := keccak256(msg)
		win := true
		for i := 0; i < 32; i++ {
			if hash[i] > target[i] { win = false; break }
			if hash[i] < target[i] { break }
		}
		if win && atomic.CompareAndSwapInt32(found, 0, 1) {
			copy(outNonce[:], msg[52:84])
			copy(outDigest[:], hash)
			return
		}
	}
}

func sendMint(nonce, digest []byte, pk *ecdsa.PrivateKey, gasBoost int64) (string, bool) {
	from := crypto.PubkeyToAddress(pk.PublicKey)
	txData, _ := hex.DecodeString(("0x1801fbe5" + hex.EncodeToString(nonce) + hex.EncodeToString(digest))[2:])

	// Fetch nonce from chain (never cache — nonce desync kills all TXes)
	var nonceHex string
	rawNonce, _ := rpc("eth_getTransactionCount", []interface{}{from.Hex(), "pending"})
	json.Unmarshal(rawNonce, &nonceHex)
	nonceNum := new(big.Int).SetBytes(common.FromHex(nonceHex)).Uint64()

	// Cache gas price, refresh every 30s
	var gpHex string
	gpMu.Lock()
	if gpCacheHex == "" || time.Since(lastGasUpdate) > 30*time.Second {
		rawGas, _ := rpc("eth_gasPrice", []interface{}{})
		json.Unmarshal(rawGas, &gpHex)
		gpCacheHex = gpHex
		lastGasUpdate = time.Now()
	} else {
		gpHex = gpCacheHex
	}
	gpMu.Unlock()
	gasPrice := new(big.Int).SetBytes(common.FromHex(gpHex))
	if gasBoost > 1 {
		gasPrice.Mul(gasPrice, big.NewInt(gasBoost))
	}

	tx := types.NewTransaction(nonceNum, contractAddr, big.NewInt(MINT_PRICE), GAS_LIMIT, gasPrice, txData)
	signer := types.NewEIP155Signer(big.NewInt(CHAIN_ID))
	signedTx, _ := types.SignTx(tx, signer, pk)
	rlpData, _ := signedTx.MarshalBinary()

	rawResult, _ := rpc("eth_sendRawTransaction", []interface{}{"0x" + hex.EncodeToString(rlpData)})
	if rawResult == nil { return "TX_FAIL", false }
	var txHash string
	json.Unmarshal(rawResult, &txHash)
	return "TX_SENT: " + txHash[:20] + "...", true
}

func main() {
	pkHex := strings.TrimSpace(func() string {
		b, _ := os.ReadFile("/root/miner/.env")
		s := string(b)
		if !strings.HasPrefix(s, "0x") { s = "0x" + s }
		return s
	}())

	pk, err := crypto.HexToECDSA(pkHex[2:])
	if err != nil { fmt.Println("PK error:", err); os.Exit(1) }
	addr := crypto.PubkeyToAddress(pk.PublicKey)

	fmt.Printf("Go PoW Miner — Address: %s\n", addr.Hex())
	addrHex := addr.Hex()
	lastBlock := uint64(0)
	lastBlkCheck := time.Now()

	for {
		// Check block number every 500ms (avoid RPC rate limit)
		var blkHex string
		blockNum := lastBlock
		if time.Since(lastBlkCheck) > 500*time.Millisecond {
			rawBlk, _ := rpc("eth_blockNumber", []interface{}{})
			json.Unmarshal(rawBlk, &blkHex)
			blockNum = new(big.Int).SetBytes(common.FromHex(blkHex)).Uint64()
			lastBlkCheck = time.Now()
			if blockNum > lastBlock && lastBlock > 0 {
				fmt.Printf("[%s] Block %d → %d\n", time.Now().Format("15:04:05"), lastBlock, blockNum)
			}
			lastBlock = blockNum
		}

		challenge, target := getWork()
		if challenge == [32]byte{} { time.Sleep(2 * time.Second); continue }

		var found int32
		var resultNonce, resultDigest [32]byte
		var wg sync.WaitGroup
		ts := time.Now()

		for i := 0; i < THREADS; i++ {
			wg.Add(1)
			go minerThread(i, challenge, target, addrHex, &found, &resultNonce, &resultDigest, &wg)
		}
		wg.Wait()
		elapsed := time.Since(ts)

		if atomic.LoadInt32(&found) == 1 {
			// Optional: checkValid before submitting (free eth_call, saves gas on expired)
			// if !checkValid(resultNonce, addr) { continue }
			status, _ := sendMint(resultNonce[:], resultDigest[:], pk, 2)
			fmt.Printf("[%s] %s (%v)\n", time.Now().Format("15:04:05"), status, elapsed)
		}
	}
}
