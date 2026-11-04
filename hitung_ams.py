# -*- coding: utf-8 -*-
"""
hitung_ams.py — angka desain papan AMS (AMS #1, 3 Nov 2026)
Jalankan:  python hitung_ams.py
Semua angka yang muncul di panduan AMS berasal dari skrip ini.
Asumsi bertanda INFERRED dipilih bebas (tidak ada data tim) — ubah di bagian KONSTANTA.
"""
import math

# ---------------- KONSTANTA ----------------
VDDA = 3.3          # V, referensi ADC = VDDA Blue Pill (pin 3V3)
NBIT = 12
ADC_MAX = 2**NBIT - 1
V5 = 5.0            # V, keluaran 7805
# NTC (INFERRED: tim belum menyebut jenis) -> NTC 10k, B25/50 = 3950 (MF58/MF52 di Jogjarobotika)
R25 = 10_000.0
B = 3950.0
T25 = 298.15
R_PU = 10_000.0     # pull-up 1 % ke 3V3
C_NODE = 100e-9     # kapasitor tiap kanal NTC
T_TRIP = 58.0       # degC ambang trip (rules: maks 60 degC) -> marjin 2 degC
T_RULE = 60.0
T_SHORT = 120.0     # di atas ini = sensor short (tidak masuk akal untuk sel)
T_OPEN = -30.0      # di bawah ini = sensor putus
# Sensor arus (INFERRED): sensor hall 5 V, keluaran 0,5–4,5 V; diwakili pot 10k ke 5 V
R_TOP, R_BOT = 10_000.0, 10_000.0   # pembagi 1 % ke ADC
I_FS = 100.0        # A, INFERRED: 0,5 V = -100 A, 2,5 V = 0 A, 4,5 V = +100 A
# Relay HRS2H-S-DC12V (kumparan 400 ohm, angka dari proyek BSPD) + 2N2222
V12 = 12.0
V_SCHOTTKY = 0.35
R_COIL = 400.0
VBE = 0.75
VCE_SAT = 0.2
R_BASE = 1_000.0
R_BPD = 10_000.0    # pull-down basis
HFE_MIN = 75        # PN2222A hFE min @ 10 mA (datasheet ON Semi, INFERRED untuk klon)
# CAN: APB1 = 36 MHz bila SYSCLK 72 MHz
F_APB1 = 36e6


def r_ntc(t_c):
    t = t_c + 273.15
    return R25 * math.exp(B * (1.0 / t - 1.0 / T25))


def t_from_r(r):
    return 1.0 / (1.0 / T25 + math.log(r / R25) / B) - 273.15


def v_node(r):
    return VDDA * r / (R_PU + r)


def counts(v, vref=VDDA):
    return round(v / vref * ADC_MAX)


def garis(judul):
    print("\n" + "=" * 70 + "\n" + judul + "\n" + "=" * 70)


# ---------------- 1. NTC ----------------
garis("1. NTC 10k B3950 + pull-up 10k ke 3,3 V  (V = 3,3 * R_ntc / (10k + R_ntc))")
print(f"{'T (C)':>6} {'R_ntc (ohm)':>12} {'V (V)':>7} {'ADC':>5} {'mV/C':>6} {'hitung/C':>8}")
for t in [-30, -20, 0, 10, 25, 40, 50, 55, 58, 60, 70, 80, 100, 120]:
    r = r_ntc(t)
    v = v_node(r)
    dv = (v_node(r_ntc(t + 0.5)) - v_node(r_ntc(t - 0.5)))
    print(f"{t:6.0f} {r:12.0f} {v:7.3f} {counts(v):5d} {dv*1000:6.1f} {dv/VDDA*ADC_MAX:8.1f}")

r_trip = r_ntc(T_TRIP)
print(f"\nAmbang trip {T_TRIP} C  -> R = {r_trip:.0f} ohm, V = {v_node(r_trip):.3f} V, ADC = {counts(v_node(r_trip))}")
print(f"Batas rules {T_RULE} C -> R = {r_ntc(T_RULE):.0f} ohm, V = {v_node(r_ntc(T_RULE)):.3f} V, ADC = {counts(v_node(r_ntc(T_RULE)))}")
v_short = v_node(r_ntc(T_SHORT))
v_open = v_node(r_ntc(T_OPEN))
print(f"Jendela sah: {T_OPEN} C .. {T_SHORT} C  ->  ADC {counts(v_short)} .. {counts(v_open)}")
print(f"   ADC < {counts(v_short)} = SHORT ke GND (atau > {T_SHORT} C);  ADC > {counts(v_open)} = PUTUS (kabel lepas)")
print(f"   kabel putus -> node ditarik ke 3,3 V -> ADC ~{ADC_MAX};  short -> ADC ~0")

