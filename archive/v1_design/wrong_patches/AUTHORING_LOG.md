# Wrong-patch authoring log (pre-generation)
All wrong patches written by the harness author (executor agent), before any test-generation run. Not by Gemini.
Replacements made before freezing:
- youssofal__mtplx-21 w2 (off-by-one in partial-marker tail): PASSED all 4 dev F2P → discarded (kept in discarded/), replaced by w4.
- youssofal__mtplx-21 w4 first draft broke 1 P2P (pure tool-call streamed in pieces) → narrowed to content mode only.
- raullenchai__rapid-mlx-289 w3 first draft was a corrupt hand-edited diff (apply failure) → regenerated from a real checkout.
- agronholm__anyio-1134 w2 first draft (exec as '__main__') broke 30/36 P2P (too obviously wrong) → replaced by the SourceFileLoader/no-__mp_main__ variant.
