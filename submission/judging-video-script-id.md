# Naskah Video Juri — MarketOps ID (Bahasa Indonesia)

**Durasi target: 2 menit 50 detik.** Batas keras lomba 3 menit, jadi tersisa
10 detik margin untuk jeda napas dan transisi.

**Semua angka di naskah ini sudah terverifikasi** terhadap run publik per
2026-09-01. Jangan mengubah angka tanpa memverifikasi ulang ke sumbernya —
seluruh kekuatan submission ini justru terletak pada bukti yang bisa dicek.

---

## Tabel Naskah

| Waktu | Yang tampil di layar | Narasi |
|---|---|---|
| **00:00–00:12** | Judul + ilustrasi meja analis dengan banyak layar terpisah. | "Analis riset saham Indonesia memulai hari dengan pertanyaan yang sama: dari begitu banyak sinyal yang tersebar di layar berbeda, mana yang harus saya periksa lebih dulu? MarketOps ID menjawab pertanyaan itu." |
| **00:12–00:26** | Diagram ketergantungan Sectors: 6 kapabilitas menyatu jadi satu antrean. | "Sumbernya satu: Sectors Financial API versi dua. Enam kapabilitas — filing, suspensi, penggerak harga harian, berita per emiten, aliran dana asing, dan aksi korporasi — digabung menjadi satu antrean riset." |
| **00:26–00:42** | Dashboard kartu P1. **Banner wajib terlihat: "SANITIZED HISTORICAL REPLAY — NOT LIVE MARKET DATA".** | "Bukti dikorelasikan per ticker kanonik, lalu dinilai dengan Research Attention Score yang deterministik. Skornya transparan: setiap komponen menampilkan alasan dan bukti sumbernya. Yang Anda lihat ini replay historis tersanitasi, bukan data pasar langsung." |
| **00:42–00:56** | Kartu FLMC 100/100 (suspensi), lalu ANTM 75/100 dengan rincian komponen. | "Suspensi bursa langsung mengangkat emiten ke P1. Aturan lain menimbang filing material, lonjakan harga, anomali aliran asing, berita, aksi korporasi, dan watchlist meja riset. Ini triase riset, bukan rekomendasi investasi." |
| **00:56–01:14** | Dua ringkasan run berdampingan, kolom duplikat disorot. | "Deduplikasi bekerja lintas siklus, bukan hanya di dalam satu run. Run terjadwal pertama mendeteksi enam puluh tiga kejadian, lima puluh sembilan di antaranya baru. Run berikutnya menekan empat puluh duplikat, dan run ketiga menekan tiga puluh. Analis tidak pernah menerima kejadian yang sama dua kali." |
| **01:14–01:34** | **Actions history: tiga baris dengan event `schedule`.** Lalu satu halaman detail run. | "Inilah bukti Track 2. Tiga eksekusi GitHub Actions asli dengan event schedule, berjalan tanpa disentuh siapa pun, memakai state produksi dan tetap di dalam anggaran lima belas kredit. Dua di antaranya dipicu jendela observasi sementara — tetap event schedule asli, bukan dispatch manual." |
| **01:34–01:50** | Tangkapan pengiriman Discord pasca-remediasi (dari run `33155463943`). | "Pengirimannya nyata. Delapan belas kartu terkirim dalam empat batch, nol error. Setiap kartu membawa skor, alasan, dan tautan bukti, sehingga analis bisa langsung menelusuri sumbernya." |
| **01:50–02:14** | Ringkasan SEC-001: kutipan temuan → diff perbaikan → gate `Enforce artifact safety` hijau. | "Kami juga menemukan masalah pada diri kami sendiri. Log bawaan httpx menuliskan URL webhook secara utuh ke artefak publik. Artefaknya kami hapus, webhook-nya kami cabut, penjadwalnya kami matikan. Perbaikannya dua lapis: formatter yang meredaksi rahasia, dan pemindai artefak fail-closed yang menggagalkan workflow bila masih menemukan kredensial." |
| **02:14–02:32** | Kartu hasil tes lokal + CI publik hijau + output pemindai `findings=0`. | "Empat ratus tes lulus dengan cakupan sembilan puluh lima koma enam dua persen, CI publik hijau, dan artefak setiap run terjadwal dipindai dua kali oleh dua pemindai independen. Ketiganya nol temuan." |
| **02:32–02:50** | Diagram arsitektur, lalu disclaimer layar penuh. | "MarketOps ID mengubah bukti dari Sectors menjadi antrean riset yang berjalan sendiri, dapat diaudit, dan jujur tentang batasannya. Keputusan investasi tetap sepenuhnya di tangan manusia. MarketOps ID tidak memberi rekomendasi investasi dan tidak mengeksekusi transaksi." |

