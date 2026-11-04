# Tugas AMS (Accumulator Management System) — ringkasan & strategi

Dibuat HUB #5, Sel 3 Nov 2026 ±16.30. Sumber: cerita pengguna (bukan kata-kata senior verbatim) + FS Rules 2027 v1.0.
Klaim tentang perangkat/praktik tim = INFERRED sampai dikonfirmasi senior (PERTANYAAN-SENIOR bagian L).

## 1. Tugas (dari pengguna)
Buat AMS berupa **PCB setrika** (PCB buatan sendiri, toner transfer + etsa FeCl3) yang:
1. membaca data **BMS** lewat **CAN bus**;
2. membaca **sensor arus** (boleh diwakili potensiometer);
3. membaca **14 sensor suhu NTC** (sementara boleh diwakili potensiometer);
4. **mengirim** sinyal/data lewat CAN bus;
5. mengeluarkan **sinyal overtemperatur**.
Boleh programmable; disarankan **STM32**. Individu. Serahan: **PCB setrika jadi & bekerja**.
**Tenggat senior: Jum 6 Nov 2026.** Tenggat pribadi: **Min 8 Nov**; target "hampir selesai" **Sab 7 Nov**.
Uji CAN: pengguna ingat dari **BMS asli** (belum pasti) → pertanyaan L1–L4.

## 2. Rules yang relevan (VERIFIED, FS Rules 2027 v1.0)
- **T 11.7.7** (baterai litium non-LiFePO4 **dan semua penyimpan energi hybrid**): casing tahan api; proteksi arus lebih; **overtemperature protection ≥ 30 % sel** (sensor sesuai EV 5.8.5: < 15 mm dari titik acuan sel), **trip bila sel keluar batas datasheet, maks 60 °C, lebih dari 1 s**, dan **memutus baterai**.
- **CV 5.1.2**: hybrid system = LVS → T 11.1 & T 11.7 berlaku. **CV 4.1.4**: satu sisi kumparan HSC AIR langsung di SDC, sisi lain dikendalikan sistem kontrol hybrid.
- **T 11.9** SCS: kabel putus / short GND / short supply → safe state; sinyal sensor di perangkat programmable → cek out-of-range; **pesan digital (CAN): data rusak & hilang/terlambat dideteksi, timeout ≤ 500 ms (T 11.9.4)**. Safe state baterai LV: minimal satu kutub diputus (T 11.9.5).
- Pembanding EV (tidak wajib untuk hybrid, dipakai sebagai acuan desain): EV 5.8.3 (ukur semua tegangan sel, arus, suhu ≥ 30 % sel), EV 5.8.4 (maks 60 °C), EV 5.8.10 (buka SDC bila kritis > 500 ms untuk V/I, > 1 s untuk suhu; akurasi, derau, sampling diperhitungkan), EV 5.8.12 (lampu merah "AMS"), EV 5.8.13 (sinyal AMS = SCS; sensor putus → SDC terbuka), EV 5.8.15 (semua nilai bisa ditampilkan di laptop), **EV 6.1.6 (trip AMS ditahan latch non-programmable, reset manual)**.
- Arti "sinyal overtemperatur" (tafsiran HUB): keluaran digital AMS yang **aktif bila suhu mana pun > batas selama > 1 s, atau sensor suhu rusak**, menuju relay (HSC AIR / SDC) + LED. **Fail-safe: relay ON = aman** (sama dengan BSPD) → AMS mati/hang/tanpa daya = trip.

## 3. Arsitektur (diputuskan AMS #1, Sel 3 Nov malam — menggantikan usulan HUB)
Dasar: jawaban senior L1–L11 (PERTANYAAN-SENIOR §L) + stok toko dicek 3 Nov ±20.30 + `hitung_ams.py`.
Pin map masih **draf**: diverifikasi terhadap datasheet STM32F103x8 + RM0008 di langkah "rangkaian per blok".

