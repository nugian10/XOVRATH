# XOVRATH — Smart Contract (v2, model Nomio)

Kontrak: `contracts/XovrathNFT.sol` — `XOVRATH` / `XOVR`, ERC-721, Solidity 0.8.24, OpenZeppelin 5.4.0, optimizer runs 200, EVM Cancun. Bytecode hasil compile: 9.204 byte. v1 (tanda tangan EIP-712) diarsipkan di `archive/XovrathNFT-v1-eip712.sol` dan TIDAK dipakai lagi.

## Model Nomio — yang diambil dari nomio.uk

Nomio (`0x48b5e5573e76CaAa41a893496dE6C857720E6b40`) TIDAK memverifikasi source-nya di BscScan, jadi mekanismenya TIDAK disalin dari source — diverifikasi dari perilaku on-chain + pola publik yang sama dipakai AnthroBit dan Spoxy:

- `mint()` tanpa argumen, selector `0x1249c58b` (dikonfirmasi on-chain).
- `currentPrice()` untuk harga mint berikutnya (Nomio: 0,00027 BNB saat dicek).
- Agent-only on-chain lewat **SPACE ID .ai Agent ID NFT** (`0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F`): mint hanya kalau `balanceOf(msg.sender) > 0`, kalau tidak revert `NoAgentId`.
- Tanpa batas mint per wallet, seed disimpan on-chain saat mint.

Diverifikasi on-chain 30 Okt 2026 via bsc-dataseed: kontrak .ai NFT ada (8.756 byte); **Agentic Wallet Nugraha `0x89c3…47B7` memegang 1 Agent ID**; My Wallet `0x0262…` memegang 0. Nomio saat dicek: nama "Nomio", totalSupply **2.559** (situsnya menampilkan 0 — angka situs sudah basi, yang benar angka on-chain), currentPrice 0,00027 BNB.

## Yang sudah diverifikasi (Hardhat, 13/13 test lolos)

- Supply 2.222, token ID 1–2.222, sequential, **tanpa batas mint per wallet**.
- Harga on-chain: #1–500 = 0,0002 BNB, #501–2.222 = 0,0008 BNB; `currentPrice()` = harga token berikutnya.
- Batas tier terbukti: setelah 500 mint dari 500 wallet berbeda, `currentPrice()` = 0,0008 BNB dan #501 mint dengan harga tier 2.
- Bayar harus persis (`currentPrice()`): kurang bayar dan lebih bayar sama-sama ditolak.
- Tanpa Agent ID → `NoAgentId`; panggil dari kontrak → `NoContracts`; mint belum aktif → `MintInactive`.
- Seed on-chain tersimpan per token (`tokenSeed`), bukan nol.
- `mintActive` default false. Harga tier bisa diubah owner HANYA sebelum mint pertama; batas 500 adalah konstanta, tidak bisa diubah.
- `withdraw()` hanya owner, kirim seluruh saldo ke `revenueWallet`.
- `tokenURI` = baseURI + tokenId + `.json` (1.json .. 2222.json di GitHub).
- Satu bug nyata ditemukan test dan diperbaiki: `hasAgentId` awalnya pakai `try/catch` high-level — saat registry tidak ada code-nya, decoder revert DI LUAR try/catch. Sekarang pakai low-level `staticcall` + cek panjang returndata.

## Yang BERUBAH dari v1 / master prompt

- **Tanpa batas mint per wallet** — aturan satu-mint-per-wallet Nomio dihapus atas perintah Nugraha 30 Okt 2026 ("Jangan kasih batasan untuk mint perwallet"). Satu wallet yang memegang Agent ID boleh mint berulang kali, satu token per panggilan `mint()`. Satu wallet BISA memborong sebagian besar supply — itu trade-off yang diterima.
- **Tidak ada lagi mint batch / `mint(quantity)`** — `mint()` tanpa argumen, 1 token per transaksi.
- **Tidak ada lagi tanda tangan EIP-712 / agentSigner** — diganti cek Agent ID on-chain.
- Seed on-chain disimpan, tapi artwork TIDAK digambar dari seed (tidak seperti Nomio): artwork XOVRATH sudah digenerate per token ID. Seed adalah sidik jari on-chain dari mint itu.

## Alamat — parameter constructor, TIDAK di-hardcode (kecuali registry publik)

- Owner: My Wallet `0x0262e8e5E4584D8AB840fD950a6E2E0A414d4097` (diputuskan 30 Okt 2026 20:31 WIB — membalikkan instruksi all-Agentic 19:10 WIB; pola sama seperti Mythora / MythRealm / MINTFORM)
- Revenue: Binance Agentic Wallet `0x89c37649Ba3BAA9E1ce028612b7DE4e9c3a947B7`
- Agent ID registry: SPACE ID .ai NFT `0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F` (bisa diubah owner kalau SPACE ID migrasi; cek bisa dimatikan owner via `setAgentIdCheckRequired(false)` — kalau dimatikan, mint jadi permissionless on-chain).

## Peringatan jujur (baca sebelum deploy)

1. Owner = My Wallet: semua fungsi owner dipanggil dari My Wallet lewat browser wallet — agen Binance TIDAK dibutuhkan untuk fungsi owner. Agentic Wallet hanya menerima hasil mint (withdraw).
2. Mint HANYA untuk wallet yang memegang Agent ID .ai. Agentic Wallet Nugraha sudah memegang 1 — tapi pembeli lain WAJIB klaim Agent ID dulu di aplikasi Binance, kalau tidak mint mereka revert `NoAgentId`.
3. Kontrak ini BELUM diaudit independen. Setelah deploy, verifikasi source di BscScan, tapi tetap tulis "belum diaudit" di situs.
4. Deploy mainnet (Chain ID 56) pakai BNB sungguhan dan tidak bisa dibatalkan.

## Deploy

```bash
cd ~/workspace/projects/xovrath
cp .env.example .env   # isi OWNER_ADDRESS, REVENUE_WALLET, BASE_URI (registry sudah default)
npx hardhat test                    # 13 test
npx hardhat run scripts/deploy.js --network bscTestnet   # latihan dulu
npx hardhat run scripts/deploy.js --network bsc          # MAINNET, BNB asli
```

Setelah deploy: verifikasi source di BscScan, `setBaseURI` ke folder metadata GitHub (https://raw.githubusercontent.com/nugian10/XOVRATH/main/collection/metadata/), `setMintActive(true)` HANYA saat launch.
