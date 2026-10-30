# XOVRATH v2 — Prompt siap tempel untuk agen Binance kamu (MAINNET)

Salin seluruh blok di bawah ini ke agen yang sudah dipasangkan
dengan Agentic Wallet kamu (bukan ke Muse — Muse tidak bisa
dipasangkan ke Agentic Wallet dan tidak bisa tanda tangan sebagai
Agentic Wallet). Agen ini yang akan tanda tangan sebagai Agentic
Wallet. Jangan kirim seed phrase, private key, atau pairing code
ke siapa pun, termasuk ke chat ini.

Model kontrak v2 mengikuti Nomio (nomio.uk): mint() tanpa argumen,
cek Agent ID on-chain, tanpa batas mint per wallet, seed disimpan on-chain.

> Catatan untuk agen: baca dulu, konfirmasi dulu, baru eksekusi.
> Satu transaksi pun tidak boleh dikirim tanpa konfirmasi pengguna
> untuk transaksi itu.

---

```
PERINTAH SAYA: Deploy XOVRATH v2 saya LANGSUNG ke BNB Smart Chain
Mainnet (chain ID 56) dengan BNB asli. JANGAN deploy ke Testnet
(chain ID 97) dalam kondisi apa pun. Jangan deploy kontrak v1
(EIP-712) — v1 sudah dibatalkan dan diarsipkan. Deploy v2 ini.

Kontrak ini DIPAKSA harus pakai Agentic Wallet saya untuk owner
dan revenue. Jangan pakai pola lama (owner My Wallet). Jangan ganti
alamat apa pun tanpa konfirmasi saya.

Langkah 1 — Verifikasi dulu, jangan transaksi dulu:
- Cek status login Agentic Wallet (baw CLI), alamat wallet, saldo BNB,
  dan status Developer Mode. Laporkan semuanya ke saya.
- Cek juga: wallet ini memegang SPACE ID .ai Agent ID (kontrak
  0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F, balanceOf harus > 0).
  Kalau belum punya Agent ID, bantu saya klaim di aplikasi Binance
  dulu — tanpa Agent ID, mint di kontrak ini akan gagal.
- Jika belum login, bantu saya login lewat QR + pairing code di aplikasi
  Binance (kode pairing hanya dicocokkan di aplikasi, bukan dikirim ke chat).
- Jika login / koneksi agen GAGAL di langkah ini, BERHENTI dan laporkan
  persis apa yang tampil di layar (screenshot + pesan error) — jangan
  coba-coba cara lain tanpa persetujuan saya.
- Cek harga gas saat ini dan hitung perkiraan biaya deploy. Jika saldo
  BNB tidak cukup untuk gas deploy, BERHENTI dan laporkan — jangan pakai
  dana lain tanpa persetujuan saya.

Langkah 2 — Dapatkan dan periksa kode:
- File kontrak akan saya kirim: XovrathNFT.sol v2 (ERC-721, Solidity
  0.8.24, OpenZeppelin 5.4.0, supply 2.222, harga 2 tier on-chain:
  token #1–500 = 0,0002 BNB, #501–2.222 = 0,0008 BNB, mint() tanpa
  argumen, cek Agent ID on-chain, tanpa batas mint per wallet, seed on-chain).
- Siapkan proyek Hardhat dengan file itu (optimizer enabled, runs 200,
  EVM cancun), install @openzeppelin/contracts@5.4.0, lalu jalankan:
  npx hardhat compile, lalu npx hardhat test.
  HARUS 13/13 test lolos, termasuk test batas tier: setelah 500 mint,
  currentPrice() = 0,0008 BNB dan #501 mint dengan harga tier 2.
  Jika ada test gagal, BERHENTI dan laporkan.
- Gambar NFT dan metadata SUDAH ada di repo GitHub lokal dan TIDAK dibutuhkan untuk
  deploy kontrak — jangan berhenti karena itu.

Langkah 3 — Konfirmasi ke saya SEBELUM deploy (jangan ditebak):
- Pola yang sudah saya PAKSA: kamu (Agentic Wallet) yang deploy dan
  bayar gas, DAN owner = revenue = Agentic Wallet ini.
  Agent ID registry = SPACE ID .ai NFT
  0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F (jangan diganti).
  Konfirmasikan alamat-alamat ini ke saya, dan deploy HANYA setelah
  saya menjawab "ya, alamatnya benar":
  Owner:         0x89c37649Ba3BAA9E1ce028612b7DE4e9c3a947B7
  Revenue:       0x89c37649Ba3BAA9E1ce028612b7DE4e9c3a947B7
  Agent registry: 0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F
- Base URI awal: kosong ("") — akan di-set belakangan ke folder metadata GitHub,
  lewat setBaseURI oleh owner (kamu).
- Deploy mainnet HANYA setelah saya menjawab "ya, alamatnya benar"
  DAN "ya, deploy mainnet".

Langkah 4 — Deploy mainnet saja:
- Deploy XovrathNFT dengan constructor
  (initialOwner, revenueWallet, agentIdRegistry, baseURI)
  = (0x89c37649Ba3BAA9E1ce028612b7DE4e9c3a947B7,
     0x89c37649Ba3BAA9E1ce028612b7DE4e9c3a947B7,
     0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F, "").
- Laporkan: alamat kontrak, hash transaksi deploy, owner, revenue
  wallet, agent ID registry, totalSupply (harus 0), mintActive (harus
  false), agentIdCheckRequired (harus true), dan biaya gas yang
  benar-benar terpakai.
- Verifikasi kontrak di BscScan (mainnet) dan kirim link verifikasinya.
- Cek fungsi baca: currentPrice() harus 0,0002 BNB, priceForTokenId(500)
  harus 0,0002 BNB, priceForTokenId(501) harus 0,0008 BNB,
  MAX_SUPPLY() harus 2222, TIER_1_END() harus 500,
  hasAgentId(0x89c37649Ba3BAA9E1ce028612b7DE4e9c3a947B7) harus true.

DILARANG:
- Deploy ke Testnet (97) dalam kondisi apa pun, mengaktifkan mint
  (setMintActive), setBaseURI, withdraw, atau transaksi lain apa pun
  tanpa instruksi dan konfirmasi saya yang terpisah untuk tiap transaksi itu.
- Deploy kontrak v1 (EIP-712 / agentSigner) — v1 sudah dibatalkan.
- Meminta seed phrase, private key, password, atau pairing code saya.
- Mengarang alamat kontrak, hash transaksi, atau status verifikasi.
- Mengganti owner / revenue / agent registry ke alamat lain.
```

---

Setelah agen melaporkan alamat mainnet, kirim alamat itu ke Muse di
chat ini — Muse bisa memverifikasi on-chain (read-only) dan
menyambungkan alamat itu ke website XOVRATH. Aktivasi mint tetap
tertahan sampai repo GitHub terisi dan kamu menyetujuinya.

Catatan Muse (bukan bagian dari prompt): kontrak v2 ini 13/13 test
lolos. Agentic Wallet Nugraha sudah memegang 1 Agent ID .ai
(diverifikasi on-chain 30 Okt 2026), jadi agennya bisa mint.
Koneksi agen Binance-nya pernah gagal di langkah 1 pada 29 Okt 2026
— kalau gagal login lagi, yang perlu diperbaiki adalah koneksi/pairing
agen itu di aplikasi Binance, bukan kontraknya.
