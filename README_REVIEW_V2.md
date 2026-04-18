This patch keeps the visual baseline and logic breadth of app(210).py but restructures the UX:

- Dashboard = control tower with connected cause/effect flow
- Dashboard stops at market effect; detailed tickers live in market tabs
- Market tabs are action-first
- IHSG is buy-only
- US / FX / Commodities / Crypto surface long + short sections

Status:
- review build
- conservative patch on top of app(210).py baseline
- intended for UX review, not claiming full final integration of every future engine change