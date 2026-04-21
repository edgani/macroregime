# PATCH for orchestration/build_snapshot.py
# Find the line: narrative_dict = {}
# AFTER that block, add:

        # ── Bottleneck Discovery Engine v2 ──
        try:
            from engines.bottleneck_discovery_engine import BottleneckDiscoveryEngine
            bde = BottleneckDiscoveryEngine(raw.get('prices', {}), narrative_signals)
            bottleneck_output = bde.run(current_quad=quad.get("structural_quad", "Q?"))
            bottleneck_dict = {
                "active_bottlenecks": bottleneck_output.active_bottlenecks,
                "ticker_implications": bottleneck_output.ticker_implications,
                "cross_market_chains": bottleneck_output.cross_market_chains,
                "front_run_basket": bottleneck_output.front_run_basket,
                "summary": bottleneck_output.summary,
            }
        except Exception:
            bottleneck_dict = {}

# Then in the returned snapshot dict, add key:
# "bottleneck_discovery": bottleneck_dict,