# trimpot 10k sebagai rheostat
garis("2. Trimpot 3296W 10k sebagai pengganti NTC (rheostat 0..10k)")
for r in [10_000, 8_000, 5_000, 3_000, r_trip, 2_000, 1_000, 500, 100, 0.0]:
    if r > 0:
        print(f"R = {r:7.0f} ohm -> {t_from_r(r):6.1f} C -> V = {v_node(r):.3f} V (ADC {counts(v_node(r))})")
    else:
        print(f"R =       0 ohm -> short -> V = 0,000 V (ADC 0) -> FAULT")
print(f"Putaran pot dari 10k (25 C) ke ambang {T_TRIP} C: {(10_000 - r_trip) / 10_000 * 100:.0f} % jangkauan "
      f"(3296W 25 putaran -> ~{(10_000 - r_trip) / 10_000 * 25:.0f} putaran)")

# ketidakpastian suhu di ambang
garis("3. Ketidakpastian di sekitar 60 C (kenapa ambang 58 C, bukan 60 C)")
def t_meas(r_true, r25_err=0.0, b_err=0.0, rpu_err=0.0, adc_err=0):
    # nilai NTC sebenarnya r_true; firmware memakai R25,B nominal
    rpu = R_PU * (1 + rpu_err)
    v = VDDA * r_true / (rpu + r_true)
    n = counts(v) + adc_err
    v_fw = n / ADC_MAX * VDDA
    r_fw = R_PU * v_fw / (VDDA - v_fw)
    return t_from_r(r_fw)

for nama, r25e, be in [("NTC kaca MF58 5 %", 0.05, 0.01), ("NTC probe 1 %", 0.01, 0.01)]:
    worst = 0
    for s1 in (-1, 1):
        for s2 in (-1, 1):
            for s3 in (-1, 1):
                for s4 in (-2, 2):
                    # NTC sebenarnya pada 60 C dengan R25 dan B meleset
                    t = T_RULE + 273.15
                    r_true = R25 * (1 + s1 * r25e) * math.exp(B * (1 + s2 * be) * (1 / t - 1 / T25))
                    tm = t_meas(r_true, rpu_err=s3 * 0.01, adc_err=s4)
                    worst = max(worst, abs(tm - T_RULE))
    print(f"{nama:20s}: sel sebenarnya 60,0 C bisa terbaca 60 +/- {worst:.1f} C (R25, B +/-1 %, pull-up 1 %, ADC +/-2 LSB)")
print("-> ambang 58 C memberi marjin 2 C untuk NTC 1 %; dengan NTC 5 % marjin belum cukup (kalibrasi 1 titik / pakai NTC 1 %).")

# RC & mux
garis("4. RC tiap kanal + mux 74HC4051")
for t in [25, 60]:
    r = r_ntc(t)
    rth = R_PU * r / (R_PU + r)
    tau = rth * C_NODE
    print(f"T = {t} C: R_thevenin = {rth:.0f} ohm, tau = {tau*1e3:.2f} ms, f_c = {1/(2*math.pi*tau):.0f} Hz")
C_ADC = 8e-12  # STM32F103 datasheet: C_ADC 8 pF (cek ulang saat firmware)
err = C_ADC / (C_ADC + C_NODE)
print(f"Pindah kanal: muatan C_ADC 8 pF dibagi dengan 100 nF -> galat maks {err*VDDA*1e3:.3f} mV = {err*ADC_MAX:.2f} LSB (abaikan)")
print("Tanpa kapasitor per kanal, tiap pindah kanal harus menunggu RC pembagi + Ron mux -> kapasitor dipasang di sisi sensor.")
print("Pemutusan kabel terdeteksi setelah node naik ke 3,3 V: 5 tau dari pull-up 10k x 100 nF = "
      f"{5*R_PU*C_NODE*1e3:.0f} ms (jauh < 1 s)")

# Arus
garis("5. Sensor arus (pot 10k ke 5 V mewakili sensor hall 0,5–4,5 V) -> pembagi 10k/10k -> PA2")
k = R_BOT / (R_TOP + R_BOT)
for vs in [0.0, 0.5, 2.5, 4.5, 5.0]:
    va = vs * k
    i = (vs - 2.5) / 2.0 * I_FS
    tag = "FAULT (di luar 0,5–4,5 V)" if vs < 0.5 or vs > 4.5 else f"I = {i:+.0f} A (INFERRED skala)"
    print(f"V_sensor {vs:.1f} V -> V_ADC {va:.3f} V -> ADC {counts(va):4d}  {tag}")
print(f"Thevenin pembagi = {R_TOP*R_BOT/(R_TOP+R_BOT):.0f} ohm; dengan 100 nF f_c = "
      f"{1/(2*math.pi*R_TOP*R_BOT/(R_TOP+R_BOT)*C_NODE):.0f} Hz")