| Blok | Keputusan | Alasan singkat |
|---|---|---|
| MCU | Modul **Blue Pill STM32F103C8T6** di header perempuan 2×20 | Senior: modul boleh. C8T6 ada di Beetrona; Jogja kosong (C6T6 32 KB ada → cadangan, CAN belum diverifikasi) |
| 14 NTC | Pull-up 10k 1 % ke 3V3 + 100 nF per kanal; tiap kanal header 1×3 (1 trimpot · 2 node · 3 GND) + jumper cap | Jumper 1–2 = trimpot (simulasi), lepas = **kabel putus**, 2–3 = **short GND** → uji T 11.9 tanpa membongkar. NTC asli dipasang di 2–3. Trimpot disolder (pelajaran BSPD: pot di soket = kontak goyang = FAULT berkedip) |
| Mux | **2× 74HC4051 DIP** (CD74HC4067 kosong di dua toko) · S0–S2 bersama · keluaran A → PA0, B → PA1 | Mux B ch6 = GND (cek 0), ch7 = monitor 5 V (pembagi 10k/10k) → cek mux/ADC hidup + koreksi rasiometrik arus |
| Arus | Pot 10k ke 5 V mewakili sensor hall 5 V **0,5–4,5 V** (INFERRED) → pembagi 10k/10k 1 % → PA2 | Pin ADC STM32 **tidak** tahan 5 V; di luar 0,5–4,5 V = fault sensor |
| CAN | bxCAN **PB8/PB9 (remap)** + modul transceiver lewat header 4 pin (VCAN pilih 3V3/5V dengan jumper · GND · TX · RX) | **Transceiver tidak ada stok di dua toko** (L12). SN65HVD230 3,3 V diutamakan; TJA1050/MCP2551 5 V bisa dengan TX open-drain + pull-up 4k7 ke 5 V (PB9 tahan 5 V — verifikasi) |
| Data BMS | Daly. Dokumen Daly CAN V1.0: 250 kbps, ID 29-bit `0x18 DataID Tujuan Sumber`, BMS **menjawab permintaan** host (`0x18900140` → `0x18904001`, data 0x90–0x98). Senior: 400 kbps, ID di-sniff | Firmware: mode **sniffer** (semua ID → UART), bitrate pilihan 125/250/400/500 + scan silent, mode polling Daly |
| Overtemp | Ambang **58 °C** selama > 1 s (debounce ≤ 0,9 s); juga trip bila sensor/mux fault atau CAN timeout > 500 ms (opsi) | Rules maks 60 °C; ketidakpastian ±1,1 °C (NTC 1 %) / ±2,2 °C (NTC 5 %) di 60 °C |
| Keluaran | PA8 "AMS_OK" → 1k → **2N2222** (BC548 kosong) → relay **HRS2H DPDT**: kutub A = SDC (COM–NO), kutub B = **latch tahan-diri** di sisi emitor + LED AMS merah di NC; tombol **AMS RESET** | Latch non-programmable + reset manual (gaya EV 6.1.6); relay ON = aman; MCU hang → IWDG reset → pin mengambang → pull-down 10k → relay lepas → terkunci |
| Catu | 12 V → sekring 1 A → 1N5819 → 7805 → 5 V (Blue Pill 5V, pot arus, pembagi). 12 V setelah dioda → kumparan relay & LED AMS | Pola BSPD; beban 7805 ±66 mA |
| Tampilan | USART1 PA9/PA10 → CP2102 → laptop | USB & CAN pada F103 berbagi SRAM → USB bawaan Blue Pill tidak dipakai bersamaan dengan CAN (verifikasi RM0008) |
| PCB | 1 lapis, FR4 polos 10×15 (Beetrona) | Toner transfer 2 lapis sulit diluruskan; jumper kawat bila bersilang |

**Pin map draf**: PA0 mux A · PA1 mux B · PA2 arus · PA3/PA4/PA5 = S0/S1/S2 · PA8 AMS_OK · PA9/PA10 UART · PB8/PB9 CAN · PC13 LED kedip (bawaan) · PA13/PA14 SWD (ST-Link). Sisi header analog (A0–A5) terpisah dari sisi komunikasi (A8–A10, B8–B9).
Simulasi KiCad (ngspice): hanya blok analog (pembagi NTC, pembagi arus, penggerak relay). STM32, mux digital, dan CAN tidak bisa disimulasikan di KiCad.


### Perubahan Rab 4 Nov ±03.30 (AMS #1, keputusan pengguna + buku Bagian A)
- **PCB = AMS saja.** 14 trimpot pengganti NTC + pot arus dipasang di **breadboard**, disambung kabel jumper ke PCB: **J2** 1×16 (NTC1–14 + 2 GND), **J3** 1×3 (5 V, SIG, GND). Uji putus = cabut kabel; uji short = jumper sinyal ke GND. Header 1×3 + jumper cap per kanal **dibatalkan**.
- **Mux final**: U3 (→PA0) Y0–Y6 = NTC1–7, **Y7 = 3,3 V (cek atas)**; U4 (→PA1) **Y0 = GND (cek bawah)**, Y1–Y7 = NTC8–14. Posisi 000 & 111 berlawanan → semua kabel S macet-0/macet-1 tertangkap.
- **Monitor 5 V** (R16/R17 10k/10k + C21) langsung ke **PA6** (bukan lewat mux); arus = rasio N(PA2)/N(PA6).
- Penomoran komponen Bagian A + netlist lengkap: `AMS-Jilid-1A.html` Bab 4.2 (R1 LED PWR, R2–R15 pull-up, C5–C18, C19/C20 dekopling mux, R16–R19, C21–C22, R20 basis, R21 pull-down, R22 LED AMS, D1 1N5819, D2 LED PWR, D3 1N4007, D4 LED AMS, Q1 2N2222, K1 HRS2H, SW1 AMS RESET, J1 12 V, J4 SDC).
- Latch final: emitor Q1 → kontak NO kutub B → COM B = GND; SW1 paralel kontak; LED AMS dari 12 V lewat R22 ke NC B.
- Pin map Bagian A: PA0 MUXA · PA1 MUXB · PA2 arus · PA3/4/5 S0/1/2 · PA6 monitor 5 V · PA8 AMS_OK · PC13 LED. Bagian B (belum diverifikasi RM0008): PA9/PA10 UART, PB8/PB9 CAN, PA13/14 SWD.
- Online (Rab): modul **SN65HVD230 ×2** (bila senior tidak meminjami) + disarankan **USB logic analyzer 8CH 24 MHz** (sniff CAN lewat PulseView, bengkel tanpa osiloskop).

