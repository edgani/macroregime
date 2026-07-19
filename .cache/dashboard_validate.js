
(() => {
'use strict';
let D = window.DASHBOARD_DATA || {};
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const arr = x => Array.isArray(x) ? x : [];
const obj = x => x && typeof x === 'object' ? x : {};
const num = x => { const n=Number(x); return Number.isFinite(n)?n:null; };
const fmt = x => x===null||x===undefined||x===''?'—':String(x);
const money = x => { const n=num(x); if(n===null)return '—'; const a=Math.abs(n); return (n<0?'-':'')+'$'+(a>=1e9?(a/1e9).toFixed(1)+'B':a>=1e6?(a/1e6).toFixed(1)+'M':a>=1e3?(a/1e3).toFixed(0)+'K':a.toFixed(0)); };
const pct = x => { const n=num(x); return n===null?'—':(n>0?'+':'')+n.toFixed(1)+'%'; };
const timeLabel = x => { if(!x)return '—'; try { const d=new Date(x); return isNaN(d)?String(x).slice(0,19):d.toISOString().replace('T',' ').slice(0,19)+'Z'; } catch(e){return String(x).slice(0,19);} };
const short = (s,n=58) => String(s??'').length>n?String(s).slice(0,n-1)+'…':String(s??'');
function setHTML(id,html){const el=document.getElementById(id);if(el&&el.innerHTML!==html)el.innerHTML=html;}
const normalizeState = s => { const v=String(s??'').toUpperCase(); if(/LIVE|BULL|LONG|EXPAND|ACCUM|IMPROV|POSITIVE|CONSTRUCT/.test(v))return 'constructive'; if(/BEAR|SHORT|CONTRACT|DISTRIB|DETERIOR|NEGATIVE|RISK|CRITICAL|ERROR|BROKEN/.test(v))return 'destructive'; if(/WATCH|MIXED|PARTIAL|WAIT|TRANSITION|GUARDED|STANDBY|NO_SIGNAL|ACTION_REQUIRED|INITIALIZING/.test(v))return 'watch'; if(/NO_DATA|NOT_CONFIGURED|NOT_ENTITLED|EMPTY|UNAVAILABLE|OFFLINE|NONE|—/.test(v))return 'no_data'; return 'neutral'; };
let sourceState = obj(D.data_health).overall || obj(D.meta).source || 'NO_DATA';
let LI = obj(D.live_intelligence);
let FLD = obj(D.full_live_data);
let lastRevision = Number(obj(D.runtime).snapshot_sequence || 0);
let lastContentHash = String(obj(D.runtime).content_hash || '');
let lastPollOkAt = Date.now();
const DATA_URL = 'desk_snapshot.json';
const STATUS_URL = 'worker_status.json';
const POLL_MS = Math.max(5000, Number(new URLSearchParams(location.search).get('poll_ms') || 7000));
let pollInFlight=false;

const NAV = [
 {group:'COMMAND',items:[['mc','⌖','MISSION CONTROL'],['macro','◈','MACRO & REGIME'],['ew','⚠','EARLY WARNING']]},
 {group:'OPPORTUNITY',items:[['alpha','◆','ALPHA CENTER'],['inst','◎','INSTITUTIONAL'],['deriv','≋','DERIVATIVES / SQUEEZE']]},
 {group:'MARKETS',items:[['us','▦','US STOCKS'],['ihsg','▥','IHSG'],['crypto','⬡','CRYPTO'],['commod','◇','COMMODITIES'],['fx','⇄','FX']]},
 {group:'INTELLIGENCE',items:[['flow','⟿','FLOW & ROTATION'],['sc','⌁','SUPPLY CHAIN'],['co','▣','COMPANY INTEL'],['kg','✣','KNOWLEDGE GRAPH']]},
 {group:'CONTROL',items:[['rc','✓','VALIDATION CENTER']]}
];
const savedState=(()=>{try{return JSON.parse(localStorage.getItem('warroom_ui_state')||'{}')}catch(_){return {}}})();
let state={view:savedState.view||'mc',mode:savedState.mode||'observed',selected:null,selectedTicker:savedState.selectedTicker||null,search:''};
function persistState(){try{localStorage.setItem('warroom_ui_state',JSON.stringify({view:state.view,mode:state.mode,selectedTicker:state.selectedTicker}))}catch(_){}}

function renderSidebar(){
 const counts={alpha:state.mode==='all'?arr(D.alpha).length:0,inst:arr(obj(D.institutional).events).length,deriv:arr(LI.events).length};
 setHTML('sidebar',NAV.map(g=>`<div class="nav-group">${g.group}</div>${g.items.map(([id,ico,label])=>`<button class="nav-item ${state.view===id?'active':''}" data-view="${id}"><span class="ico">${ico}</span>${label}${counts[id]?`<span class="nav-badge">${counts[id]}</span>`:''}</button>`).join('')}`).join('')+`<div class="sidebar-foot"><div class="label">PRODUCTION RULE</div><div class="value">Missing feed = NO DATA.<br>Synthetic data is disabled unless explicit test mode.</div></div>`);
 document.querySelectorAll('.nav-item').forEach(b=>b.onclick=()=>{state.view=b.dataset.view;state.selected=null;persistState();render();});
}

function renderTop(){
 const sys=obj(D.systemic), health=obj(D.data_health), inst=obj(D.institutional), li=LI;
 const dot=health.overall==='LIVE'?'live':health.overall==='PARTIAL'?'partial':'bad';
 const feeds=arr(health.sources); const good=feeds.filter(x=>x.state==='LIVE').length;
 const chips=[
  `<span class="status-dot ${dot}"></span><b>${esc(health.overall||obj(D.meta).source||'NO_DATA')}</b>`,
  `REGIME <b>${esc(sys.quad_name||sys.quad||'NO_DATA')}</b>`,
  `LIQUIDITY <b>${esc(short(sys.liquidity||'NO_DATA',24))}</b>`,
  `SOURCES <b>${good}/${feeds.length||0}</b>`,
  `INSTITUTIONAL <b>${esc(inst.overall_state||'NOT_LOADED')}</b>`,
  `DERIVATIVES <b>${esc(li.overall_state||'NOT_LOADED')}</b>`,
  `FULL STACK <b>${esc(FLD.overall_state||'NOT_LOADED')}</b>`,
  `UPDATED <b>${esc(timeLabel(obj(D.meta).generated))}</b>`
 ];
 setHTML('topMetrics',chips.map(x=>`<div class="top-chip">${x}</div>`).join(''));
 const sync=document.getElementById('dataSync');if(sync&&!sync.dataset.worker){const age=Math.max(0,Math.round((Date.now()-lastPollOkAt)/1000));sync.innerHTML=`SYNC <b>${age<15?'LIVE':age<60?'DELAYED':'STALE'} · R${lastRevision}</b>`;}
}

function node(id,label,sub,value,stateName='neutral',evidence='observed',extra={}){return {id,label,sub,value,state:normalizeState(stateName),evidence,...extra};}
function edge(from,to,stateName='neutral',evidence='observed',label='',width=1.7,extra={}){
 return {from,to,state:normalizeState(stateName),evidence,label,width,active:false,relation:'association',...extra};
}
function layered(layers){
 const nodes=[]; const edges=[]; const xPad=72, width=856, top=55, bottom=555;
 layers.forEach((layer,li)=>{
  const y=layers.length===1?300:top+(bottom-top)*li/(layers.length-1); const n=layer.length;
  layer.forEach((nd,ni)=>{const x=n===1?500:xPad+(width)*(ni/(n-1)); nd.x=x;nd.y=y;nodes.push(nd);});
 });
 return {nodes,edges};
}
function connectAll(graph,fromLayer,toLayer,stateName='neutral',evidence='observed'){
 fromLayer.forEach(a=>toLayer.forEach(b=>graph.edges.push(edge(a.id,b.id,stateName,evidence))));
}
function basicRail(title,desc,current,next,alt,invalidation,windowText,confidence=0,action='WATCH / WAIT FOR CONFIRMATION'){
 return {title,desc,current,next,alternative:alt,invalidation,window:windowText,confidence,action};
}

function coverageFor(tab){return obj(obj(FLD.tab_coverage)[tab]);}
function coverageRows(tab){return arr(coverageFor(tab).provider_statuses).map(x=>({time:x.fetched_at||FLD.generated,ticker:x.provider,desc:`${x.dataset} · ${x.note||''}`,state:x.state,raw:x}));}
function coverageLabel(tab){const c=coverageFor(tab);return Object.keys(c).length?`${c.state||'NO_DATA'} · ${c.live||0} live · ${c.optional_missing||0} optional enrichment missing`:'NO COVERAGE CONTRACT';}
function providerStatus(providerPattern,datasetPattern=''){return arr(FLD.statuses).find(x=>new RegExp(providerPattern,'i').test(String(x.provider||''))&&(!datasetPattern||new RegExp(datasetPattern,'i').test(String(x.dataset||''))))||null;}
function latestFundamental(ticker){return arr(FLD.sec_fundamentals).find(x=>String(x.ticker||'').toUpperCase()===String(ticker||'').toUpperCase())||null;}
function breadthFor(id){return obj(obj(D.market_breadth)[id]);}
function bestAvailabilityStatus(statuses, fallback='NO_DATA'){
 const states=arr(statuses).map(x=>String(x?.state||'').toUpperCase());
 for(const candidate of ['LIVE','STALE','PARTIAL','NO_SIGNAL','ACTION_REQUIRED','NOT_ENTITLED','ERROR','NO_DATA'])if(states.includes(candidate))return candidate;
 return fallback;
}
function marketDerivativeContext(id){
 const liveStatuses=arr(LI.statuses), fullStatuses=arr(FLD.statuses);
 if(id==='us'){
  const rows=arr(LI.us_options);const relevant=liveStatuses.filter(x=>/OPTION|MASSIVE|UNUSUAL/i.test(`${x.provider||''} ${x.dataset||''}`));
  const state=rows.some(x=>x.state==='LIVE')?'LIVE':rows.some(x=>x.state==='STALE')?'STALE':bestAvailabilityStatus(relevant,'NO_DATA');
  return {rows,state,label:'US OPTIONS'};
 }
 if(id==='crypto'){
  const rows=[...arr(LI.crypto_derivatives),...arr(LI.crypto_options)];const relevant=liveStatuses.filter(x=>/BINANCE|BYBIT|OKX|DERIBIT|COINGLASS|CRYPTO/i.test(`${x.provider||''} ${x.dataset||''}`));
  const state=rows.some(x=>x.state==='LIVE')?'LIVE':rows.some(x=>x.state==='STALE')?'STALE':bestAvailabilityStatus(relevant,'NO_DATA');
  return {rows,state,label:'PERPS + OPTIONS'};
 }
 if(id==='commodity'){
  const db=arr(FLD.databento).filter(x=>/CL|GC|SI|HG|NG|BZ|OIL|GOLD|SILVER|COPPER/i.test(String(x.symbol||x.raw_symbol||'')));
  const cot=Object.values(obj(FLD.cftc)).flatMap(x=>arr(obj(x).rows)); const rows=[...db,...cot];
  const relevant=fullStatuses.filter(x=>/DATABENTO|CFTC/i.test(`${x.provider||''} ${x.dataset||''}`));
  return {rows,state:rows.length?'LIVE':bestAvailabilityStatus(relevant,'NO_DATA'),label:'FUTURES OI / COT'};
 }
 if(id==='fx'){
  const db=arr(FLD.databento).filter(x=>/6E|6J|6B|6A|DX|EUR|JPY|GBP|AUD|DOLLAR/i.test(String(x.symbol||x.raw_symbol||'')));
  const tff=arr(obj(obj(FLD.cftc).tff_futures).rows);const rows=[...db,...tff];
  const relevant=fullStatuses.filter(x=>/DATABENTO|CFTC/i.test(`${x.provider||''} ${x.dataset||''}`));
  return {rows,state:rows.length?'LIVE':bestAvailabilityStatus(relevant,'NO_DATA'),label:'FX FUTURES / COT'};
 }
 if(id==='idx')return {rows:[],state:'CASH_ONLY',label:'CASH LONG-ONLY'};
 return {rows:[],state:'NO_DATA',label:'DERIVATIVES'};
}
function marketDerivativeLedger(id){
 const c=marketDerivativeContext(id);return c.rows.slice(0,20).map(x=>({time:x.timestamp||x.report_date_as_yyyy_mm_dd||FLD.generated,ticker:x.symbol||x.market_and_exchange_names||x.ticker||c.label,desc:`${c.label} · ${x.stat_type||x.dataset||x.report_date_as_yyyy_mm_dd||'observed record'} · OI/positioning does not identify initiating side`,state:x.state||'LIVE',raw:x}));
}


function marketSetups(id){return arr(obj(obj(D.markets)[id]).setups).filter(x=>x&&x.tk&&x.tk!=='—');}
function marketObj(id){return obj(obj(D.markets)[id]);}
function setupDirection(s){
 const a=String(s?.act||s?.ty||'').toUpperCase();
 if(/SHORT|SELL|DISTRIB|BREAKDOWN|REDUCE/.test(a))return 'short';
 if(/LONG|BUY|BUILD|ACCUM|BREAKOUT/.test(a))return 'long';
 return 'neutral';
}
function biasDirection(b){
 const x=String(b||'').toUpperCase();
 if(/SHORT|BEAR|RISK_OFF|DEFENS/.test(x))return 'short';
 if(/LONG|BULL|RISK_ON|CONSTRUCT/.test(x))return 'long';
 return 'neutral';
}
function isSetupAligned(marketId,marketBias,s){
 const sd=setupDirection(s), bd=biasDirection(marketBias);
 if(marketId==='idx' && sd==='short')return false;
 if(sd==='neutral'||bd==='neutral')return true;
 return sd===bd;
}
function marketOfCandidate(c){return c?.market||c?.market_id||c?.source_market||null;}
function edgeAllowed(a,b){
 if(!a||!b)return false;
 const blocked=new Set(['no_data','error','not_configured','not_loaded','not_entitled','action_required','offline','initializing','empty','no_signal']);
 return !(blocked.has(normalizeState(a.state))||blocked.has(normalizeState(b.state)));
}
function connectPairs(graph,pairs){
 pairs.forEach(p=>{
  const [a,b,stateName='neutral',evidence='inferred',label='',extra={}]=p;
  if(a&&b)graph.edges.push(edge(a.id||a,b.id||b,stateName,evidence,label,extra.width||1.7,extra));
 });
}

function firstCandidates(limit=8){
 const out=[];
 Object.entries(obj(D.markets)).forEach(([marketId,m])=>{
  const bias=m?.bias||'NO_DATA';
  arr(m?.setups).forEach(s=>{
   if(!s?.tk||s.tk==='—')return;
   const aligned=isSetupAligned(marketId,bias,s);
   out.push({ticker:s.tk,score:num(s.conv)||0,why:s.why,stage:s.act||s.ty,evidence:'observed',market:marketId,aligned,bias,raw:s});
  });
  // Keep loaded names available for Company Intel even when no trade setup passes. These rows are
  // explicitly PRICE CONTEXT and never become actionable/aligned candidates.
  arr(breadthFor(marketId).constituents).slice(0,8).forEach(r=>{
   const ticker=r.ticker||r.tk;if(ticker&&!out.some(x=>x.ticker===ticker))out.push({ticker,score:0,why:`Loaded price context · 1D ${pct(r.ret_1d)} · 5D ${pct(r.ret_5d)}`,stage:'PRICE CONTEXT',evidence:'observed',market:marketId,aligned:false,bias,raw:r});
  });
 });
 if(state.mode==='all')arr(D.alpha).forEach(a=>a.tk&&out.push({ticker:a.tk,score:num(a.asymmetry)||0,why:a.node||a.scarcity||a.stage,stage:a.stage||'ALPHA',evidence:'structural',market:a.market||a.domain||null,aligned:false,raw:a}));
 const seen=new Set();
 return out.filter(x=>!seen.has(x.ticker)&&seen.add(x.ticker))
  .sort((a,b)=>(Number(b.aligned)-Number(a.aligned))||(b.score-a.score)).slice(0,limit);
}

function modelMission(){
 const sys=obj(D.systemic), markets=obj(D.markets);
 const l0=[node('liq','GLOBAL LIQUIDITY','macro/liquidity observations',short(sys.liquidity||'NO_DATA',18),sys.liquidity,'observed',{raw:sys})];
 const l1=[node('regime','REGIME',`growth ${fmt(sys.growth_roc)} · inflation ${fmt(sys.infl_roc)}`,sys.quad_name||sys.quad||'NO_DATA',sys.quad_name||sys.quad,'inferred',{raw:sys})];
 const ids=[['us','US'],['idx','IHSG'],['crypto','CRYPTO'],['commodity','COMMOD'],['fx','FX']];
 const l2=ids.map(([id,label])=>{const m=obj(markets[id]);return node('m_'+id,label,`${obj(m.funnel).setups||0} surfaced`,m.bias||'NO_DATA',m.bias,'inferred',{raw:m,market:id});});
 const all=firstCandidates(80).filter(c=>c.evidence==='observed'&&c.aligned);
 const perMarket=[];
 ids.forEach(([id])=>{const c=all.filter(x=>x.market===id).sort((a,b)=>b.score-a.score)[0];if(c)perMarket.push(c);});
 const l3=perMarket.length?perMarket.map((c,i)=>node('c_'+i,c.ticker,short(c.why,34),c.stage||'CANDIDATE',c.stage,c.evidence||'observed',{raw:c,market:c.market})):[node('none','NO ALIGNED ACTIONABLE TICKER','data loaded; current gates emitted no actionable ticker','NO_SIGNAL','NO_SIGNAL')];
 const g=layered([l0,l1,l2,l3]);
 // Keep each overview candidate directly below its actual parent market to eliminate crossing lines.
 l3.forEach(c=>{if(c.id==='none')return;const parent=l2.find(m=>m.market===c.market);if(parent)c.x=parent.x;});
 // derived relationship: liquidity is an input to the regime model, not an observed cash-flow ledger.
 if(edgeAllowed(l0[0],l1[0]))g.edges.push(edge('liq','regime','watch','inferred','model input',1.8,{active:false,relation:'model_input'}));
 l2.forEach(m=>{if(edgeAllowed(l1[0],m))g.edges.push(edge('regime',m.id,m.state,'inferred','regime filter',1.7,{active:false,relation:'regime_filter'}));});
 l3.forEach(c=>{
  if(c.id==='none')return;
  const parent=l2.find(m=>m.market===c.market);
  if(parent&&edgeAllowed(parent,c))g.edges.push(edge(parent.id,c.id,c.state,'inferred','aligned setup',2.0,{active:true,relation:'candidate_lineage'}));
 });
 const rotationsIn=arr(sys.rotation_in), rotationsOut=arr(sys.rotation_out);
 return {title:'MISSION CONTROL',sub:'World → regime → market → aligned candidate. Every candidate arrow now follows its actual market lineage; no index/modulo routing.',canvas:'GLOBAL CAPITAL STATE',badges:['observed','inferred'],graph:g,
  rail:basicRail(`Quad ${fmt(sys.quad||'—')} · ${fmt(sys.quad_name||'NO_DATA')}`,
   `Liquidity: ${fmt(sys.liquidity)}. Cross-asset: ${fmt(sys.cross_asset)}.`,
   rotationsIn.length?`Rotation-in candidates: ${rotationsIn.join(', ')}`:'No validated rotation-in list.',
   perMarket.map(x=>x.ticker).join(' → ')||'Wait for aligned data and conviction gates.',
   rotationsOut.length?`Rotation-out: ${rotationsOut.join(', ')}`:'Alternative path not confirmed.',
   `Shock ${fmt(sys.shock_prob)} · Fragility ${fmt(sys.fragility)}`,'Driven by active regime horizon',55,'OPEN THE STRONGEST EVIDENCE PATH'),
  ledger:arr(obj(D.data_health).sources).slice(0,14).map(x=>({time:obj(D.meta).generated,ticker:x.provider,desc:`${x.dataset}: ${x.note}`,state:x.state})), queue:firstCandidates(20).filter(x=>x.aligned).slice(0,8)};
}

function modelMacro(){
 const s=obj(D.systemic), mo=obj(D.macro_observations); const macroCount=Object.keys(mo).length;
 const growth=node('growth','GROWTH','rate of change',fmt(s.growth_roc),s.growth_roc>0?'constructive':s.growth_roc<0?'destructive':'NO_DATA','observed');
 const infl=node('infl','INFLATION','rate of change',fmt(s.infl_roc),s.infl_roc>0?'watch':s.infl_roc<0?'constructive':'NO_DATA','observed');
 const liq=node('liqm','LIQUIDITY','Fed/Treasury/credit',short(s.liquidity||'NO_DATA',16),s.liquidity,'observed');
 const credit=node('credit','CREDIT','HY OAS / funding',fmt(s.fragility),s.fragility,'observed');
 const policy=node('policy','OFFICIAL MACRO FEEDS',`${macroCount} current series`,macroCount?'LIVE':'NO_DATA',macroCount?'constructive':'NO_DATA','observed',{raw:mo});
 const drivers=[growth,infl,liq,credit,policy];
 const regime=node('macroreg','FORWARD REGIME',`quad ${fmt(s.quad)}`,s.quad_name||'NO_DATA',s.quad_name,'inferred');
 const risk=node('risk','RISK ASSETS','cross-asset',s.cross_asset||'NO_DATA',s.cross_asset,'inferred');
 const def=node('def','DEFENSIVES','shock sensitivity',fmt(s.shock_prob),s.shock_prob,'inferred');
 const em=node('em','EM ROTATION','regional confirmation',Object.keys(obj(D.regional)).length?'AVAILABLE':'NO_DATA',Object.keys(obj(D.regional)).length?'watch':'NO_DATA','inferred');
 const outputs=[risk,def,em]; const g=layered([drivers,[regime],outputs]);
 connectPairs(g,[[growth,regime,'watch','inferred','quad input'],[infl,regime,'watch','inferred','quad input'],[policy,regime,'watch','inferred','data context'],[liq,risk,'watch','inferred','liquidity transmission'],[credit,risk,'watch','inferred','credit transmission'],[regime,risk,s.cross_asset||'watch','inferred','regime filter'],[regime,def,'watch','structural','regime sensitivity'],[liq,em,'watch','inferred','funding condition']]);
 return {title:'MACRO & REGIME',sub:'Only explicit model inputs/transmission paths are connected; the map no longer draws a full Cartesian web.',canvas:'MACRO TRANSMISSION MAP',badges:['observed','inferred'],graph:g,
 rail:basicRail(s.quad_name||'NO_DATA',`Growth RoC ${fmt(s.growth_roc)} · Inflation RoC ${fmt(s.infl_roc)}.`, `Liquidity ${fmt(s.liquidity)}`,`Confirm through price, breadth and credit before allocation.`,`Market-implied regime can disagree with economic data.`,`Regime invalidates when its underlying driver directions reverse.`,'Structural / monthly / weekly / daily',50,'USE AS FILTER, NOT A STANDALONE TRADE'),
 ledger:[...Object.entries(mo).slice(0,30).map(([k,v])=>({time:v.timestamp,ticker:k,desc:`value ${fmt(v.value)} · 1p ${pct(v.change_1_period_pct)} · 4p ${pct(v.change_4_period_pct)}`,state:v.state||'LIVE',raw:v})),...coverageRows('macro_regime')],queue:firstCandidates(20).filter(x=>x.aligned).slice(0,6)};
}

function modelEarly(){
 const s=obj(D.systemic), b=breadthFor('us');
 const valStatus=coverageFor('early_warning').state||'ACTION_REQUIRED';
 const val=node('val','VALUATION','requires point-in-time valuation feed',valStatus,valStatus,'observed',{raw:coverageFor('early_warning')});
 const breadth=node('breadth','BREADTH',`${b.coverage||0} loaded names`,b.state==='LIVE'?`${fmt(b.above_50d_pct)}% >50D`:'NO_DATA',b.advance_pct>=55?'constructive':b.advance_pct<45?'destructive':'watch','observed',{raw:b});
 const liq=node('liqstress','LIQUIDITY','funding condition',short(s.liquidity||'NO_DATA',14),s.liquidity,'observed',{raw:s});
 const frag=node('frag','FRAGILITY','systemic',fmt(s.fragility),s.fragility,'inferred');
 const vol=node('vol','VOLATILITY','stress transmission',fmt(s.shock_prob),s.shock_prob,'inferred');
 const credit=node('credit2','CREDIT SPREADS','confirmation',fmt(s.fragility),s.fragility,'observed');
 const risk=node('riskstate','RISK STATE','not a forecast',s.defer_longs?'DEFER LONGS':'MONITOR',s.defer_longs?'destructive':'watch','inferred');
 const first=[val,breadth,liq,frag], mid=[vol,credit], end=[risk]; const g=layered([first,mid,end]);
 connectPairs(g,[[breadth,vol,'watch','inferred','breadth stress'],[liq,credit,'watch','inferred','funding channel'],[frag,credit,'watch','inferred','fragility channel'],[credit,vol,'watch','inferred','credit-vol transmission'],[breadth,risk,'watch','inferred','confirmation'],[credit,risk,s.defer_longs?'destructive':'watch','inferred','confirmation'],[vol,risk,s.defer_longs?'destructive':'watch','inferred','confirmation']]);
 return {title:'EARLY WARNING',sub:'Explicit risk paths only. Missing liquidity/valuation nodes do not emit active causal arrows.',canvas:'RISK PROPAGATION NETWORK',badges:['observed','inferred'],graph:g,
 rail:basicRail(s.defer_longs?'DEFENSIVE POSTURE':'NO SYSTEMIC CONFIRMATION',`Shock probability: ${fmt(s.shock_prob)} · Fragility: ${fmt(s.fragility)}.`,`Current state is a conditional warning, not a crash prediction.`,`Watch breadth → credit → volatility sequence.`,`False alarm if breadth and credit recover while liquidity improves.`,`Invalidation comes from source metrics, not price narrative.`,'Event-dependent',s.defer_longs?70:35,s.defer_longs?'REDUCE FRAGILITY / DEFER NEW LONGS':'MONITOR CONFIRMATION'),
 ledger:[...(b.constituents||[]).slice(0,20).map(x=>({time:obj(D.meta).generated,ticker:x.ticker,desc:`1D ${pct(x.ret_1d)} · 5D ${pct(x.ret_5d)} · >20D ${fmt(x.above_20d)}`,state:x.ret_1d>0?'constructive':x.ret_1d<0?'destructive':'neutral',raw:x})),...coverageRows('early_warning')],queue:[]};
}

function modelAlpha(){
 const structural=arr(D.alpha);
 const live=firstCandidates(30).filter(x=>x.evidence==='observed'&&x.aligned);
 if(state.mode!=='all'){
  if(!live.length){
   const observed=firstCandidates(24).filter(x=>x.evidence==='observed');
   const center=node('alpha_no_signal','ALPHA RESEARCH GATE','price data loaded; no candidate passed all gates','NO_SIGNAL','NO_SIGNAL','inferred',{x:500,y:310});
   const rejected=observed.slice(0,12).map((a,i)=>{const angle=(i/Math.max(1,observed.length))*Math.PI*2;return node('ar_'+i,a.ticker,`${String(a.market||'').toUpperCase()} · conflicts with ${a.bias||'market state'}`,'FAILED CURRENT GATE','watch','observed',{x:500+Math.cos(angle)*190,y:310+Math.sin(angle)*190,raw:a,market:a.market});});
   const g={nodes:[center,...rejected],edges:rejected.map(n=>edge(n.id,'alpha_no_signal','watch','inferred','did not clear all gates',1.4,{relation:'failed_gate'}))};
   return {title:'ALPHA CENTER',sub:'NO_SIGNAL is not NO_DATA: live price/setup inputs loaded, but nothing currently clears direction, conviction and evidence gates.',canvas:'LIVE OPPORTUNITY GATE',badges:['observed','inferred'],graph:g,
    rail:basicRail('NO SIGNAL','No candidate currently passes the complete observed gate.','Data is available; do not force a trade.','Wait for market alignment, stronger price evidence or independent confirmation.','Rejected candidates remain visible for audit, not recommendation.','Any candidate remains invalid until all required gates pass.','Until state changes',0,'NO ACTION'),
    ledger:observed.slice(0,20).map(a=>({time:obj(D.meta).generated,ticker:a.ticker,desc:`FAILED CURRENT GATE · ${a.market} · bias ${a.bias} · ${a.stage} · ${a.why}`,state:'NO_SIGNAL',raw:a})),queue:[]};
  }
  const center=node('alpha_live_core','LIVE ALPHA GATE','market → setup → evidence','OBSERVED CANDIDATES','watch','inferred',{x:500,y:310});
  const nodes=live.slice(0,16).map((a,i)=>{const angle=(i/Math.max(1,live.length))*Math.PI*2;const radius=140+(i%2)*62;return node('al_'+i,a.ticker,`${String(a.market||'').toUpperCase()} · ${a.bias||'—'}`,`${a.stage||'SETUP'} · ${Math.round(a.score||0)}`,a.stage,'observed',{x:500+Math.cos(angle)*radius,y:310+Math.sin(angle)*radius,raw:a,market:a.market});});
  const g={nodes:[center,...nodes],edges:nodes.map(n=>edge('alpha_live_core',n.id,n.state,'inferred','passed live gate',1.8,{active:true,relation:'live_alpha_gate'}))};
  const lead=live[0];
  return {title:'ALPHA CENTER',sub:'OBSERVED mode now shows only candidates that cleared live market-direction and setup gates. Structural moonshots remain separate.',canvas:'LIVE OPPORTUNITY CONSTELLATION',badges:['observed','inferred'],graph:g,
   rail:basicRail(`${lead.ticker} · ${lead.stage}`,lead.why||'Top live-gated candidate.',`Market ${String(lead.market).toUpperCase()} · bias ${lead.bias}.`,`Require independent institutional/fundamental confirmation before promotion.`,`A live setup can fail; this is not a generational-alpha claim.`,`Invalidate on setup stop, data staleness or market-bias reversal.`,'Setup-specific',Math.min(90,lead.score||0),'OPEN CANDIDATE TRACE'),
   ledger:live.slice(0,20).map(a=>({time:obj(D.meta).generated,ticker:a.ticker,desc:`LIVE-GATED · ${a.market} · ${a.bias} · ${a.stage} · ${a.why}`,state:a.stage,raw:a})),queue:live.slice(0,8)};
 }
 if(!structural.length)return emptyModel('ALPHA CENTER','No structural candidate is available from the alpha research contract.');
 const nodes=structural.slice(0,18).map((a,i)=>{const score=num(a.asymmetry)||0; const angle=(i/structural.length)*Math.PI*2; const radius=130+(i%3)*58; return node('a_'+i,a.tk,`${String(a.market||'').toUpperCase()} · ${a.stage||'stage —'}`,`ASYM ${score}`,score>=70?'constructive':score>=50?'watch':'neutral','structural',{x:500+Math.cos(angle)*radius,y:310+Math.sin(angle)*radius,raw:a});});
 const center=node('alpha_core','ALPHA RESEARCH GATE','macro → bottleneck → mispricing','HYPOTHESIS',structural.length?'watch':'NO_DATA','inferred',{x:500,y:310});
 const g={nodes:[center,...nodes],edges:nodes.map(n=>edge('alpha_core',n.id,n.state,'structural','hypothesis',1.5,{relation:'structural_hypothesis'}))};
 return {title:'ALPHA CENTER',sub:'ALL LAYERS shows structural hypotheses. These are not promoted to Mission Control until live gates confirm.',canvas:'STRUCTURAL OPPORTUNITY CONSTELLATION',badges:['structural','inferred'],graph:g,
 rail:basicRail(structural[0].tk,`${structural[0].node||structural[0].scarcity||'Top structural hypothesis'} · tier ${fmt(structural[0].tier)}.`,`Stage: ${fmt(structural[0].stage)} · scarcity: ${fmt(structural[0].scarcity)}`,`Require live market, institutional and price confirmation before promotion.`,`Most high-asymmetry hypotheses fail; structural upside is not a return forecast.`,`Kill thesis and data gates must be explicit.`,'Candidate-specific',Math.min(65,num(structural[0].asymmetry)||35),'OPEN RESEARCH TRACE'),
 ledger:structural.slice(0,12).map(a=>({time:obj(D.meta).generated,ticker:a.tk,desc:`STRUCTURAL · ${a.node||a.scarcity} · gated: ${arr(a.gated).join(', ')||'none'}`,state:'watch'})),queue:structural.slice(0,8).map(a=>({ticker:a.tk,score:num(a.asymmetry)||0,why:a.node||a.scarcity,stage:`STRUCTURAL · ${a.stage||'hypothesis'}`}))};
}

function modelInstitutional(){
 const I=obj(D.institutional), statuses=arr(I.statuses), events=arr(I.events); const providers=statuses.length?statuses:[
  {provider:'Unusual Whales',dataset:'options_flow',state:'NOT_CONFIGURED',note:'Set API key'},
  {provider:'Massive / UW',dataset:'dark_pool',state:'NOT_CONFIGURED',note:'Set API key'},
  {provider:'SEC EDGAR',dataset:'filings',state:'NOT_LOADED',note:'Direct public feed'},
  {provider:'Nansen',dataset:'smart_money',state:'NOT_CONFIGURED',note:'Set API key'},
  {provider:'Arkham',dataset:'labeled_transfers',state:'NOT_CONFIGURED',note:'Set API key'}];
 const pnodes=providers.map((p,i)=>node('p_'+i,p.provider,p.dataset,p.state,p.state,'observed',{raw:p,provider:p.provider}));
 const tickerNames=[...new Set(events.map(e=>e.ticker).filter(Boolean))].slice(0,8);
 const tickers=tickerNames.map((t,i)=>node('it_'+i,t,'observed event cluster',`${events.filter(e=>e.ticker===t).length} events`,'watch','observed',{raw:{ticker:t,events:events.filter(e=>e.ticker===t)},ticker:t}));
 const gate=node('iscore','EVIDENCE GATE','cross-source reconciliation',events.length?'EVIDENCE ACTIVE':'NO_SIGNAL',events.length?'watch':'NO_SIGNAL','inferred');
 const last=tickers.length?tickers:[node('ino','NO LIVE INSTITUTIONAL EVENTS','public SEC may need user-agent; licensed enrichments need entitlement','NO_SIGNAL','NO_SIGNAL')];
 const g=layered([pnodes,last,[gate]]);
 function providerMatches(p,e){const s=(String(p.provider)+' '+String(p.dataset)).toUpperCase(),t=String(e.event_type||'').toUpperCase(),ep=String(e.provider||'').toUpperCase();return s.includes(ep)||ep.includes(String(p.provider).toUpperCase())||(t==='OPTIONS_FLOW'&&/UNUSUAL|OPTION/.test(s))||(t==='DARK_POOL'&&/MASSIVE|DARK|TRF/.test(s))||(t==='SEC_FILING'&&/SEC/.test(s))||(t==='SMART_MONEY'&&/NANSEN/.test(s))||(t==='ARKHAM_TRANSFER'&&/ARKHAM/.test(s));}
 tickers.forEach(tn=>{events.filter(e=>e.ticker===tn.ticker).forEach(e=>{const p=pnodes.find(n=>providerMatches(n.raw,e));if(p)g.edges.push(edge(p.id,tn.id,eventState(e),'observed',e.event_type,1.8,{active:true,relation:'observed_event'}));});g.edges.push(edge(tn.id,gate.id,'watch','inferred','reconcile',1.6,{relation:'evidence_gate'}));});
 const lead=events[0];
 return {title:'INSTITUTIONAL POSITIONING',sub:'Arrows now mean an actual provider/event/ticker lineage. A provider is never connected to a ticker it did not observe.',canvas:'INSTITUTIONAL EVIDENCE MAP',badges:['observed','inferred'],graph:g,
 rail:basicRail(lead?`${lead.ticker} · ${lead.event_type}`:(I.overall_state||'NOT CONFIGURED'),lead?eventDescription(lead):'Connect provider keys. SEC can run without a paid market-data key.',`Observed events: ${events.length}. Active feeds: ${providers.filter(p=>p.state==='LIVE').length}.`,`Cluster repeated evidence and reconcile options with next-day OI / price response.`,`Single prints, hedges, rolls and custody transfers can be noise.`,`Invalidate the inference when follow-through or independent evidence fails.`,'Seconds to quarters by source',lead?60:0,lead?'OPEN RAW EVENT / CROSS-CHECK':'CONFIGURE DATA SOURCES'),
 ledger:events.slice(0,30).map(e=>({time:e.timestamp,ticker:e.ticker||e.provider,desc:eventDescription(e),state:eventState(e)})),queue:institutionalQueue(events)};
}

function eventDescription(e){
 if(e.event_type==='OPTIONS_FLOW')return `${e.option_type||''} ${e.contract||''} · ${money(e.premium)} · ${arr(e.flags).join('/')||e.classification||'trade-side'}`;
 if(e.event_type==='DARK_POOL')return `TRF print ${money(e.premium)} @ ${fmt(e.price)} · ${e.nbbo_location||'location unknown'} · intent unconfirmed`;
 if(e.event_type==='SEC_FILING')return `${e.form} · ${e.description||e.company||'SEC filing'}`;
 if(e.event_type==='SMART_MONEY')return `${e.chain||''} · holdings ${money(e.value_usd)} · 24h ${pct(e.change_24h_pct)}`;
 if(e.event_type==='ARKHAM_TRANSFER')return `${e.chain||''} · ${e.from_entity||'unknown'} → ${e.to_entity||'unknown'} · ${money(e.value_usd)} · intent unconfirmed`;
 if(e.event_type==='DERIVATIVES_STATE'||e.event_type==='OPTIONS_STATE')return e.description||`${e.state||'CONTEXT'} · not a calibrated probability`;
 return short(JSON.stringify(e),100);
}
function eventState(e){if(e.event_type==='SMART_MONEY')return normalizeState(e.classification); if(e.event_type==='OPTIONS_FLOW')return /CALL_ASK|PUT_BID/.test(e.classification||'')?'constructive':/PUT_ASK|CALL_BID/.test(e.classification||'')?'destructive':'watch'; return 'watch';}
function institutionalQueue(events){const m={};events.forEach(e=>{const t=e.ticker||'—';if(!m[t])m[t]={ticker:t,score:0,why:[],stage:'EVIDENCE'};m[t].score+=e.event_type==='SEC_FILING'?18:e.event_type==='OPTIONS_FLOW'?12:e.event_type==='DARK_POOL'?9:10;m[t].why.push(e.event_type);});return Object.values(m).sort((a,b)=>b.score-a.score).slice(0,8).map(x=>({...x,why:[...new Set(x.why)].join(' + ')}));}

function derivativeLedgerRows(kind='all'){
 const rows=[];
 if(kind==='all'||kind==='crypto')arr(LI.crypto_derivatives).forEach(x=>rows.push({time:LI.generated,ticker:x.asset,desc:`${x.positioning_quadrant||'NO HISTORY'} · funding ${fmt(x.funding_rate_mean)} · OI Δ ${pct(x.oi_change_since_reference_pct)} · short/long squeeze ${fmt(x.short_squeeze_pressure)}/${fmt(x.long_squeeze_pressure)}`,state:x.state,raw:x}));
 if(kind==='all'||kind==='us')arr(LI.us_options).forEach(x=>{const c=obj(x.integrated_context);rows.push({time:LI.generated,ticker:x.ticker,desc:`${c.directional_context||x.directional_context||'NO DATA'} · ${c.volatility_context||'NO VEGA'} · ${c.gamma_context||x.gamma_context||'NO GAMMA'} · evidence ${fmt(c.evidence_completeness_pct)}% · ${c.horizon_context||('expiry '+fmt(x.nearest_expiry))}`,state:x.state,raw:x});});
 if(kind==='all'||kind==='us')arr(LI.us_squeeze).forEach(x=>rows.push({time:LI.generated,ticker:x.ticker,desc:`short/long squeeze pressure ${fmt(x.short_squeeze_pressure)}/${fmt(x.long_squeeze_pressure)} · probability not calibrated`,state:x.state,raw:x}));
 return rows;
}
function derivativeQueue(kind='all'){
 const rows=[];
 if(kind==='all'||kind==='crypto')arr(LI.crypto_derivatives).forEach(x=>rows.push({ticker:x.asset,score:Math.max(num(x.short_squeeze_pressure)||0,num(x.long_squeeze_pressure)||0),why:`${x.positioning_quadrant||'NO HISTORY'} · S ${fmt(x.short_squeeze_pressure)} / L ${fmt(x.long_squeeze_pressure)}`,stage:'CRYPTO DERIVATIVES'}));
 if(kind==='all'||kind==='us')arr(LI.us_squeeze).forEach(x=>rows.push({ticker:x.ticker,score:Math.max(num(x.short_squeeze_pressure)||0,num(x.long_squeeze_pressure)||0),why:`S ${fmt(x.short_squeeze_pressure)} / L ${fmt(x.long_squeeze_pressure)} · pressure only`,stage:'US SQUEEZE CONTEXT'}));
 return rows.sort((a,b)=>b.score-a.score).slice(0,10);
}
function modelDerivatives(){
 const statuses=arr(LI.statuses), crypto=arr(LI.crypto_derivatives), options=arr(LI.us_options), ussq=arr(LI.us_squeeze), copt=arr(LI.crypto_options), marketOpt=obj(LI.market_options_context);
 const providerRows=[...new Map(statuses.map(x=>[`${x.provider}:${x.dataset}`,x])).values()].slice(0,10);
 const providers=providerRows.map((x,i)=>node('lp_'+i,x.provider,short(x.dataset,28),x.state,x.state,'observed',{raw:x,provider:x.provider,dataset:x.dataset}));
 const usOpt=node('dom_us','US OPTIONS',`${options.filter(x=>x.state!=='NO_DATA').length}/${options.length} chains`,options.some(x=>x.state==='LIVE')?'LIVE':'NO_DATA',options.some(x=>x.state==='LIVE')?'constructive':'NO_DATA','observed');
 const shortB=node('dom_si','SHORT / BORROW',`${arr(LI.us_short_interest).length} tickers`,arr(LI.us_short_interest).length?'LIVE':'NO_DATA',arr(LI.us_short_interest).length?'watch':'NO_DATA','observed');
 const cp=node('dom_cp','CRYPTO PERPS',`${crypto.filter(x=>x.state!=='NO_DATA').length} assets`,crypto.some(x=>x.state==='LIVE')?'LIVE':'NO_DATA',crypto.some(x=>x.state==='LIVE')?'constructive':'NO_DATA','observed');
 const co=node('dom_co','CRYPTO OPTIONS',`${copt.filter(x=>x.state!=='NO_DATA').length} assets`,copt.some(x=>x.state==='LIVE')?'LIVE':'NO_DATA',copt.some(x=>x.state==='LIVE')?'watch':'NO_DATA','observed');
 const domains=[usOpt,shortB,cp,co];
 const oi=node('eng_oi','OI + FUNDING','build / cover / liquidation','STATE ENGINE','watch','inferred');
 const greeks=node('eng_g','GAMMA / VANNA / CHARM','signed-OI proxy unless live side known','GREEKS CONTEXT','watch','inferred');
 const squeeze=node('eng_sq','SQUEEZE PRESSURE','ingredients, not probability','PRESSURE INDEX','watch','inferred');
 const zones=node('eng_z','REFERENCE ZONES','walls / expected move / liquidation','NOT TARGETS','watch','inferred');
 const rot=node('eng_rot','OPTIONS ROTATION',`${arr(marketOpt.sector_rotation).length} sectors`,marketOpt.state||'NO_DATA',marketOpt.state,'observed',{raw:marketOpt});
 const engines=[oi,greeks,squeeze,zones,rot];
 const targets=[...crypto.map((x,i)=>node('dc_'+i,x.asset,short(x.positioning_quadrant,31),`S${fmt(x.short_squeeze_pressure)} / L${fmt(x.long_squeeze_pressure)}`,Math.max(num(x.short_squeeze_pressure)||0,num(x.long_squeeze_pressure)||0)>=70?'watch':x.state,'observed',{raw:x,targetType:'crypto'})),...ussq.filter(x=>x.state!=='NO_DATA').slice(0,6).map((x,i)=>node('du_'+i,x.ticker,'US forced-flow context',`S${fmt(x.short_squeeze_pressure)} / L${fmt(x.long_squeeze_pressure)}`,Math.max(num(x.short_squeeze_pressure)||0,num(x.long_squeeze_pressure)||0)>=70?'watch':x.state,'observed',{raw:x,targetType:'us'}))];
 const last=targets.length?targets:[node('dt0','NO DERIVATIVES CONTEXT','connect feeds / wait for history','NO_DATA','NO_DATA')];
 const g=layered([providers.length?providers:[node('lp0','LIVE PROVIDERS','public endpoints unavailable','NO_DATA','NO_DATA')],domains,engines,last]);
 function pd(p,d){const x=(String(p.provider)+' '+String(p.dataset)).toUpperCase();if(d===usOpt)return /MASSIVE|UNUSUAL|OPTION/.test(x);if(d===shortB)return /ORTEX|INTRINIO|SHORT|BORROW/.test(x);if(d===cp)return /BINANCE|BYBIT|OKX|COINGLASS/.test(x);if(d===co)return /DERIBIT|OPTION/.test(x);return false;}
 providers.forEach(p=>domains.filter(d=>pd(p.raw,d)).forEach(d=>g.edges.push(edge(p.id,d.id,'watch','observed','feed',1.6,{active:p.state==='live',relation:'provider_domain'}))));
 connectPairs(g,[[usOpt,greeks,'watch','inferred','surface'],[usOpt,zones,'watch','inferred','walls/EM'],[usOpt,rot,'watch','inferred','sector flow'],[usOpt,squeeze,'watch','inferred','option pressure'],[shortB,squeeze,'watch','inferred','borrow pressure'],[cp,oi,'watch','inferred','OI/funding'],[cp,squeeze,'watch','inferred','forced flow'],[cp,zones,'watch','inferred','liquidations'],[co,greeks,'watch','inferred','option surface'],[co,zones,'watch','inferred','walls/EM'],[co,squeeze,'watch','inferred','option pressure']]);
 targets.forEach(t=>{if(t.targetType==='crypto'){[oi,squeeze,zones,greeks].forEach(e=>g.edges.push(edge(e.id,t.id,t.state,'inferred','context',1.4,{relation:'engine_target'})));}else{[greeks,squeeze,zones,rot].forEach(e=>g.edges.push(edge(e.id,t.id,t.state,'inferred','context',1.4,{relation:'engine_target'})));}});
 const queue=derivativeQueue('all'), lead=queue[0]; const leadRaw=crypto.find(x=>x.asset===lead?.ticker)||ussq.find(x=>x.ticker===lead?.ticker);
 return {title:'DERIVATIVES / SQUEEZE',sub:'Each arrow now follows a valid provider → domain → engine → asset path; no all-to-all inference web.',canvas:'DERIVATIVES PRESSURE MAP',badges:['observed','inferred'],graph:g,
  rail:{...basicRail(lead?`${lead.ticker} · ${lead.stage}`:(LI.overall_state||'NO DATA'),lead?lead.why:'No asset has enough current derivatives evidence.',`Live providers ${num(obj(LI.status_counts).live)||0}/${num(obj(LI.status_counts).total)||0}. OI and funding are interpreted jointly with price.`,`Require persistence, price confirmation and a reachable liquidity/reference zone before acting.`,`Crowding can unwind slowly or be hedged; a high pressure index can remain high without a squeeze.`,`Data stale, OI units incomparable, or price/OI quadrant reverses.`,leadRaw?.horizon_context||'Intraday funding/OI; expiry-specific options horizon',lead?Math.min(95,lead.score):0,'OPEN RAW VENUES / REFERENCE ZONES'),confidenceLabel:'EVIDENCE COMPLETENESS'},
  ledger:[...derivativeLedgerRows('all'),...statuses.slice(0,30).map(x=>({time:x.fetched_at,ticker:x.provider,desc:`${x.dataset} · ${x.note}`,state:x.state,raw:x}))],queue};
}

function modelMarket(id,title){
 const m=marketObj(id), allSetups=marketSetups(id), setups=allSetups.filter(s=>isSetupAligned(id,m.bias,s)), drivers=arr(m.drivers), b=breadthFor(id), tab=id==='idx'?'ihsg':id==='commodity'?'commodities':id==='fx'?'fx':id==='crypto'?'crypto':'us_stocks';
 const l0=drivers.length?drivers.slice(0,6).map((d,i)=>node('d_'+i,String(d).replaceAll('_',' ').toUpperCase(),'market-specific driver','INPUT','neutral','structural',{raw:d})):[node('dn','DRIVER FEEDS','none mapped','NO_DATA','NO_DATA')];
 const derivCtx=marketDerivativeContext(id), liveRows=derivCtx.rows, liveState=derivCtx.state;
 const stateNode=node('mbias',title+' STATE',`${obj(m.funnel).universe||0} loaded`,m.bias||'NO_DATA',m.bias,'inferred',{raw:m});
 const breadthNode=node('breadth_ctx','BREADTH',`${b.coverage||0} names`,b.state==='LIVE'?`${fmt(b.advance_pct)}% ADV`:'NO_DATA',b.advance_pct>=55?'constructive':b.advance_pct<45?'destructive':'watch','observed',{raw:b});
 const derivNode=node('mderiv',derivCtx.label,`${liveRows.length} normalized rows`,liveState,liveState,'observed',{raw:liveRows});
 const l1=[stateNode,breadthNode,derivNode];
 const l2=setups.length?setups.slice(0,8).map((s,i)=>node('s_'+i,s.tk,short(s.why,35),s.act||s.ty||'SETUP',s.act||s.ty,'observed',{raw:s,market:id})):[node('sn','NO ALIGNED SURFACED TICKER',allSetups.length?'setups conflict with market bias':'price data loaded; conviction gate not met','NO_SIGNAL','NO_SIGNAL')];
 const g=layered([l0,l1,l2]);
 l0.forEach(d=>{if(edgeAllowed(d,stateNode))g.edges.push(edge(d.id,stateNode.id,'watch','structural','driver',1.4,{relation:'driver_state'}));});
 if(edgeAllowed(breadthNode,stateNode))g.edges.push(edge(breadthNode.id,stateNode.id,'watch','inferred','breadth confirm',1.5,{relation:'confirmation'}));
 if(edgeAllowed(derivNode,stateNode))g.edges.push(edge(derivNode.id,stateNode.id,'watch','inferred','derivatives confirm',1.5,{relation:'confirmation'}));
 l2.forEach(s=>{if(s.id!=='sn'&&edgeAllowed(stateNode,s))g.edges.push(edge(stateNode.id,s.id,s.state,'inferred','aligned setup',1.9,{active:true,relation:'candidate_lineage'}));});
 const top=setups[0];
 const special=id==='idx'?'IHSG remains long-only; bearish state means wait/reduce, never short.':id==='crypto'?'Wallet/entity flows are separated from protocol TVL and price proxies.':'Market setup requires driver, price and execution agreement.';
 return {title,sub:special,canvas:`${title} DECISION MAP`,badges:['observed','structural','inferred'],graph:g,
 rail:basicRail(top?`${top.tk} · ${top.act}`:(m.bias||'NO_DATA'),top?top.why:(allSetups.length?`Setups exist but conflict with ${fmt(m.bias)} bias.`:`No ticker cleared the gate. Bias: ${fmt(m.bias)}.`),top?`Entry ${fmt(top.e)} · stop ${fmt(top.s)} · target ${fmt(top.t)} · R/R ${fmt(top.rr)}`:'Keep the market state visible without inventing an opportunity.',`Next candidate appears only after full funnel, direction alignment and data checks.`,`Alternative path: market bias can rotate while no individual ticker qualifies.`,top?(top.warn||`Invalidation ${fmt(top.s)}`):'No setup means no trade-level invalidation.','Setup-specific',top?Math.min(95,num(top.conv)||0):0,top?top.act:'NO ACTION'),
 ledger:[...allSetups.map(s=>({time:obj(D.meta).generated,ticker:s.tk,desc:`${s.act} · ${s.why} · ${isSetupAligned(id,m.bias,s)?'ALIGNED':'CONFLICTS WITH MARKET BIAS'} · entry ${fmt(s.e)} / stop ${fmt(s.s)} / target ${fmt(s.t)}`,state:isSetupAligned(id,m.bias,s)?s.act:'watch'})),...derivativeLedgerRows(id==='crypto'?'crypto':id==='us'?'us':'none'),...marketDerivativeLedger(id),...coverageRows(tab)],queue:[...setups.slice(0,8).map(s=>({ticker:s.tk,score:num(s.conv)||0,why:s.why,stage:s.act||s.ty})),...derivativeQueue(id==='crypto'?'crypto':id==='us'?'us':'none')].sort((a,b)=>b.score-a.score).slice(0,8)};
}

function modelFlow(){
 const s=obj(D.systemic), ins=arr(s.rotation_in), outs=arr(s.rotation_out), rot=obj(D.rotation_snapshot), rrows=arr(rot.rows);
 const l0=[node('cash','GLOBAL LIQUIDITY','macro impulse',short(s.liquidity||'NO_DATA',17),s.liquidity,'observed')];
 const out=node('out','ROTATING OUT','confirmed list',outs.length?outs.join(', '):'NO_DATA',outs.length?'destructive':'NO_DATA','inferred');
 const reg=node('reg','REGIME FILTER','cross asset',s.cross_asset||s.quad_name||'NO_DATA',s.cross_asset||s.quad_name,'inferred');
 const l1=[out,reg];
 const marketNodes=Object.entries(obj(D.markets)).map(([id,m])=>node('fm_'+id,(m.label||id).toUpperCase(),`${obj(m.funnel).setups||0} setups`,m.bias||'NO_DATA',m.bias,'inferred',{market:id,raw:m}));
 const optRot=arr(LI.options_sector_rotation).slice(0,8), observedRot=rrows.slice(0,10);
 const l3=optRot.length?optRot.map((t,i)=>node('orin_'+i,String(t.key||'SECTOR').toUpperCase(),`options net premium ${money(t.net)}`,`${t.records||0} BUCKETS`,num(t.net)>=0?'constructive':'destructive','observed',{raw:t,market:'us'})):observedRot.length?observedRot.map((t,i)=>node('rin_'+i,t.ticker,`20D ${pct(t.ret_20d_pct)} · 5D ${pct(t.ret_5d_pct)}`,`RANK ${t.rank_20d}`,t.ret_20d_pct>0?'constructive':'destructive','observed',{raw:t,market:t.market||null})):(ins.length?ins.slice(0,10).map((t,i)=>node('rin_'+i,t,'model rotation-in output','WATCH','watch','inferred',{raw:t,market:null})):[node('rin0','NO ROTATION-IN','no validated list','NO_DATA','NO_DATA')]);
 const g=layered([l0,l1,marketNodes,l3]);
 if(edgeAllowed(l0[0],reg))g.edges.push(edge('cash','reg','watch','inferred','macro filter',1.7,{relation:'model_input'}));
 if(edgeAllowed(reg,out))g.edges.push(edge('reg','out','watch','inferred','rotation state',1.4,{relation:'rotation_state'}));
 marketNodes.forEach(m=>{if(edgeAllowed(reg,m))g.edges.push(edge('reg',m.id,m.state,'inferred','market filter',1.5,{relation:'market_filter'}));});
 l3.forEach(n=>{let parent=marketNodes.find(m=>m.market===n.market);if(!parent&&n.evidence==='inferred')return;if(parent&&edgeAllowed(parent,n))g.edges.push(edge(parent.id,n.id,n.state,n.evidence==='observed'?'observed':'inferred','rotation evidence',1.8,{active:n.evidence==='observed',relation:'rotation_lineage'}));});
 return {title:'FLOW & ROTATION',sub:'Rotation arrows only connect a node to its identified market. Unmapped price/model outputs remain unconnected instead of being assigned arbitrarily.',canvas:'CAPITAL ROTATION MAP',badges:['observed','inferred'],graph:g,
 rail:basicRail(ins.length?`ROTATING INTO ${ins.join(', ')}`:'NO CONFIRMED ROTATION',`Rotating out: ${outs.join(', ')||'none confirmed'}.`,`Current flow view uses only available sources and does not pretend dollar flows reconcile across providers.`,`Follow the path with improving persistence and remaining return.`,`Price-only rotation can reverse without actual fund-flow confirmation.`,`Invalidate when driver and flow direction disagree.`,'Front-run → current → late → exhausted',ins.length?60:10,'OPEN MARKET PATH'),ledger:[...rrows.map(x=>({time:x.timestamp,ticker:x.ticker,desc:`1D ${pct(x.ret_1d_pct)} · 5D ${pct(x.ret_5d_pct)} · 20D ${pct(x.ret_20d_pct)} · price rotation only`,state:x.ret_20d_pct>0?'constructive':'destructive',raw:x})),...coverageRows('flow_rotation')],queue:firstCandidates(20).filter(x=>x.aligned).slice(0,8)};
}

function selectedChain(){const chains=arr(obj(obj(D.reference).chain_reactions).chains);return chains[0]||null;}
function modelSupply(){
 const c=selectedChain(); if(!c)return emptyModel('SUPPLY CHAIN','No chain-reaction reference loaded.');
 const seq=arr(c.propagation_sequence).slice(0,7); const layers=[[node('trigger','TRIGGER',short(c.trigger_event,62),c.trigger_status||'STRUCTURAL',c.trigger_status,'structural',{raw:c})]];
 seq.forEach((s,i)=>layers.push([node('tier_'+i,`TIER ${s.tier} · STEP ${s.step}`,short(s.role,48),arr(s.tickers).slice(0,5).join(' · '),s.tier<=2?'constructive':'watch','structural',{raw:s})]));
 const g=layered(layers); for(let i=0;i<layers.length-1;i++)connectAll(g,layers[i],layers[i+1],'watch','structural');
 return {title:'SUPPLY CHAIN',sub:`Structural reference: ${c.name}. Topology is curated; live activation must be independently observed.`,canvas:'BOTTLENECK CASCADE',badges:['structural'],graph:g,
 rail:basicRail(c.name,short(c.mechanism,220),`Trigger status in reference: ${fmt(c.trigger_status)}.`,`Identify which tier is newly binding and still mispriced.`,`A theme can be real while a selected ticker fails to capture value.`,`Invalidate via capacity response, substitution, demand slowdown or broken pricing power.`,c.horizon||'Structural',45,'SELECT A TIER / VERIFY LIVE EVIDENCE'),
 ledger:seq.map(s=>({time:obj(obj(D.reference).chain_reactions)._schema_version,ticker:arr(s.tickers).slice(0,5).join(', '),desc:`${s.role} · ${s.rationale}`,state:'STRUCTURAL'})),queue:seq.flatMap(s=>arr(s.tickers).slice(0,2).map(t=>({ticker:t,score:Math.max(1,100-s.tier*14),why:s.role,stage:`TIER ${s.tier}`}))).slice(0,8)};
}

function modelCompany(){
 const pool=firstCandidates(80); const cand=(state.selectedTicker&&pool.find(x=>x.ticker===state.selectedTicker))||pool.find(x=>x.aligned)||pool[0]; if(!cand)return emptyModel('COMPANY INTEL','No ticker has usable price/setup data yet. The tab no longer requires an aligned Alpha candidate, but it still requires at least one loaded ticker.');
 const t=cand.ticker, events=arr(obj(D.institutional).events).filter(e=>e.ticker===t), setup=Object.values(obj(D.markets)).flatMap(m=>arr(m.setups)).find(s=>s.tk===t), alpha=arr(D.alpha).find(a=>a.tk===t), fundamental=latestFundamental(t);
 const sec=providerStatus('SEC','company|facts'), instConfigured=arr(obj(D.institutional).statuses).some(x=>!['NOT_CONFIGURED','NOT_ENTITLED','ACTION_REQUIRED'].includes(String(x.state||'').toUpperCase()));
 const root=node('co','COMPANY / TOKEN',cand.why||'loaded candidate',t,cand.aligned?'watch':'NO_SIGNAL','observed',{raw:{cand,setup,alpha,events}});
 const value=node('value','VALUE CAPTURE','bottleneck / role',alpha?.node||alpha?.scarcity||'RESEARCH NOT MAPPED',alpha?'watch':'NO_SIGNAL',alpha?'structural':'observed');
 const fundamentalState=fundamental?'LIVE':(sec?.state||'ACTION_REQUIRED');
 const fund=node('fund','FUNDAMENTALS','SEC filed XBRL',fundamental?'LIVE':fundamentalState,fundamental?'constructive':fundamentalState,'observed',{raw:fundamental||sec});
 const positionState=events.length?'LIVE':(instConfigured?'NO_SIGNAL':'NOT_ENTITLED');
 const pos=node('pos','POSITIONING','options / TRF / filings',events.length?`${events.length} EVENTS`:positionState,events.length?'watch':positionState,'observed');
 const valuation=node('valuation','VALUATION','expected vs market cap',alpha?.upside||'RESEARCH NOT MAPPED',alpha?'watch':'NO_SIGNAL','inferred');
 const price=node('price','PRICE STATE','entry / stop / target',setup?`${fmt(setup.e)} / ${fmt(setup.s)} / ${fmt(setup.t)}`:'NO_SIGNAL',setup?.act||'NO_SIGNAL','observed');
 const kill=node('kill','KILL THESIS','fundamental + price invalidation',setup?.warn||'NOT YET DEFINED',setup?.warn?'destructive':'NO_SIGNAL','inferred');
 const l0=[root],l1=[value,fund,pos],l2=[valuation,price,kill]; const g=layered([l0,l1,l2]);
 connectPairs(g,[[root,value,'watch',value.evidence,'structural role'],[root,fund,'watch','observed','filed facts'],[root,pos,'watch','observed','events'],[value,valuation,'watch','inferred','value capture'],[fund,valuation,'watch','inferred','valuation input'],[fund,kill,'watch','inferred','fundamental invalidation'],[price,kill,'watch','inferred','price invalidation'],[pos,price,'watch','inferred','confirmation only']]);
 return {title:'COMPANY INTEL',sub:'Explicit evidence relationships only; fundamentals, positioning and value capture no longer point to every output.',canvas:`${t} INVESTMENT MAP`,badges:['observed','structural','inferred'],graph:g,
 rail:basicRail(t,cand.why||'Candidate selected from current queue.',setup?`${setup.act} · entry ${fmt(setup.e)} · stop ${fmt(setup.s)}`:'No current executable setup.',events.length?`${events.length} institutional events require interpretation.`:'Wait for independent institutional evidence.',fundamental?'Filed fundamentals loaded; compare matched periods before valuation.':'No fundamentals loaded means the thesis cannot be considered complete.',setup?.warn||`Price invalidation ${fmt(setup?.s)}`,'Company-specific',Math.min(90,cand.score||0),'OPEN EVIDENCE TRACE'),
 ledger:[...(events.slice(0,10).map(e=>({time:e.timestamp,ticker:t,desc:eventDescription(e),state:eventState(e)}))),...(fundamental?[{time:obj(D.meta).generated,ticker:t,desc:`SEC facts · ${Object.keys(fundamental.facts||{}).join(', ')}`,state:'LIVE',raw:fundamental}]:[]),...(setup?[{time:obj(D.meta).generated,ticker:t,desc:`${setup.act} · ${setup.why}`,state:setup.act}]:[]),...coverageRows('company_intel')],queue:[cand]};
}

function modelKnowledge(){
 const c=selectedChain(); if(!c)return emptyModel('KNOWLEDGE GRAPH','No structural knowledge graph reference loaded.');
 const seq=arr(c.propagation_sequence).slice(0,6); const layers=[[node('event','EVENT / STRUCTURAL TRIGGER',short(c.trigger_event,52),c.trigger_status||'REFERENCE','watch','structural',{raw:c})]];
 seq.forEach((s,i)=>layers.push([node('k_'+i,short(s.role,34),arr(s.tickers).slice(0,4).join(' · '),`LAG ${s.horizon_quarters}Q`,'watch','structural',{raw:s})]));
 const g=layered(layers);for(let i=0;i<layers.length-1;i++)g.edges.push(edge(layers[i][0].id,layers[i+1][0].id,'watch','structural',i===0?'economic / physical':'value capture'));
 return {title:'KNOWLEDGE GRAPH',sub:'Edges distinguish observed flow from structural transmission. Structural truth does not imply current mispricing.',canvas:'CAUSAL KNOWLEDGE GRAPH',badges:['structural'],graph:g,
 rail:basicRail(c.name,short(c.mechanism,210),`Chain reference status: ${fmt(c.trigger_status)}.`,`Test each edge for current activation, lag and actual value capture.`,`Narrative/reflexive edges must not be treated like contractual or physical transmission.`,`Invalidate an edge when the mechanism or beneficiary link fails.`,c.horizon||'Variable',40,'TRACE EDGE → SOURCE → INVALIDATION'),ledger:[...seq.map(s=>({time:`+${s.horizon_quarters}Q`,ticker:arr(s.tickers).slice(0,4).join(', '),desc:s.rationale,state:'STRUCTURAL'})),...coverageRows('commodities')],queue:seq.flatMap(s=>arr(s.tickers).slice(0,1).map(t=>({ticker:t,score:100-s.tier*12,why:s.role,stage:`TIER ${s.tier}`})))};
}

function modelValidation(){
 const grades=obj(D.grades); const entries=Object.entries(grades).filter(([k,v])=>v&&typeof v==='object');
 if(!entries.length)return emptyModel('VALIDATION CENTER','No machine-readable metric grades were loaded.');
 const center=node('prod','PRODUCTION GATE','OOS / DSR / multiple testing','ENFORCED','watch','observed'); const nodes=entries.slice(0,18).map(([k,v],i)=>{const status=v.grade||v.status||v.verdict||'UNKNOWN';const angle=(i/Math.max(1,entries.length))*Math.PI*2;return node('v_'+i,k.replaceAll('_',' ').toUpperCase(),short(v.note||v.reason||'',35),status,status,'observed',{x:500+Math.cos(angle)*(175+(i%2)*60),y:310+Math.sin(angle)*(175+(i%2)*60),raw:v});});center.x=500;center.y=310;const g={nodes:[center,...nodes],edges:nodes.map(n=>edge(n.id,'prod',n.state,'inferred'))};
 return {title:'VALIDATION CENTER',sub:'A component enters production only after its frozen specification beats the baseline out of sample.',canvas:'EVIDENCE LABORATORY',badges:['observed','inferred'],graph:g,
 rail:basicRail('PRODUCTION GATE',`${entries.length} graded components loaded.`,`Validated components may inform decisions within their tested scope.`,`Monitor degradation, drift, calibration and prospective lockbox outcomes.`,`Good in-sample results are not production evidence.`,`Reject or downgrade on OOS failure, drift or broken data lineage.`,'Continuous monitoring',65,'OPEN GRADE CARD'),ledger:[...entries.slice(0,20).map(([k,v])=>({time:obj(D.meta).generated,ticker:k,desc:v.note||v.reason||JSON.stringify(v),state:v.grade||v.status||'UNKNOWN'})),...arr(FLD.statuses).slice(0,30).map(x=>({time:x.fetched_at,ticker:x.provider,desc:`${x.dataset} · ${x.note}`,state:x.state,raw:x}))],queue:entries.slice(0,8).map(([k,v])=>({ticker:k,score:/VALID/i.test(v.grade||v.status||'')?90:/PARTIAL/i.test(v.grade||v.status||'')?55:15,why:v.note||v.reason||'',stage:v.grade||v.status||'UNKNOWN'}))};
}

function emptyModel(title,message){const g=layered([[node('empty',title,message,'NO_DATA','NO_DATA')]]);return {title,sub:message,canvas:title,badges:['observed'],graph:g,rail:basicRail('NO DATA',message,'No action.','Connect or repair the required source.','Do not substitute a static narrative or synthetic series.','Data availability is the current invalidation.','Until source recovers',0,'NO ACTION'),ledger:[],queue:[]};}
function getModel(){switch(state.view){case'mc':return modelMission();case'macro':return modelMacro();case'ew':return modelEarly();case'alpha':return modelAlpha();case'inst':return modelInstitutional();case'deriv':return modelDerivatives();case'us':return modelMarket('us','US STOCKS');case'ihsg':return modelMarket('idx','IHSG');case'crypto':return modelMarket('crypto','CRYPTO');case'commod':return modelMarket('commodity','COMMODITIES');case'fx':return modelMarket('fx','FX');case'flow':return modelFlow();case'sc':return modelSupply();case'co':return modelCompany();case'kg':return modelKnowledge();case'rc':return modelValidation();default:return modelMission();}}

function graphSvg(model){
 const g=model.graph||{nodes:[],edges:[]}; const visibleNodes=g.nodes.filter(n=>state.mode==='all'||n.evidence!=='structural'||['sc','kg'].includes(state.view)); const ids=new Set(visibleNodes.map(n=>n.id)); const edges=arr(g.edges).filter(e=>ids.has(e.from)&&ids.has(e.to)); const map=Object.fromEntries(visibleNodes.map(n=>[n.id,n]));
 if(!visibleNodes.length)return `<div class="empty"><div><div class="code">NO OBSERVED NODES</div><p>Switch to <b>ALL LAYERS</b> to inspect structural maps, or connect the required live feed.</p></div></div>`;
 const defs=`<defs>
  <marker id="arrow-neutral" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#365274"/></marker>
  <marker id="arrow-constructive" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#36f28b"/></marker>
  <marker id="arrow-destructive" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#ff4fa3"/></marker>
  <marker id="arrow-watch" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#ffd166"/></marker>
  <marker id="arrow-structural" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#a97aff"/></marker>
  <filter id="glow"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>`;
 const edgeHtml=edges.map((e,i)=>{const a=map[e.from],b=map[e.to];if(!a||!b)return'';const dy=b.y-a.y;const c1y=a.y+dy*.42,c2y=a.y+dy*.58;const path=`M ${a.x} ${a.y+26} C ${a.x} ${c1y}, ${b.x} ${c2y}, ${b.x} ${b.y-26}`;const klass=`edge ${e.state||''} ${e.evidence||''} ${e.active?'active':''}`;const marker=e.evidence==='structural'?'structural':['constructive','destructive','watch'].includes(e.state)?e.state:'neutral';const lx=(a.x+b.x)/2,ly=(a.y+b.y)/2;const tip=`${a.label} → ${b.label} · ${e.relation||e.evidence||'relation'}${e.label?' · '+e.label:''}`;return `<g class="edge-group"><title>${esc(tip)}</title><path class="${klass}" d="${path}" stroke-width="${e.width||1.7}" marker-end="url(#arrow-${marker})"/>${e.label?`<text class="edge-label" x="${lx}" y="${ly-4}" text-anchor="middle">${esc(e.label)}</text>`:''}</g>`;}).join('');
 const nodeHtml=visibleNodes.map(n=>{const w=168,h=54,x=n.x-w/2,y=n.y-h/2;const selected=state.selected===n.id?'selected':'';const ev=n.evidence||'observed';return `<g class="node ${n.state||''} ${ev} ${selected}" data-node="${esc(n.id)}" transform="translate(${x},${y})"><rect class="node-box" width="${w}" height="${h}" rx="4"/><text class="node-title" x="10" y="17">${esc(short(n.label,24))}</text><text class="node-sub" x="10" y="33">${esc(short(n.sub,30))}</text><text class="node-value" x="158" y="17" text-anchor="end">${esc(short(n.value,18))}</text><rect class="node-badge" x="116" y="39" width="42" height="10" rx="5"/><text class="node-badge-text" x="137" y="47" text-anchor="middle">${esc(ev.toUpperCase().slice(0,6))}</text></g>`;}).join('');
 return `<svg viewBox="0 0 1000 620" preserveAspectRatio="xMidYMid meet">${defs}${edgeHtml}${nodeHtml}</svg>`;
}

function renderRail(r){
 const conf=Math.max(0,Math.min(100,num(r.confidence)||0));const confLabel=r.confidenceLabel||'CONFIDENCE';return `<div class="location"><div class="eyebrow">YOU ARE HERE</div><div class="main">${esc(r.title||'NO DATA')}</div><div class="desc">${esc(r.desc||'')}</div></div>${[['CURRENT',r.current,''],['NEXT',r.next,'green'],['ALTERNATIVE',r.alternative,'amber'],['INVALIDATION',r.invalidation,'mag'],['TIME WINDOW',r.window,''],['ACTION',r.action,'green']].map(([k,v,c])=>`<div class="decision-row"><div class="decision-label">${k}</div><div class="decision-value ${c}">${esc(v||'—')}</div>${k==='ACTION'?`<div class="confidence"><i style="width:${conf}%"></i></div><div class="decision-label" style="margin-top:4px">${esc(confLabel)} ${conf}%</div>`:''}</div>`).join('')}`;
}
function renderLedger(rows){
 const filtered=arr(rows).filter(r=>!state.search||JSON.stringify(r).toLowerCase().includes(state.search.toLowerCase())); if(!filtered.length)return `<div class="empty"><div><div class="code">NO EVIDENCE ROWS</div><p>The system will not fill this panel with mock values.</p></div></div>`;
 return `<div class="ledger">${filtered.slice(0,40).map(r=>`<div class="ledger-row"><div class="ledger-time">${esc(timeLabel(r.time))}</div><div class="ledger-ticker">${esc(short(r.ticker,18))}</div><div class="ledger-desc" title="${esc(r.desc)}">${esc(r.desc)}</div><div class="state-tag ${normalizeState(r.state)}">${esc(short(r.state,12))}</div></div>`).join('')}</div>`;
}
function renderQueue(rows){
 const filtered=arr(rows).filter(r=>!state.search||JSON.stringify(r).toLowerCase().includes(state.search.toLowerCase())); if(!filtered.length)return `<div class="empty"><div><div class="code">NO ACTION QUEUE</div><p>No candidate has enough evidence to occupy the queue.</p></div></div>`;
 return `<div class="queue">${filtered.slice(0,10).map((r,i)=>`<div class="queue-item" data-queue="${esc(r.ticker)}"><div class="queue-rank">${String(i+1).padStart(2,'0')}</div><div class="queue-main"><b>${esc(r.ticker)}</b><div>${esc(short(r.stage||r.why,42))}</div></div><div class="queue-score">${Math.round(num(r.score)||0)}</div></div>`).join('')}</div>`;
}
function renderTape(){
 const events=[...arr(obj(D.institutional).events),...arr(LI.events)].sort((a,b)=>String(b.timestamp||'').localeCompare(String(a.timestamp||''))); const base=events.length?events.slice(0,35):arr(obj(D.data_health).sources).map(x=>({timestamp:obj(D.meta).generated,event_type:x.dataset,ticker:x.provider,description:x.note,state:x.state}));
 const html=base.map(e=>`<span class="tape-item"><span>${esc(timeLabel(e.timestamp).slice(11,19))}</span> <span class="type">${esc(e.event_type||e.dataset||'FEED')}</span> <b>${esc(e.ticker||e.provider||'—')}</b> <span>${esc(short(e.description||eventDescription(e),68))}</span>${e.premium?` <span class="money">${money(e.premium)}</span>`:''}</span>`).join('');setHTML('tape',(html||'<span class="tape-item">NO LIVE EVENTS — DATA GATE ACTIVE</span>')+(html||''));
}
function badgeHtml(b){return `<span class="evidence-pill ${b}">${b.toUpperCase()}</span>`;}
function openDetail(raw,title){document.getElementById('drawerTitle').textContent=title||'DETAIL';const entries=Object.entries(obj(raw)).filter(([k,v])=>typeof v!=='object'||v===null).slice(0,16);document.getElementById('drawerBody').innerHTML=`<div class="detail-grid">${entries.map(([k,v])=>`<div class="detail-cell"><div class="k">${esc(k)}</div><div class="v">${esc(fmt(v))}</div></div>`).join('')}</div><div class="raw">${esc(JSON.stringify(raw,null,2))}</div>`;document.getElementById('drawerBackdrop').classList.add('open');}

function render(){
 renderSidebar();renderTop();const model=getModel();window.__MODEL=model;
 document.getElementById('viewTitle').textContent=model.title;document.getElementById('viewSub').textContent=model.sub;document.getElementById('canvasTitle').textContent=model.canvas;document.getElementById('canvasMeta').textContent=`${arr(model.graph?.nodes).length} nodes · ${arr(model.graph?.edges).length} edges`;
 setHTML('canvasBadges',arr(model.badges).map(badgeHtml).join(''));setHTML('graph',graphSvg(model));setHTML('rail',renderRail(model.rail));setHTML('ledger',renderLedger(model.ledger));setHTML('queue',renderQueue(model.queue));document.getElementById('ledgerMeta').textContent=`${arr(model.ledger).length} records`;document.getElementById('queueMeta').textContent=`${arr(model.queue).length} ranked`;renderTape();
 document.querySelectorAll('.seg').forEach(b=>b.classList.toggle('active',b.dataset.mode===state.mode));
 document.querySelectorAll('.node').forEach(el=>el.onclick=()=>{const id=el.dataset.node;state.selected=id;const n=arr(model.graph.nodes).find(x=>x.id===id);const tk=n?.raw?.ticker||n?.raw?.tk||n?.raw?.asset||n?.label;if(tk&&/^[A-Z0-9.=_-]{1,20}$/i.test(String(tk)))state.selectedTicker=String(tk);persistState();render();if(n?.raw)openDetail(n.raw,n.label);});
 document.querySelectorAll('.queue-item').forEach(el=>el.onclick=()=>{state.selectedTicker=el.dataset.queue;persistState();openDetail(arr(model.queue).find(x=>x.ticker===el.dataset.queue)||{},el.dataset.queue);});
}

function acceptSnapshot(next){
 if(!next||typeof next!=='object')return false;
 const rt=obj(next.runtime), revision=Number(rt.snapshot_sequence||0), hash=String(rt.content_hash||'');
 if((hash&&hash===lastContentHash)||(!hash&&revision===lastRevision))return false;
 D=next;LI=obj(D.live_intelligence);FLD=obj(D.full_live_data);sourceState=obj(D.data_health).overall||obj(D.meta).source||'NO_DATA';lastRevision=revision;lastContentHash=hash;lastPollOkAt=Date.now();
 requestAnimationFrame(render);return true;
}
async function fetchJsonBounded(url,timeoutMs=3500){
 const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),timeoutMs);
 try{const response=await fetch(`${url}?r=${Date.now()}`,{cache:'no-store',signal:controller.signal});if(!response.ok)throw new Error(`${url} ${response.status}`);return await response.json();}
 finally{clearTimeout(timer);}
}
async function pollSnapshot(){
 if(pollInFlight)return;pollInFlight=true;
 try{
  const next=await fetchJsonBounded(DATA_URL);lastPollOkAt=Date.now();acceptSnapshot(next);
  try{const status=await fetchJsonBounded(STATUS_URL,2500);const sync=document.getElementById('dataSync');if(sync){const st=String(status.state||'UNKNOWN');sync.dataset.worker='1';const html=`SYNC <b>${esc(st)} · R${lastRevision}</b>`;if(sync.innerHTML!==html)sync.innerHTML=html;}}catch(_){ }
 }catch(err){const sync=document.getElementById('dataSync');if(sync){const html=`SYNC <b>RETRYING · R${lastRevision}</b>`;if(sync.innerHTML!==html)sync.innerHTML=html;}}
 finally{pollInFlight=false;}
}

document.querySelectorAll('.seg').forEach(b=>b.onclick=()=>{state.mode=b.dataset.mode;persistState();render();});
document.getElementById('search').addEventListener('input',e=>{state.search=e.target.value;const model=getModel();setHTML('ledger',renderLedger(model.ledger));setHTML('queue',renderQueue(model.queue));});
document.getElementById('drawerClose').onclick=()=>document.getElementById('drawerBackdrop').classList.remove('open');document.getElementById('drawerBackdrop').onclick=e=>{if(e.target.id==='drawerBackdrop')e.currentTarget.classList.remove('open');};
render();
pollSnapshot();
setInterval(pollSnapshot,POLL_MS);
})();
