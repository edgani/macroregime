
function tick(){const d=new Date();document.getElementById('clk').textContent=d.toISOString().substr(11,8)+' UTC';}
setInterval(tick,1000);tick();

/* helper builders */
const badge=(cls,txt)=>`<span class="b ${cls}">${txt}</span>`;
const esc2=s=>String(s==null?'—':s).replace(/</g,'&lt;').replace(/>/g,'&gt;');
function panel(title, provs, bodyHTML){
  return `<div class="panel"><div class="phd"><h3>${title}</h3><div class="prov">${provs.map(([c,t])=>badge(c,t)).join('')}</div></div><div class="pbd">${bodyHTML}</div></div>`;
}
function rows(list){ // list: [ [k, v, subhtml?] ]
  return list.map(r=>`<div class="drow"><div><span class="${r[3]?'kk':'k'}">${r[0]}</span>${r[2]?`<div class="sub2">${r[2]}</div>`:''}</div><div class="v">${r[1]}</div></div>`).join('');
}

/* ══════════ MISSION CONTROL (bespoke) ══════════ */
function viewMC(){
  const S = window.__SYS;
  const liveStrip = S ? `<div class="panel" style="margin-bottom:12px;border-color:rgba(46,193,111,.35)"><div class="phd"><h3 style="color:var(--up)">◆ LIVE SYSTEMIC — this run</h3><div class="prov">${badge('eng','◆ gcfis/orchestrator')}${badge('prod','✅ from run.py')}</div></div><div class="pbd"><div class="wsb" style="grid-template-columns:repeat(5,1fr)">
    <div class="wcell"><span class="kx">Quad</span><span class="vx sg">${S.quad||'—'} · ${esc2(S.quad_name)}</span></div>
    <div class="wcell"><span class="kx">Liquidity</span><span class="vx ${String(S.liquidity).includes('expand')?'u':'m'}">${esc2(S.liquidity)}</span></div>
    <div class="wcell"><span class="kx">Fragility</span><span class="vx ${typeof S.fragility==='number'&&S.fragility>60?'d':'m'}">${esc2(S.fragility)}</span></div>
    <div class="wcell"><span class="kx">Shock P</span><span class="vx ${typeof S.shock_prob==='number'&&S.shock_prob>0.5?'d':'m'}">${esc2(S.shock_prob)}</span></div>
    <div class="wcell"><span class="kx">Cross-asset</span><span class="vx i">${esc2(S.cross_asset)}</span></div>
  </div>${(S.rotation_in&&S.rotation_in.length)?`<div class="lbl" style="margin-top:9px">Rotating IN: <span class="u">${S.rotation_in.join(', ')}</span> · OUT: <span class="d">${(S.rotation_out||[]).join(', ')}</span></div>`:''}</div></div>` : '';
  return `
  <div class="viewhead"><h2 class="sg">MISSION CONTROL</h2><span class="vd">Cockpit — what the world is doing, now. &lt;30s scan.</span></div>
  <div class="provrow">${badge('eng','◆ warroom/attention.py')}${badge('eng','◆ meters.py')}${badge('eng','◆ drivers.py')}${badge('prod','✅ meters/drivers PROD')}${badge('build','○ status-bar wiring')}</div>
  ${liveStrip}
  <div class="grid" style="grid-template-columns:1fr">
    ${panel('World Status — Macro Drivers',[['eng','◆ drivers.py'],['prod','✅ PROD']],`
      <div class="wsb">
        <div class="wcell"><span class="kx">Liquidity</span><span class="vx u">▲ Improving <span class="chip up" style="margin-left:auto"><span class="dot"></span>+</span></span></div>
        <div class="wcell"><span class="kx">Growth</span><span class="vx d">▼ Weakening <span class="chip dn" style="margin-left:auto"><span class="dot"></span>−</span></span></div>
        <div class="wcell"><span class="kx">Inflation</span><span class="vx a">▲ Sticky <span class="chip amb" style="margin-left:auto"><span class="dot"></span>=</span></span></div>
        <div class="wcell"><span class="kx">Credit</span><span class="vx d">▼ Tightening <span class="chip dn" style="margin-left:auto"><span class="dot"></span>−</span></span></div>
        <div class="wcell"><span class="kx">Dollar</span><span class="vx a">▲ Strong <span class="chip amb" style="margin-left:auto"><span class="dot"></span>=</span></span></div>
        <div class="wcell"><span class="kx">Volatility</span><span class="vx i">→ Neutral <span class="chip neu" style="margin-left:auto"><span class="dot"></span>~</span></span></div>
      </div>`)}
    ${panel('Regional Regime',[['eng','◆ gip_engine.py'],['eng','◆ country_regime.py'],['prod','✅ quad PROD']],`
      <div class="regions">
        <div class="rcell"><div class="rk">US</div><div class="rv a">Late Expansion</div></div>
        <div class="rcell"><div class="rk">China</div><div class="rv i">Recovery 31%</div></div>
        <div class="rcell"><div class="rk">Europe</div><div class="rv d">Weak</div></div>
        <div class="rcell"><div class="rk">Japan</div><div class="rv u">Bull</div></div>
        <div class="rcell"><div class="rk">India</div><div class="rv u">Bull</div></div>
        <div class="rcell"><div class="rk">IHSG</div><div class="rv u">Bull</div></div>
        <div class="rcell"><div class="rk">Crypto</div><div class="rv u">Expansion</div></div>
        <div class="rcell"><div class="rk">Commod</div><div class="rv a">Mixed</div></div>
      </div>`)}
    ${panel('Global Capital Rotation',[['eng','◆ cycle_rotation.py'],['prod','✅ PROD']],`
      <div class="rot">
        <div class="rstep cold"><div class="rn">CASH</div><div class="rb"><i style="width:30%"></i></div><span class="rflow">›</span></div>
        <div class="rstep cold"><div class="rn">BONDS</div><div class="rb"><i style="width:25%"></i></div><span class="rflow">›</span></div>
        <div class="rstep"><div class="rn">GOLD</div><div class="rb"><i style="width:68%;background:var(--amb)"></i></div><span class="rflow">›</span></div>
        <div class="rstep"><div class="rn">COMMOD</div><div class="rb"><i style="width:52%"></i></div><span class="rflow">›</span></div>
        <div class="rstep"><div class="rn">LG CAP</div><div class="rb"><i style="width:60%"></i></div><span class="rflow">›</span></div>
        <div class="rstep hot"><div class="rn">GROWTH</div><div class="rb"><i style="width:82%;background:var(--up)"></i></div><span class="rflow">›</span></div>
        <div class="rstep hot"><div class="rn">MICRO</div><div class="rb"><i style="width:74%;background:var(--up)"></i></div><span class="rflow">›</span></div>
        <div class="rstep hot"><div class="rn">CRYPTO</div><div class="rb"><i style="width:79%;background:var(--up)"></i></div></div>
      </div>
      <div class="lbl" style="margin-top:9px">Position on curve: <span class="sg">RISK-SEEKING TAIL</span> — late-cycle behavior.</div>`)}
    <div class="grid row3" style="grid-template-columns:1fr 1fr 1fr">
      ${panel('10 Composite Meters',[['eng','◆ meters.py'],['prod','✅ PROD']],rows([
        ['Trend','<span class="u">+62</span>','price-proxy composite'],['Credit','<span class="a">−18</span>','HY/IG proxy'],
        ['Bubble','<span class="a">71</span>','valuation + breadth'],['Liquidity','<span class="u">+</span>','FRED net-liq'],['Wealth','<span class="u">+</span>','']]))}
      ${panel('Early Warning',[['eng','◆ early_warning.py'],['prod','✅ panic PROD']],rows([
        ['Fear-Greed','<span class="a">58 / greed</span>','40%·VIX+30%·breadth+30%·mom'],
        ['Panic-Bottom','<span class="m">not active</span>','fwd63 +5-8% when fires, p<0.001'],
        ['Crash 24mo','<span class="a">27%</span>','crash_lead.py · p=0.0001']]))}
      ${panel('Live Allocation',[['eng','◆ risk.py'],['res','◐ conviction book']],rows([
        ['US Equity','35%'],['Crypto','<span class="th">17%</span>'],['Cash','18%'],['Gold','<span class="a">9%</span>'],['Commodities','<span class="u">8%</span>'],['IHSG · JP · EU','13%']]))}
    </div>
  </div>`;
}

