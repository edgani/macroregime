# V10.0 Operator Guide

## Daily workflow

1. Jalankan aplikasi. Worker melakukan refresh fast setiap 15 menit dan full refresh setiap 6 jam secara default.
2. Buka Mission Control untuk melihat market state dan jumlah bias/shadow candidate.
3. Buka Alpha Center. Prioritaskan `SHADOW ELIGIBLE`, lalu buka ticker packet.
4. Periksa causal/value assumptions, low/base/high target, entry, stop, reward/risk, data quality, dan remaining gates.
5. Rekam shadow candidate melalui `RUN_V100_SHADOW.bat`.
6. Review outcome hanya setelah horizon matang. Jangan backfill.

## Arti status

- `LONG_BIAS` / `SHORT_BIAS`: fixed current research score melewati threshold. Bukan klaim proven alpha.
- `WATCH`: data kurang atau score belum cukup.
- `SHADOW ELIGIBLE`: current quote, value bridge, data quality, score, risk plan dan R/R lulus.
- `PROOF_GATED`: systematic live belum memiliki exact bound proof.
- `ELIGIBLE_REQUIRES_HUMAN_APPROVAL`: exact proof telah terikat; auto-submit tetap off.

## Experimental manual micro-risk

Fitur ini bukan systematic live dan mati secara default. Untuk mengaktifkannya secara sadar, edit `.env`:

```env
WARROOM_EXPERIMENTAL_LIVE=1
WARROOM_EXPERIMENTAL_ACK=I_ACCEPT_EXPERIMENTAL_UNPROVEN_ALPHA_RISK
WARROOM_HUMAN_APPROVAL_SECRET=<minimum 24 random characters>
```

Refresh aplikasi, lalu jalankan `EXPORT_V100_EXPERIMENTAL_ORDER.bat`. Ticket:

- memakai risk cap 0.10% equity dan notional cap 5%;
- berlaku 15 menit;
- HMAC-bound ke packet yang tepat;
- tidak mengirim order ke broker;
- tetap memerlukan verifikasi manual symbol/contract, currency, lot size, fees, tax, borrow, dan venue.

## Data limitations

Current provider-normalized financials dan current-vintage macro dipakai untuk current research action. Itu tidak menggantikan historical point-in-time proof. Bundled historical/reference data tetap tampil ketika network gagal.