---

## Aturan Kejujuran — Jangan Dilanggar Saat Menyunting

Bagian ini yang membedakan submission ini. Kalau durasi kepanjangan, **potong
bagian fitur, jangan potong bagian pengungkapan.**

1. **Banner fixture wajib terbaca** setiap kali footage replay muncul. Jangan
   pernah menampilkan data fixture tanpa label seolah-olah itu data pasar hidup.
2. **Jangan hapus pengungkapan SEC-001.** Menampilkan kerentanan yang ditemukan
   sendiri lalu ditutup dengan bukti justru menaikkan kredibilitas, bukan
   menurunkannya.
3. **Sebutkan asal dua run Senin.** Keduanya berasal dari cron observasi
   sementara (commit `10ff99b`, kini sudah dihapus). Itu tetap event `schedule`
   asli — tapi menyembunyikannya membuat rekaman terkesan lebih kuat dari
   kenyataan.
4. **Jangan pakai `discord-result.png` lama** sebagai bukti pengiriman terkini.
   Itu aset historis dari sebelum remediasi. Gunakan tangkapan baru dari run
   `33155463943`.
5. **Jangan bilang "OK" kalau layarnya "PARTIAL".** Semua run live berstatus
   `PARTIAL` karena cap satu halaman berita yang memang disengaja. Kalau statusnya
   terlihat di layar, biarkan; jangan pilih frame yang menyesatkan.
6. **Disclaimer wajib muncul** minimal sekali sebagai teks, dan sekali diucapkan.

---

## Aset yang Harus Disiapkan Sebelum Merekam

| Aset | Status | Cara memperoleh |
|---|---|---|
| `actions-history.png` | **Belum ada** | Tab Actions → filter workflow "MarketOps scheduled triage" → tangkap tiga baris `schedule` |
| `scheduled-run.png` | **Belum ada** | Buka run `33472247776` → tangkap halaman detail (workflow, trigger, status, waktu) |
| Tangkapan Discord baru | **Belum ada** | Dari hasil run `33155463943` di channel Anda |
| `dashboard.png`, `p1-card.png` | Sudah ada | `marketops serve` → `http://127.0.0.1:8000` |
| `test-pass-local.png` | Sudah ada | Sudah menampilkan 400 tes / 95.62% |
| `architecture.png` | Sudah ada | — |

---

## Tips Perekaman

- **Kecepatan bicara:** naskah ini 349 kata untuk 170 detik, jadi rata-rata
  **2,05 kata per detik** — tempo penjelasan yang tenang, bukan terburu-buru.
  Segmen terpadat (00:56–01:14, dedup) ada di 2,50 kata/detik; empat segmen
  terakhir sengaja lebih longgar (1,6–1,9) supaya ada ruang jeda saat visual
  bukti perlu dibaca juri. Kalau Anda bicara cepat, jangan mempercepat — pakai
  sisa waktunya untuk menahan shot lebih lama.
- **Rekam audio terpisah** dari tangkapan layar, lalu sinkronkan. Jauh lebih
  mudah daripada mengulang seluruh take karena satu kalimat tersandung.
- **Segmen 01:14–01:34 adalah inti penilaian.** Tahan shot Actions history
  cukup lama agar juri sempat membaca ketiga kata `schedule`.
- **Jangan zoom terlalu dekat** pada dashboard — juri perlu melihat banner
  fixture dan skor sekaligus dalam satu frame.
- **Periksa sebelum unggah:** tidak ada URL webhook, tidak ada API key, tidak
  ada isi file `.env` yang terlihat di frame mana pun. Termasuk di address bar,
  tab browser, dan riwayat terminal.

---

## Checklist Sebelum Publikasi

- [ ] Durasi akhir ≤ 3 menit
- [ ] Semua angka cocok dengan `evidence/unattended-runs.md`
- [ ] Banner fixture terbaca di setiap footage replay
- [ ] Pengungkapan SEC-001 utuh, tidak terpotong
- [ ] Asal dua run Senin disebutkan
- [ ] Disclaimer muncul sebagai teks dan diucapkan
- [ ] Tidak ada kredensial terlihat di frame mana pun
- [ ] Video dapat diakses tanpa login (cek dari jendela penyamaran)