/* ══════════ generic tab spec (data-driven) ══════════ */
const TABS={
 macro:{title:'MACRO &amp; REGIME',cls:'',sub:'Risk-on/off timing, dollar-hub, quad, regime state, decision engine.',
  prov:[['eng','◆ drivers.py'],['eng','◆ gip_engine.py'],['eng','◆ regime_hmm.py'],['eng','◆ forward_macro.py'],['prod','✅ cross-asset + quad PROD']],
  panels:[
   ['Cross-Asset Driver Coherence',[['eng','◆ drivers.py'],['prod','✅ PROD · empirical OLS']],rows([
     ['Gold (XAU)','<span class="a">STRETCHED +1.4σ</span>','R²=0.61 · real-rates−dollar model'],
     ['Copper','<span class="u">IN-LINE</span>','R²=0.55 · growth−dollar'],
     ['Oil (WTI)','<span class="d">OFFSIDE −2.1σ</span>','R²=0.48 · rich vs model'],
     ['BTC','<span class="a">DECOUPLED</span>','R²=0.22 → coherence N/A (low fit)'],
     ['SPY','<span class="u">IN-LINE</span>','R²=0.71 · rates+credit+growth']],)],
   ['GIP Quad Regime',[['eng','◆ gip_engine.py'],['prod','✅ PROD']],rows([
     ['Current Quad','<span class="a">Q3 · Growth↓ Inflation↑</span>','stagflationary lean'],
     ['Playbook','<span class="m">Gold, energy, quality, USD</span>','quad→asset map'],
     ['Δ vs 3mo','Q1 → Q3','deceleration path'],
     ['Forward-implied','<span class="a">Q3 persists</span>','forward_macro.py · market-implied']],)],
   ['Regime State Machine',[['eng','◆ regime_hmm.py'],['res','◐ RESEARCH']],rows([
     ['HMM State','State 3 / 4','Gaussian HMM, runtime-fit on daily'],
     ['Persistence','~34 days median','needs walk-forward'],
     ['Historical Analog','1999 / 2007 / 2018','nearest-fit (BUILD)','x']],)],
   ['Decision Engine',[['eng','◆ decision_center.py'],['eng','◆ regime_meta.py'],['res','◐ structure OK, edges need data']],`
     <div class="note">Theme → Evidence → Probability → Scenarios → Market → Industry → Company → Ticker → Execution.<br>
     <span class="d">War = state machine</span> (Shock→Transmission→Reaction→Pricing→Recovery), <span class="d">Fed = conditional</span> (cut+recession ≠ cut+soft-landing). Structure exists in <b>gcfis/meta/decision_stack.py</b>; needs wiring to the UI + edge validation.</div>`],
  ]},

 ew:{title:'EARLY WARNING',cls:'',sub:'Panic-bottom, euphoria-top, crash lead-time, funding stress, mania/distribution.',
  prov:[['eng','◆ early_warning.py'],['eng','◆ crash_lead.py'],['eng','◆ funding_stress.py'],['eng','◆ crash_bottom.py'],['prod','✅ panic-bottom PROD']],
  panels:[
   ['Composite Fear-Greed',[['eng','◆ early_warning.py'],['prod','✅ panic PROD · euphoria FLAGGED']],rows([
     ['Index (0=fear,100=greed)','<span class="a">58 · mild greed</span>','40%·(1−VIXpct)+30%·(1−breadth)+30%·mom-z'],
     ['Panic→Bottom signal','<span class="m">not active</span>','when fires: fwd63 +5-8% vs +3%, p<0.001'],
     ['Euphoria→Top signal','<span class="a">weak (p=0.34)</span>','bull-sample bias — flagged, not overclaimed']],)],
   ['Crash Lead-Time (probabilistic)',[['eng','◆ crash_lead.py'],['prod','✅ PROD']],rows([
     ['P(crash ≤12mo)','<span class="a">15%</span>','baseline-conditioned'],
     ['P(crash ≤24mo)','<span class="d">27%</span>','vs 15% base · p=0.0001'],
     ['P(crash ≤36mo)','<span class="d">34%</span>','valuation + credit + breadth']],)],
   ['Funding / Liquidity Stress',[['eng','◆ funding_stress.py'],['need','⚠ needs FRED']],rows([
     ['SOFR−FF spread','<span class="a">watch</span>','FRED · repo stress proxy'],
     ['Credit accident risk','<span class="u">low</span>','HY OAS + MOVE composite'],
     ['Net-liquidity impulse','<span class="u">+</span>','FedBS − TGA − RRP']],)],
   ['Mania / Distribution',[['eng','◆ crash_bottom.py'],['build','○ insider/IPO feeds BUILD']],`<div class="note">Retail mania · insider selling · CEO selling · IPO/SPAC surge · AI-bubble gauge. Composite exists (crash-pressure + type classifier); insider/IPO sub-panels need alt-data feeds — flagged, not faked.</div>`],
  ]},

 sc:{title:'SUPPLY CHAIN / BOTTLENECK',cls:'',sub:'The choke-points that create asymmetry. Node → tier → who is exposed.',
  prov:[['eng','◆ bottleneck_engine.py'],['eng','◆ moonshot_universe.py'],['eng','◆ secular_map.py'],['res','◐ scoring RESEARCH']],
  panels:[
   ['Bottleneck Migration Map',[['eng','◆ moonshot_universe.py'],['res','◐ 10 domains curated']],rows([
     ['GPU / accelerator silicon','<span class="a">Tier1 · consensus</span>','NVDA AMD AVGO — priced'],
     ['Advanced packaging / ABF (L3-4)','<span class="u">Tier3 · accelerating</span>','hidden: AEHR CAMT FORM'],
     ['Photonics / CPO','<span class="u">Tier2 · accelerating</span>','COHR LITE AAOI · hidden FN'],
     ['Power / grid','<span class="u">Tier2</span>','GEV ETN VRT POWL'],
     ['Cooling / thermal','<span class="u">Tier3 · emergence</span>','liquid-cooling supply chain'],
     ['Uranium / nuclear','<span class="a">Tier3</span>','CCJ UEC · supply-inelastic']],)],
   ['Bottleneck Score (per node)',[['eng','◆ bottleneck_engine.py'],['res','◐ needs pricing-power test']],rows([
     ['Formula','geo-mean of normalized [0,1]','irreplaceability × qual-cycle × substitution × layer-depth'],
     ['Validation gap','bottleneck→pricing-power/return','event-study on YOUR data'],
     ['Elasticity','how fast supply responds','THE core of asymmetry']],)],
  ]},

 co:{title:'COMPANY INTELLIGENCE',cls:'',sub:'Ticker = investment memo. Role in chain, accumulation stage, scenario, kill-thesis.',
  prov:[['eng','◆ investment_memo.py'],['eng','◆ accumulation.py'],['eng','◆ market_cap_target.py'],['prod','✅ accumulation PROD']],
  panels:[
   ['Institutional Adoption Curve (Stage 1-5)',[['eng','◆ accumulation.py'],['prod','✅ PROD · catches PLTR/SNDK']],rows([
     ['Accumulation score','0.30·RS + 0.25·VE + 0.20·ΔER + 0.15·own + 0.10·OI','alpha-RS, not return-ratio'],
     ['Stage','<span class="u">Stage 2→3 transition</span>','uncrowded → crowding = the timing edge'],
     ['Crowding velocity','<span class="u">accelerating</span>','the entry trigger']],)],
   ['Market-Cap Scenario → Price Target',[['eng','◆ market_cap_target.py'],['res','◐ priors, calibrate via tracker']],rows([
     ['Method','price × (mcap_target/mcap_now) × (1−dilution)','NOT technical highs'],
     ['Bull / Base / Bear','thesis-TAM multiples × mcap-now','small-cap = bigger convexity (log-scaled)'],
     ['Kill-thesis','explicit "what changes my mind"','per-thesis conditions']],)],
   ['Fundamental Dossier',[['build','○ needs paid fundamental feed']],`<div class="note">Moat · ROIC · FCF inflection · margin · patent · hiring · insider · 13F. Framework exists; <span class="d">all need a fundamental feed</span> — flagged feed-gated, never fabricated.</div>`],
  ]},

 crypto:{title:'CRYPTO',cls:'',sub:'On-chain footprint retail can\'t see on a price chart. Accumulation / cornering / distribution.',
  prov:[['eng','◆ onchain_engine.py'],['rescue','⟲ RESCUE from engines/'],['eng','◆ gcfis/crypto.py'],['need','⚠ needs Glassnode/CryptoQuant key']],
  panels:[
   ['On-Chain Accumulation / Distribution',[['eng','◆ onchain_engine.py'],['rescue','⟲ RESCUE'],['need','⚠ API key']],rows([
     ['Exchange netflow','<span class="u">outflow → accumulation</span>','neg = bullish, pos = distribution'],
     ['Exchange reserves','<span class="u">declining → supply shock</span>','thin float = outsized price impact'],
     ['Whale cohort (1k–100k)','<span class="u">balance ↑</span>','+ Glassnode Accum Trend Score'],
     ['MVRV Z','<span class="a">neutral</span>','&lt;0.85z bottom · &gt;7z top warning'],
     ['aSOPR','<span class="u">crossing &gt;1</span>','profit transition = early bull'],
     ['Funding rate','<span class="u">neg = contrarian bull</span>','shorts pay longs'],
     ['Stablecoin inflow','<span class="u">dry powder</span>','+ coin outflow = strong instit. accumulation']],)],
   ['Derivatives + ETF',[['eng','◆ gcfis/crypto.py'],['res','◐ post-ETF weighted']],rows([
     ['ETF flow','net creations','IBIT/FBTC — the marginal buyer'],
     ['CME basis','term structure','institutional positioning'],
     ['Funding + OI','leverage state','fragility down the beta chain']],)],
   ['Crypto Beta Chain',[['eng','◆ market_cap_target.py'],['res','◐ crypto_beta thesis']],`<div class="note">BTC → ETH → SOL → alt → meme: rising beta + rising fragility down the chain. mcap-scenario convexity per rung. Kill: BTC loses 200d, funding deeply negative, unlock cliff, exchange reserves rising.</div>`],
  ]},

 commod:{title:'COMMODITIES',cls:'',sub:'Positioning (COT), curve structure, driver coherence, supply elasticity.',
  prov:[['eng','◆ cftc_cot_scraper.py'],['rescue','⟲ RESCUE from engines/'],['eng','◆ drivers.py'],['prod','✅ COT feed is FREE (CFTC)']],
  panels:[
   ['Commitment of Traders (COT)',[['eng','◆ cftc_cot_scraper.py'],['rescue','⟲ RESCUE'],['prod','✅ FREE feed']],rows([
     ['Non-commercial (specs)','<span class="a">net long, 78th %ile</span>','crowded — extreme watch'],
     ['Commercial (hedgers)','<span class="d">net short</span>','the "smart" side'],
     ['Retail (non-reportable)','<span class="m">small net long</span>',''],
     ['Signal','<span class="a">positioning extreme</span>','contrarian setup building']],)],
   ['Curve + Driver Coherence',[['eng','◆ drivers.py'],['prod','✅ PROD']],rows([
     ['Copper','<span class="u">IN-LINE</span>','growth−dollar model, R²=0.55'],
     ['Curve structure','contango / backwardation','inventory signal'],
     ['Uranium','<span class="a">idiosyncratic</span>','secular — supply-inelastic (10y mine lead-time)']],)],
  ]},

 fx:{title:'FX',cls:'',sub:'Carry (rate differential) is the dominant medium-term FX driver. + COT + real yield.',
  prov:[['eng','◆ fx_carry_engine.py'],['rescue','⟲ RESCUE from engines/'],['eng','◆ cftc_cot_scraper.py'],['need','⚠ needs FRED']],
  panels:[
   ['Carry / Rate-Differential Ranking',[['eng','◆ fx_carry_engine.py'],['rescue','⟲ RESCUE'],['need','⚠ FRED']],rows([
     ['Method','FRED harmonized 10Y gov yields, G10','higher + RISING diff attracts flow'],
     ['High-carry','<span class="u">USD, AUD</span>','rate-diff tailwind'],
     ['Low/negative carry','<span class="d">JPY, CHF</span>','funding currencies'],
     ['Horizon','monthly → positioning bias','not a tick signal']],)],
   ['FX Positioning (COT)',[['eng','◆ cftc_cot_scraper.py'],['rescue','⟲ RESCUE'],['prod','✅ FREE']],rows([
     ['EUR net','<span class="a">specs long</span>','COT non-commercial'],
     ['JPY net','<span class="d">specs short (extreme)</span>','reversal risk'],
     ['DXY correlation','engine present','usd_correlation_engine']],)],
  ]},

 ihsg:{title:'IHSG',cls:'',sub:'Regime-aware foreign flow (EFD) + bandarmologi accumulation. Your validated flow_regime.',
  prov:[['eng','◆ flow_regime.py'],['eng','◆ accumulation.py'],['eng','◆ broker_flow.py'],['eng','◆ typef_idx.py'],['prod','✅ validated vs 2025 ATH']],
  panels:[
   ['Effective Flow Driver — Regime State',[['eng','◆ flow_regime.py'],['prod','✅ PROD · your redesign']],rows([
     ['Current state','<span class="u">DOMESTIC_LED</span>','4 states: FOREIGN/DOMESTIC/OPERATOR/DECOUPLED'],
     ['EFD = Corr_F × Par_F','the composite driver','KEEP tier — clean edge'],
     ['Foreign net','<span class="d">net sell</span>','but tape rising → domestic markup, NOT bearish'],
     ['Validation','2025 IHSG ATH-on-foreign-selling','BBCA/ISAT/TPIA/HUMI — confirmed']],)],
   ['Bandarmologi Accumulation',[['eng','◆ broker_flow.py'],['eng','◆ accumulation.py'],['res','◐ RESEARCH']],rows([
     ['Order-flow intent','accumulation vs distribution','BRAIN-style broker reclassification'],
     ['Type-F feed','<span class="u">live</span>','typef_idx.py — real IDX daily summary'],
     ['LPM','<span class="a">conditional-only</span>','validity gate: liq-expansion + breadth + slope']],)],
  ]},

 flow:{title:'FLOW &amp; ROTATION',cls:'',sub:'Where money is flowing, on the risk curve. RRG + cross-asset cycle.',
  prov:[['eng','◆ cycle_rotation.py'],['eng','◆ rotation.py'],['prod','✅ cycle PROD']],
  panels:[
   ['Cross-Asset Cycle Rotation',[['eng','◆ cycle_rotation.py'],['prod','✅ PROD']],rows([
     ['Cycle position','<span class="sg">risk-seeking tail</span>','cash→bond→gold→commod→lg→growth→micro→crypto'],
     ['Leading','<span class="u">growth, micro, crypto</span>','flow concentration'],
     ['Lagging','<span class="m">cash, bonds</span>','']],)],
   ['RRG Rotation Map',[['eng','◆ rotation.py'],['res','◐ RESEARCH · rotation-momentum weak prior']],`<div class="note">RRG-style relative-rotation quadrants (leading/weakening/lagging/improving) + crypto risk-curve. <span class="a">Honest flag:</span> your own prior test found rotation-momentum weak — keep as map, validate before trading it.</div>`],
  ]},

 kg:{title:'KNOWLEDGE GRAPH',cls:'',sub:'Everything connected. Shock propagation, typed causal edges, company cards.',
  prov:[['eng','◆ knowledge_graph.py'],['eng','◆ causal_chain.py'],['eng','◆ causal_attribution.py'],['res','◐ 3 edges tested, rest structural']],
  panels:[
   ['Causal Web + Shock Propagation',[['eng','◆ knowledge_graph.py'],['res','◐ 3 edges tested']],rows([
     ['Chain','War→Energy→Inflation→Fed→DXY→Gold','typed edges + delay + reliability'],
     ['Tested edges','<span class="u">3 validated</span>','rest are structural (RESEARCH)'],
     ['Kill-switch','<span class="a">causal_chain.py</span>','chain integrity check']],)],
   ['Company Knowledge Cards',[['eng','◆ investment_memo.py'],['build','○ 68 names — content curation']],`<div class="note">Per-name: role in chain + catalysts + convexity + kill-thesis. Structure + engine exist; the <b>curated content for ~68 names</b> is the build gap (needs fundamental research, not code).</div>`],
  ]},

 rc:{title:'VALIDATION / RESEARCH CENTER',cls:'',sub:'The lab, not a checklist. Every signal earns Production or stays Research.',
  prov:[['eng','◆ signal_edge.py'],['eng','◆ backtest.py'],['eng','◆ walkforward.py'],['eng','◆ run_validation.py'],['prod','✅ 16 tests executable']],
  panels:[
   ['Signal LIFT Table (event study)',[['eng','◆ signal_edge.py'],['prod','✅ PROD on S&P 2013-18']],rows([
     ['RS top-decile (cross-sectional)','<span class="u">lift 2.08x</span>','tail edge — caught AMD $2.52→$12'],
     ['Excess return top-decile','<span class="a">p=0.12 (NOT sig)</span>','mostly beta, alpha unproven — honest'],
     ['Breakout (absolute)','<span class="d">lift 0.56–1.01x REJECTED</span>','no edge'],
     ['Volume-spike / base-breakout','<span class="d">REJECTED</span>','coin-flip']],)],
   ['4-Fold Gate — Engine Status',[['eng','◆ certify.py'],['prod','✅ automated']],rows([
     ['Cross-Asset Macro','<span class="u">✅ PRODUCTION</span>','corr −0.22, p<0.001'],
     ['Panic-Bottom','<span class="u">✅ PRODUCTION</span>','fwd63 +6% vs +3%, p<0.001'],
     ['Crash Lead-Time','<span class="u">✅ PRODUCTION</span>','15→27% @24mo, p=0.0001'],
     ['Rotation','<span class="d">✗ REJECTED</span>','coin-flip'],
     ['Lead-Lag (daily)','<span class="d">✗ REJECTED</span>','p>0.5 → exploration only']],)],
   ['Anti-Overfit Harness',[['eng','◆ backtest.py'],['eng','◆ walkforward.py'],['res','◐ subset live']],`<div class="note">Walk-forward (purged/embargoed) · bootstrap · permutation/placebo · sensitivity · ablation · survivorship check · look-ahead check · data-revision (ALFRED vintage). <span class="d">Vintage/survivorship need data not in sandbox</span> — live on your machine.</div>`],
  ]},
};