lsb_a = (VDDA / ADC_MAX) / k / (2.0 / I_FS)
print(f"Resolusi: 1 LSB = {VDDA/ADC_MAX*1e3:.2f} mV di ADC = {lsb_a:.3f} A (skala INFERRED +/-{I_FS:.0f} A)")
print("Monitor 5 V (mux B ch7, pembagi 10k/10k yang sama): I dihitung rasiometrik V_cur / V_5V -> galat 7805 (+/-4 %) hilang.")

# Relay
garis("6. Penggerak relay HRS2H 12 V lewat 2N2222 + latch tahan-diri")
v_coil = V12 - V_SCHOTTKY - VCE_SAT
i_c = v_coil / R_COIL
i_b = (VDDA - VBE) / R_BASE - VBE / R_BPD
print(f"Arus kumparan = ({V12} - {V_SCHOTTKY} - {VCE_SAT}) / {R_COIL:.0f} = {i_c*1e3:.1f} mA")
print(f"Arus basis    = (3,3 - 0,75)/1k - 0,75/10k = {i_b*1e3:.2f} mA (dari GPIO, batas STM32 25 mA/pin)")
print(f"beta paksa    = {i_c/i_b:.0f}  (< hFE min {HFE_MIN}/2 -> transistor jenuh pasti)")
print(f"Tegangan pickup relay tipikal 75 % x 12 = 9 V; kumparan dapat {v_coil:.2f} V -> aman. Aki 12 V turun ke 10 V pun masih > 9 V.")

garis("7. LED & catu")
print(f"LED AMS merah dari 12 V lewat 2k2: I = ({V12-V_SCHOTTKY:.2f} - 2,0)/2200 = {(V12-V_SCHOTTKY-2.0)/2200*1e3:.1f} mA, "
      f"P_R = {((V12-V_SCHOTTKY-2.0)**2)/2200*1e3:.0f} mW (< 250 mW)")
print(f"LED PWR hijau dari 5 V lewat 1k: I = (5 - 2,1)/1000 = {(5-2.1)/1000*1e3:.1f} mA")
beban = {"Blue Pill 72 MHz": 40, "SN65HVD230 (dominan)": 17, "14 NTC (maks)": 14*VDDA/(R_PU+400)*1e3,
         "74HC4051 x2": 0.2, "pot + 2 pembagi": 5/10e3*1e3 + 2*5/20e3*1e3, "LED PWR": 2.9}
tot = sum(beban.values())
for kk, vv in beban.items():
    print(f"   {kk:24s} {vv:6.1f} mA")
print(f"   {'TOTAL dari 7805':24s} {tot:6.1f} mA  (anggaran desain 100 mA)")
for vin in (12.0, 14.4):
    p = (vin - V_SCHOTTKY - V5) * 0.1
    print(f"Disipasi 7805 @ Vin {vin} V, 100 mA = {p:.2f} W -> naik suhu +{p*50:.0f} C (TO-220 tanpa heatsink ~50 C/W)")
print(f"Lebar jalur: arus total < 0,2 A; jalur catu 1,5 mm (tembaga 35 um) jauh di atas kebutuhan (IPC-2221 ~0,3 mm untuk 1 A)")

# CAN
garis("8. CAN bit timing bxCAN (APB1 36 MHz): bitrate = 36 MHz / (prescaler * (1 + BS1 + BS2))")
def cari(bitrate):
    best = None
    for pre in range(1, 1025):
        ntq = F_APB1 / (pre * bitrate)
        if abs(ntq - round(ntq)) > 1e-9:
            continue
        ntq = int(round(ntq))
        if not 8 <= ntq <= 25:
            continue
        for bs2 in range(1, 9):
            bs1 = ntq - 1 - bs2
            if not 1 <= bs1 <= 16:
                continue
            sp = (1 + bs1) / ntq
            score = abs(sp - 0.875)
            if best is None or score < best[0] - 1e-9 or (abs(score - best[0]) < 1e-9 and ntq > best[2]):
                best = (score, pre, ntq, bs1, bs2, sp)
    return best

for br in [125e3, 250e3, 400e3, 500e3, 1000e3]:
    b = cari(br)
    if b:
        _, pre, ntq, bs1, bs2, sp = b
        print(f"{br/1e3:6.0f} kbps: Prescaler {pre:3d}, {ntq:2d} tq = SYNC 1 + BS1 {bs1:2d} + BS2 {bs2}, "
              f"titik sampel {sp*100:.1f} %, SJW 1")
print("Daly CAN Protocol V1.0: 250 kbps, ID 29-bit 0x18|DataID|tujuan|sumber, BMS hanya MENJAWAB permintaan host.")
print("Senior: 400 kbps -> firmware menyediakan pilihan 125/250/400/500 + mode scan (silent) untuk menebak bitrate.")