## 4. Risiko terbesar (urut)
1. **Waktu**: 3 hari efektif (Rab sore–Jum), pengguna belum pernah memprogram STM32, membuat PCB, atau memakai CAN. → kerja paralel (firmware di breadboard selagi PCB dibuat) + batas minimum Jumat.
2. **Data CAN BMS tidak diketahui** (merek, bitrate, ID, format, terminasi). Tanpa ini fitur 1 tidak bisa dibuktikan. → tanya malam ini (L1–L4).
3. **PCB setrika gagal** (toner tidak menempel, jalur putus, over-etch). → cetak 2–3 salinan, jalur lebar (≥ 0,8–1,0 mm), satu lapis, uji cetak footprint 1:1, sisakan Min 8 untuk membuat ulang.
4. Blue Pill palsu (chip klon) → beli 2; ST-Link klon.
5. Arah cetak (mirror) layout untuk toner transfer → diuji dengan cetakan kertas biasa + komponen asli sebelum setrika.

## 5. Tahap & bukti selesai
| Tahap | Isi | Bukti selesai (terukur) |
|---|---|---|
| S0 | Jawaban senior L★ | Tercatat di PERTANYAAN-SENIOR L |
| S1 | Belanja + pasang STM32CubeIDE + **blink** | LED Blue Pill berkedip dari kodemu |
| S2 | ADC: 1 pot arus + mux 14 kanal (breadboard) | 15 nilai tampil di laptop, berubah saat pot diputar |
| S3 | Konversi + logika: NTC → °C, fault putus/short, overtemp > batas > 1 s | Relay/LED trip ±1 s setelah satu "suhu" > batas; kabel NTC dicabut → trip |
| S4 | CAN kirim + terima: loopback lalu BMS asli | Pesan BMS terbaca; pesan AMS terkirim; timeout ≤ 500 ms → trip |
| S5 | Schematic + layout KiCad 1 lapis (paralel S2–S3) | ERC/DRC 0, cetak 1:1 cocok dengan komponen |
| S6 | PCB setrika: cetak → setrika → etsa → bor → solder | Kontinuitas jalur OK, tidak ada short, catu 5 V/3,3 V benar |
| S7 | Integrasi di PCB + justifikasi | Semua uji S2–S4 lulus di PCB; kalimat justifikasi tiap blok |

**Batas minimum Jumat** (bila terlambat): S1–S3 di breadboard + S5 + S6 tergores/teretsa. Dikorbankan dari belakang: S4 dengan BMS asli → integrasi PCB → (tidak boleh dikorbankan: overtemp + pembacaan 15 kanal).

## 6. Belanja (FINAL, AMS #1 Sel 3 Nov ±20.40)
Daftar lengkap + centang: `BELANJA-AMS.html` (juga artifact "Belanja AMS"). Perkiraan ±Rp336 rb (Beetrona ±157 rb, Jogjarobotika ±179 rb), stok dicek 3 Nov ±20.30.
Pengganti karena stok: CD74HC4067 → 2× 74HC4051 DIP · BC548 → 2N2222 · Blue Pill C8T6 dari Beetrona (Jogja kosong) · PCB polos dari Beetrona (Jogja kosong).
**Belum terpenuhi: transceiver CAN** (kosong di dua toko; v2 4 Nov: pesan online) → L12 ke senior; bila tidak ada, pesan online SN65HVD230 ×2.
Angka desain: `hitung_ams.py` (NTC, ambang 58 °C, ketidakpastian, RC, pembagi arus, relay, LED, 7805, CAN bit timing).

## 7. Chat produksi
- **AMS #1** (High, Rab 4 setelah presentasi): finalkan arsitektur dengan jawaban senior → **daftar belanja final dulu** → S1 (pasang CubeIDE + blink) → rangkaian per blok + pin map + angka (dicek skrip) → S5 schematic & layout 1 lapis → S6 panduan PCB setrika per langkah (format klinik-gambar). Prompt: `00_HUB/prompt/PROMPT-AMS-1.md`.
- **AMS #2** (High, Kam 5): firmware S2–S4 (CubeIDE langkah demi langkah, kode lengkap + logika dulu).
- **Klinik AMS** (Medium): debug breadboard/PCB/firmware.
