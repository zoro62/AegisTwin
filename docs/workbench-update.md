# Workbench update

The interface now uses a light workspace with a compact dark sidebar, local SVG navigation icons, measured spacing, denser tables, muted status labels, keyboard focus indicators and responsive layouts. No external fonts, illustration downloads, decorative graphs or fabricated statistics are required.

Overview replaces the promotional hero with actual inventory counts, grouped segment assets, evidence requiring attention, scenario outcomes and recent queue activity. Cards and labels distinguish an unanalysed scenario from an incomplete search. Page navigation resets the scroll position. Raw scenario JSON remains available under advanced configuration.

## Added workflows

- **Asset register:** search by name/ID; filter by type, segment and critical designation; sort by name/type/segment; inspect actual related edges and evidence; copy an ID; export only the filtered rows as CSV. CSV output quotes values and prefixes potential spreadsheet formula strings. This is a tabular asset export, not the mixed-row inventory import format.
- **Evidence desk:** search IDs, sources and notes; filter collection methods or records needing attention; inspect freshness, confidence and rules linked through evidence/relationships. Corrections remain explicit, provenance-backed new snapshots through the existing workflow. No review or observation is invented.
- **Run comparison:** select/swap immutable saved analyses; compare critical targets by asset and capability; inspect snapshot, engine, removed relationships, runtime and search status. Changes in scenario/snapshot/configuration trigger a comparability warning. A truncated zero is displayed as unknown rather than certified unreachability. Bars count discovered reachability only and are not a risk score.
- **Report library:** search by scenario or run identifier, filter report types and download actual HTML/JSON exports with clear provenance.

Frontend code is split into shared contracts (`types.ts`), reusable workbench views (`workbench.tsx`) and the existing API-connected application (`main.tsx`). There are no new runtime dependencies or database migrations in this update.

## Verification

TypeScript/production build and stricter unused-code checks passed. The Python suite remains **15 passing tests**. **Two Chromium tests passed** against PostgreSQL: the full desktop workflow with limited-search comparison, inventory inspection/export, evidence desk and report download; and a 390-pixel mobile workflow that checks for horizontal page overflow.

Reviewed screenshots: `evaluation/ui-overview.png`, `evaluation/ui-comparison.png`, `evaluation/ui-defence.png`, `evaluation/ui-mobile.png`. Browser tests create isolated test workspaces. No Git push was performed; the user requested that it wait while these improvements were made.