/* ══════════ ALPHA (bespoke, enriched) ══════════ */
const ALPHA=[
 {tk:"AXTI",mkt:"US · MICRO",asym:"82",tier:"gen",tierLbl:"GENERATIONAL",base:"tier-4 · base-rate: very low",
  mcNow:"$0.42B",mcBull:"$6.4B",px:"→ +14×",thesis:"InP substrate — hard <b>bottleneck</b> for AI optical I/O / CPO. Layer-3 hidden name, tiny float.",
  gated:"feed-gated neutral: valuation, coverage, room-to-run (need fundamental feed)",why:"photonics commercialization inflection"},
 {tk:"GEV",mkt:"US · LARGE",asym:"74",tier:"str",tierLbl:"STRATEGIC",base:"tier-2 · base-rate: moderate",
  mcNow:"$95B",mcBull:"$304B",px:"→ +3.2×",thesis:"Grid + gas-turbine capacity = <b>power bottleneck</b> gating datacenter buildout. Multi-year backlog.",
  gated:"",why:"AI power demand > grid capacity for a decade"},
 {tk:"$RENDER-class",mkt:"CRYPTO · DePIN",asym:"69",tier:"gen",tierLbl:"GENERATIONAL",base:"tier-5 · base-rate: lottery",
  mcNow:"$2.1B",mcBull:"$40B",px:"→ +19×",thesis:"On-chain <b>DePIN compute</b>: netflow accumulation, reserves declining, unlock cliff cleared. Real usage &gt; narrative.",
  gated:"⚠ needs on-chain feed (onchain_engine.py — RESCUE) to score live",why:"GPU scarcity routes demand to decentralized supply"},
 {tk:"BRMS.JK",mkt:"IHSG · SMALL",asym:"61",tier:"str",tierLbl:"STRATEGIC",base:"tier-3 · base-rate: low",
  mcNow:"Rp 60T",mcBull:"Rp 450T",px:"→ +7×",thesis:"Bandarmologi <b>operator accumulation</b> (broker_flow) + reserve optionality. Domestic-led flow support.",
  gated:"scored via flow_regime + accumulation (both PROD)",why:"gold cycle + smart-money footprint"},
 {tk:"CCJ / UEC",mkt:"COMMOD · URANIUM",asym:"58",tier:"tac",tierLbl:"TACTICAL",base:"tier-3 · base-rate: low",
  mcNow:"—",mcBull:"3.5× base",px:"structural",thesis:"Supply <b>inelastic</b> (10y mine lead-time) vs restart + AI-power demand. Curve backwardation.",
  gated:"COT via cftc_cot_scraper (RESCUE, FREE)",why:"structural supply deficit + demand step-change"},
];
function viewAlpha(){
  const _D=window.DASHBOARD_DATA, _real=_D&&_D.meta&&_D.meta.source!=='SYNTHETIC';
  const _banner = _real
    ? `<div class="mockbanner" style="border-color:rgba(46,193,111,.35);background:rgba(46,193,111,.06)"><span class="b prod">● ${_D.meta.source==='LIVE'?'LIVE':'REAL DATA'}</span><span class="mbx">Real run · source <b style="color:var(--up)">${_D.meta.source}</b> · universe ${_D.meta.universe_n}. Structural asymmetry from your engines. Feed-gated factors (valuation/coverage/mcap) stay neutral until fundamentals are wired — score differentiates once they're live.</span></div>`
    : `<div class="mockbanner"><span class="b res">◆ MOCK</span><span class="mbx">Synthetic values — showing <b style="color:var(--amb)">output shape</b>. Universe today = <b>US 63 names/10 domains</b>; crypto/IHSG cards illustrate the <b>extension</b> (rescue onchain/cot/fx feeds). Asymmetry is STRUCTURAL, not a return forecast — most tier-4/5 fail.</span></div>`;
    <div class="top"><div><div class="tk">${a.tk}</div><span class="mk">${a.mkt}</span></div>
      <div class="asym"><div class="av">${a.asym}</div><div class="al">ASYMMETRY</div></div></div>
    <div class="tierline"><span class="tierbadge ${a.tier}">${a.tierLbl}</span><span class="baserate">${a.base}</span></div>
    <div class="thesis">${a.thesis}</div>
    <div class="mcapline">
      <div class="mcell"><div class="mk2">MC now</div><div class="mv2">${a.mcNow}</div></div>
      <div class="mcell"><div class="mk2">MC bull (TAM)</div><div class="mv2 u">${a.mcBull}</div></div>
      <div class="mcell"><div class="mk2">Price target</div><div class="mv2 u">${a.px}</div></div>
    </div>
    ${a.gated?`<div class="gated">${a.gated}</div>`:''}
    <div class="cardfoot"><span class="why">WHY NOW · ${a.why}</span><span class="trace">TRACEBACK ›</span></div>
  </div>`).join('');
  return `
  <div class="viewhead"><h2 class="th">◆ ALPHA &amp; TICKERS — Asymmetric Opportunity</h2><span class="vd">Structural asymmetry (not expected return). Tiers SEPARATED. Ticker = consequence.</span></div>
  <div class="provrow">${badge('eng','◆ asymmetric_discovery.py')}${badge('eng','◆ moonshot_universe.py')}${badge('eng','◆ market_cap_target.py')}${badge('eng','◆ competitive_ranking_engine.py')}${badge('eng','◆ signal_edge.py')}${badge('res','◐ 3/6 factors need feeds')}</div>
  ${_banner}
  <div class="cards">${cards}</div>`;
}

/* traceback */
const TRACE={"AXTI":{intro:"Why did AXTI surface? Not a rec — a <span class='q'>consequence</span> of the chain below. Powered by the real engines in each layer.",
 nodes:[
 {layer:"World · drivers.py",title:"AI capex — <span class='u'>EXPANSIVE</span>",desc:"Hyperscaler capex guidance rising YoY."},
 {layer:"Theme · moonshot_universe.py",title:"Photonics/CPO — <span class='sg'>Stage: acceleration</span>",desc:"Node = optical transceivers 800G/1.6T. Lifecycle early → runway."},
 {layer:"Bottleneck · bottleneck_engine.py",title:"InP substrate — <span class='d'>hard choke</span>",desc:"Layer-3/4. InP/EML supply constrained through 2027+. Small floats."},
 {layer:"Accumulation · accumulation.py",title:"<span class='u'>Stage 2→3</span> transition",desc:"Uncrowded → crowding. The timing edge (PLTR/SNDK pattern)."},
 {layer:"Convexity · market_cap_target.py",title:"MC $0.42B → bull $6.4B",desc:"photonics thesis multiple × mcap-now × (1−dilution). Small-cap convexity scaled."},
 {layer:"Positioning · competitive_ranking",title:"<span class='u'>NON-CONSENSUS</span>",desc:"Low coverage/ownership = crowding low = edge not yet priced."},
 ],
 term:{layer:"Ticker",title:"AXTI · asymmetry 82",desc:"Bottleneck + MC runway + early stage + non-consensus converge. Tier-4 → very-low base rate (honest)."},
 inv:["Silicon photonics substitute scales faster than expected","New EML/InP capacity online → bottleneck gone","AI capex guide cut 2+ quarters","Coverage crowds in → non-consensus edge dies"]},
"__generic__":{intro:"Traceback (mock). Every ticker traces World→Theme→Bottleneck→Accumulation→Convexity→Positioning via the real engines. Full spine generated at wire-time.",
 nodes:[{layer:"World",title:"Macro driver",desc:"from drivers.py"},{layer:"Theme",title:"Lifecycle stage",desc:"from moonshot_universe"},{layer:"Bottleneck",title:"Choke point",desc:"from bottleneck_engine"},{layer:"Positioning",title:"Crowding",desc:"from competitive_ranking"}],
 term:{layer:"Ticker",title:"—",desc:"Consequence of the chain."},inv:["Generated per-thesis at wire-time."]},
};
function openTrace(tk){
  const t=TRACE[tk]||TRACE["__generic__"];
  const nodes=t.nodes.map(n=>`<div class="snode"><div class="sdot"></div><div class="slayer">${n.layer}</div><div class="stitle">${n.title}</div><div class="sdesc">${n.desc}</div></div>`).join('');
  const term=`<div class="snode term"><div class="sdot"></div><div class="slayer">${t.term.layer}</div><div class="stitle" style="color:var(--up);font-weight:700;font-size:15px">${t.term.title}</div><div class="sdesc">${t.term.desc}</div></div>`;
  const inv=`<div class="invbox"><div class="it">Kill-thesis — dies if:</div><ul>${t.inv.map(x=>`<li>${x}</li>`).join('')}</ul></div>`;
  document.getElementById('drawer').innerHTML=`<div class="dhd"><div class="dtk">${tk}</div><span class="pill">TRACEBACK</span><span class="pill warn">MOCK</span><span class="x" id="closeX">✕</span></div><div class="dintro">${t.intro}</div><div class="spine">${nodes}${term}</div>${inv}`;
  document.getElementById('overlay').classList.add('on');
  document.getElementById('closeX').onclick=()=>document.getElementById('overlay').classList.remove('on');
}
document.getElementById('overlay').onclick=e=>{if(e.target.id==='overlay')e.currentTarget.classList.remove('on');};

/* generic tab renderer */
function viewGeneric(id){
  const t=TABS[id];
  const panels=t.panels.map(p=>panel(p[0],p[1],p[2])).join('');
  return `<div class="viewhead"><h2 class="${t.cls}">${t.title}</h2><span class="vd">${t.sub}</span></div>
    <div class="provrow">${t.prov.map(([c,x])=>badge(c,x)).join('')}</div>
    <div class="grid" style="grid-template-columns:1fr">${panels}</div>`;
}

/* ══════════ PER-MARKET SCREENERS (the funnel + setups) ══════════ */
const MARKET={
 us:{title:'US STOCKS',sub:'Tradeable setups — dealer-gamma + earnings-revision market. Long & short.',longOnly:false,
   prov:[['eng','◆ markets.py'],['eng','◆ elimination.py'],['eng','◆ market_drivers.py'],['eng','◆ entry.py'],['eng','◆ competitive_ranking'],['prod','✅ elimination/entry PROD']],
   funnel:[['512','UNIVERSE','S&P + supply-chain map'],['190','PASS ELIMINATION','liquidity · gaps · vol-of-vol · false-BO','elim'],['LONG','MARKET BIAS','net-liq add + earnings-rev up'],['47','SCORED ≥ gate','5-pillar geo-mean + surge 0-100'],['8','ENTRY-VALID','gamma-aware type + R/R ≥ 1.5','last']],
   drivers:[['Fed net-liq Δ','LONG','ST · str3','weekly add/drain moves index in days'],['Dealer gamma','MOMENTUM','ST · str3','GEX<0 amplifies (breakouts valid)'],['Earnings-rev breadth','LONG','MT · str3','revisions up = institutions forced to chase'],['Credit stress (HY OAS)','CALM','ST · str3','no risk-off tell']],
   setups:[
    {tk:'NVDA',act:'BUILD_LONG',ac:'long',e:'182.40',s:'171.00',t:'205.00',rr:'2.0',ty:'CONTINUATION',gm:'momentum ✓',cv:78,why:'earnings-rev breadth + negative-gamma momentum tape'},
    {tk:'MU',act:'BUILD_LONG',ac:'long',e:'118.20',s:'109.50',t:'135.60',rr:'2.0',ty:'BREAKOUT',gm:'momentum ✓',cv:71,why:'HBM sold-out forward · RS top-decile (signal_edge lift 2.08x)'},
    {tk:'GEV',act:'START_SCALING',ac:'scale',e:'421.00',s:'398.00',t:'467.00',rr:'2.0',ty:'PULLBACK',gm:'mean-rev ✓',cv:66,why:'power bottleneck · buy the dip in positive-gamma'},
    {tk:'SMCI',act:'STAND_ASIDE',ac:'avoid',e:'—',s:'—',t:'—',rr:'—',ty:'BREAKOUT',gm:'INVALID',cv:0,why:'',invalid:'breakout in positive-gamma (dealers fade) → flagged INVALID by entry.py'}]},

 ihsg:{title:'IHSG / IDX',sub:'Long-only. Foreign-flow + bandarmologi. Bearish = WAIT/reduce, never short.',longOnly:true,
   prov:[['eng','◆ flow_regime.py'],['eng','◆ broker_flow.py'],['eng','◆ typef_idx.py'],['eng','◆ entry.py'],['prod','✅ flow_regime validated vs 2025 ATH']],
   funnel:[['120','UNIVERSE','IDX liquid names'],['64','PASS ELIMINATION','ADV floor · float · absorption','elim'],['DOMESTIC_LED','EFD REGIME','foreign sell into rising tape = markup'],['22','SCORED','accumulation + broker-intent'],['5','LONG SETUPS','long-only enforced','last']],
   drivers:[['Foreign net flow','NET SELL','ST · str3','but domestic absorbing → NOT bearish (EFD regime)'],['USDIDR','WATCH','ST · str3','Rp18,000 = the confidence line'],['BI rate','SUPPORTIVE','ST · str2','defends IDR + banks ≈51% of index weight'],['Ratings outlook','STABLE','MT · str3','downgrade rumor alone cratered tape (May-26)']],
   setups:[
    {tk:'BBCA.JK',act:'BUILD_LONG',ac:'long',e:'10,150',s:'9,700',t:'11,200',rr:'2.3',ty:'PULLBACK',gm:'—',cv:69,why:'domestic-led markup · persistent broker accumulation'},
    {tk:'BREN.JK',act:'START_SCALING',ac:'scale',e:'8,900',s:'8,200',t:'10,400',rr:'2.1',ty:'CONTINUATION',gm:'—',cv:64,why:'operator footprint (bandarmologi) · reserve optionality'},
    {tk:'ADRO.JK',act:'WAIT',ac:'wait',e:'trigger 2,750',s:'—',t:'—',rr:'—',ty:'FORMING',gm:'—',cv:52,why:'coal terms-of-trade support · not yet triggered'},
    {tk:'GOTO.JK',act:'AVOID',ac:'avoid',e:'—',s:'—',t:'—',rr:'—',ty:'DISTRIBUTION',gm:'long-only',cv:0,why:'',invalid:'long-only market — distribution signal → WAIT/reduce if holding, never short'}]},

 crypto:{title:'CRYPTO',sub:'ETF-flow + funding + on-chain. Leverage/liquidation-driven.',longOnly:false,
   prov:[['eng','◆ onchain_engine.py'],['rescue','⟲ RESCUE'],['eng','◆ gcfis/crypto.py'],['eng','◆ market_drivers.py'],['need','⚠ needs Glassnode/CryptoQuant key']],
   funnel:[['180','UNIVERSE','majors + L1/DeFi/DePIN'],['70','PASS ELIMINATION','liquidity thinness · liquidation risk','elim'],['LONG','MARKET BIAS','ETF inflow + negative funding'],['24','SCORED','on-chain accumulation + surge'],['6','SETUPS','trend/entry gated','last']],
   drivers:[['Spot-ETF net flows','LONG','ST · str3','most reliable ST driver 2026 · ETFs hold ~6%+ supply'],['Funding / perp','CONTRARIAN +','ST · str2','neg funding = shorts pay longs = fuel'],['Stablecoin mcap Δ','+','ST · str2','dry powder entering the venue'],['DXY Δ','HEADWIND','ST · str2','dollar squeeze drains crypto']],
   setups:[
    {tk:'BTC-USD',act:'BUILD_LONG',ac:'long',e:'trend',s:'200d break',t:'cycle',rr:'—',ty:'CONTINUATION',gm:'—',cv:72,why:'ETF net creations · exchange reserves declining (onchain)'},
    {tk:'SOL-USD',act:'START_SCALING',ac:'scale',e:'pullback',s:'—',t:'—',rr:'—',ty:'PULLBACK',gm:'—',cv:63,why:'on-chain accumulation · higher-beta rung of the chain'},
    {tk:'$RENDER',act:'BUILD_LONG',ac:'long',e:'breakout',s:'—',t:'—',rr:'—',ty:'BREAKOUT',gm:'—',cv:58,why:'DePIN usage inflection · also surfaces in ◆ Alpha'}]},

 commod:{title:'COMMODITIES',sub:'Physical tightness + COT + curve. Geopolitics-driven now.',longOnly:false,
   prov:[['eng','◆ cftc_cot_scraper.py'],['rescue','⟲ RESCUE'],['eng','◆ drivers.py'],['eng','◆ market_drivers.py'],['prod','✅ COT free (CFTC)']],
   funnel:[['40','UNIVERSE','energy · metals · ags'],['28','PASS ELIMINATION','liquidity · noise','elim'],['MIXED','MARKET BIAS','oil geopol bid · gold real-yield drag'],['14','SCORED','COT extremes + driver coherence'],['5','SETUPS','entry gated','last']],
   drivers:[['Hormuz / geopol (oil)','LONG','ST · str3','~20% of global flows — dominant driver now'],['EIA inventories','DRAWS=BULL','ST · str3','7 straight US draw weeks'],['Real 10Y (gold)','HEADWIND','ST · str3','~$40-60/oz per 25bp repricing'],['CB gold buying','+','MT · str3','EM bid intact']],
   setups:[
    {tk:'CL=F · WTI',act:'BUILD_LONG',ac:'long',e:'breakout',s:'—',t:'—',rr:'—',ty:'BREAKOUT',gm:'—',cv:70,why:'Hormuz premium + inventory draws + COT specs building'},
    {tk:'GC=F · Gold',act:'STAND_ASIDE',ac:'wait',e:'—',s:'—',t:'—',rr:'—',ty:'PULLBACK',gm:'—',cv:48,why:'real-yield drag · wait for Fed-cut repricing'},
    {tk:'HG=F · Copper',act:'START_SCALING',ac:'scale',e:'continuation',s:'—',t:'—',rr:'—',ty:'CONTINUATION',gm:'—',cv:60,why:'growth-dollar model in-line (drivers.py) · supply tight'},
    {tk:'CCJ · Uranium',act:'BUILD_LONG',ac:'long',e:'continuation',s:'—',t:'—',rr:'—',ty:'CONTINUATION',gm:'—',cv:64,why:'structural deficit · supply-inelastic · also in ◆ Alpha'}]},

 fx:{title:'FX',sub:'Carry (rate-differential) + real yield + COT. USD firm.',longOnly:false,
   prov:[['eng','◆ fx_carry_engine.py'],['rescue','⟲ RESCUE'],['eng','◆ cftc_cot_scraper.py'],['eng','◆ market_drivers.py'],['need','⚠ needs FRED']],
   funnel:[['28','UNIVERSE','G10 + EM pairs'],['22','PASS ELIMINATION','liquidity','elim'],['USD FIRM','MARKET BIAS','rate-diff + risk-off bid'],['10','SCORED','carry + COT positioning'],['4','SETUPS','entry gated','last']],
   drivers:[['2Y rate-differential','LONG USD','ST · str3','front-end repricing = day-to-week driver'],['Real rate differential','ANCHOR','MT · str3','the MT anchor of currency direction'],['Risk-off (VIX)','USD BID','ST · str2','risk-off bids USD vs EM'],['BoP / CA (IDR)','PRESSURE','MT · str2','Q1-26 BoP −$9.1bn']],
   setups:[
    {tk:'USD/JPY',act:'BUILD_LONG',ac:'long',e:'continuation',s:'—',t:'—',rr:'—',ty:'CONTINUATION',gm:'—',cv:66,why:'positive carry + rate-diff · JPY funding currency'},
    {tk:'AUD/USD',act:'STAND_ASIDE',ac:'wait',e:'—',s:'—',t:'—',rr:'—',ty:'RANGE',gm:'—',cv:45,why:'mixed carry · no edge, wait'},
    {tk:'USD/IDR',act:'WATCH',ac:'wait',e:'Rp18,000 line',s:'—',t:'—',rr:'—',ty:'PRESSURE',gm:'—',cv:55,why:'BoP deficit + foreign outflow loop (ties to IHSG tab)'}]},
};
function viewMarket(id){
  const m=MARKET[id];
  const fun=m.funnel.map((f,i)=>`<div class="fstep ${f[3]||''}">${i<m.funnel.length-1?'<span class="farr">›</span>':''}<div class="fn">${f[0]}</div><div class="fl">${f[1]}</div><div class="fg">${f[2]}</div></div>`).join('');
  const drv=rows(m.drivers.map(d=>[d[0],`<span class="${d[1].includes('LONG')||d[1].includes('BULL')||d[1].includes('+')||d[1].includes('BID')||d[1].includes('SUPPORT')||d[1].includes('MOMENTUM')?'u':d[1].includes('SELL')||d[1].includes('HEADWIND')||d[1].includes('PRESSURE')||d[1].includes('DRAG')?'d':'a'}">${d[1]}</span>`,`${d[2]} · ${d[3]}`]));
  const setups=m.setups.map(x=>`<div class="scard ${x.ac==='wait'||x.ac==='avoid'?'wait':''}">
    <div class="stop2"><span class="stk">${x.tk}</span><span class="actbadge ${x.ac}">${x.act}</span><span class="conv">${x.cv?'conv '+x.cv:''}</span></div>
    <div class="est">
      <div class="estc"><div class="ek">Entry</div><div class="ev ${x.e==='—'?'m':'i'}">${x.e}</div></div>
      <div class="estc"><div class="ek">Stop</div><div class="ev ${x.s==='—'?'m':'d'}">${x.s}</div></div>
      <div class="estc"><div class="ek">Target</div><div class="ev ${x.t==='—'?'m':'u'}">${x.t}</div></div>
      <div class="estc"><div class="ek">R/R</div><div class="ev ${x.rr==='—'?'m':'sg'}">${x.rr}</div></div>
    </div>
    <div class="styp">${x.ty}<span class="gm ${x.gm==='INVALID'?'d':'m'}">${x.gm}</span></div>
    ${x.invalid?`<div class="invalidwarn">⚠ ${x.invalid}</div>`:`<div class="swhy">${x.why}</div>`}
  </div>`).join('');
  return `
  <div class="viewhead"><h2>${m.title}</h2><span class="vd">${m.sub}</span>${m.longOnly?'<span class="lo-badge">LONG-ONLY ENFORCED</span>':''}</div>
  <div class="provrow">${m.prov.map(([c,x])=>badge(c,x)).join('')}</div>
  <div class="lbl" style="margin-bottom:7px">Screener funnel — how a ticker surfaces in this market</div>
  <div class="funnel">${fun}</div>
  <div class="grid" style="grid-template-columns:1.15fr 1fr;align-items:start">
    <div class="panel"><div class="phd"><h3>Setups — surfaced tickers</h3><div class="prov">${badge('eng','◆ entry.py')}${badge('res','◐ synthetic in mock')}</div></div><div class="pbd"><div class="setups">${setups}</div></div></div>
    ${panel('Market Driver Bias',[['eng','◆ market_drivers.py'],['res','◐ your June-26 matrix']],drv)}
  </div>`;
}

/* ══════════ LIVE-DATA BINDING (run.py injects window.DASHBOARD_DATA) ══════════ */
(function bindLive(){
  const D = window.DASHBOARD_DATA; if(!D) return;
  try{
    const b=document.querySelector('.mockbadge .pill.warn');
    const real = D.meta.source && D.meta.source!=='SYNTHETIC';
    b.textContent = (real?(D.meta.source==='LIVE'?'LIVE · ':'REAL DATA · '):'SYNTHETIC RUN · ')+(D.meta.generated||'');
    b.style.background = real ? 'var(--up)' : 'var(--amb)';
    b.style.borderColor = real ? 'var(--up)' : 'var(--amb)';
    document.querySelector('.mockbadge .pill').textContent = (real?'REAL':'v0.3')+' · universe '+(D.meta.universe_n||'?');
  }catch(e){}
  const esc=s=>String(s==null?'':s).replace(/</g,'&lt;').replace(/>/g,'&gt;');
  // ALPHA (mutate in place → existing renderer works)
  if(Array.isArray(D.alpha) && D.alpha.length){
    ALPHA.length=0;
    D.alpha.forEach(a=>ALPHA.push({
      tk:a.tk, mkt:esc(a.market).toUpperCase().slice(0,18), asym:String(a.asymmetry),
      tier: a.tier>=4?'gen':a.tier===3?'str':'tac',
      tierLbl: a.tier>=4?'GENERATIONAL':a.tier===3?'STRATEGIC':'TACTICAL',
      base:'tier-'+a.tier+' · base-rate: '+a.base_rate,
      mcNow:'—', mcBull:a.upside||'—', px:a.upside||'—',
      thesis:esc(a.scarcity||a.node),
      gated: (a.gated&&a.gated.length)? 'feed-gated neutral: '+a.gated.join(', '):'',
      why:esc(a.node)
    }));
  }
  // per-market setups + funnel (mutate in place)
  if(D.markets){
    const actClass=a=>({BUILD_LONG:'long',START_SCALING:'scale',BUILD_SHORT:'short',
      STAND_ASIDE:'wait',WAIT:'wait',AVOID:'avoid',WATCH:'wait'}[a]||'wait');
    for(const id in D.markets){ if(!MARKET[id]) continue;
      const mk=D.markets[id];
      MARKET[id].funnel=[
        [String(mk.funnel.universe),'UNIVERSE','loaded prices'],
        [String(mk.funnel.eliminated),'ELIMINATED','liquidity · noise · false-BO','elim'],
        [esc(mk.bias)||'—','MARKET BIAS','market_drivers matrix'],
        [String(mk.funnel.setups),'ENTRY-VALID','gamma-aware + R/R gate','last']];
      MARKET[id].setups=(mk.setups||[]).map(x=>({
        tk:x.tk, act:x.act, ac:actClass(x.act),
        e:x.e==null?'—':String(x.e), s:x.s==null?'—':String(x.s),
        t:x.t==null?'—':String(x.t), rr:x.rr==null?'—':String(x.rr),
        ty:x.ty||'—', gm:x.valid?(x.gm||'—'):'INVALID', cv:x.conv||0,
        why:esc(x.why), invalid: x.valid?null:(x.warn||'gate not met')}));
      if(!MARKET[id].setups.length) MARKET[id].setups=[{tk:'—',act:'NO SETUP',ac:'wait',
        e:'—',s:'—',t:'—',rr:'—',ty:'—',gm:'—',cv:0,why:'',
        invalid:'no name cleared the conviction gate on this data — correct behavior, not fabricated'}];
    }
  }
  // Mission Control live-macro override (quad / liquidity / fragility / shock / x-asset)
  window.__SYS = D.systemic || null;
})();

/* router */
const MARKET_IDS=['us','ihsg','crypto','commod','fx'];
function render(v){
  const stage=document.getElementById('stage');
  if(v==='mc') stage.innerHTML=viewMC();
  else if(v==='alpha'){ stage.innerHTML=viewAlpha(); stage.querySelectorAll('.acard').forEach(c=>c.onclick=()=>openTrace(c.dataset.tk)); }
  else if(MARKET_IDS.includes(v)) stage.innerHTML=viewMarket(v);
  else stage.innerHTML=viewGeneric(v);
  window.scrollTo(0,0);
}
document.getElementById('nav').onclick=e=>{
  const t=e.target.closest('.tab');if(!t)return;
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));t.classList.add('on');
  render(t.dataset.v);
};
render('mc');
