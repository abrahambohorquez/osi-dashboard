# OSI Dashboard, The Overfitters (advanced visual direction)

This is a second, parallel version of the dashboard in `../dash`, not a
replacement for it. Same data logic, same pages, same statistics; the
difference is the publication language. `theme.py`, `components.py` and
`Inicio.py` are built to read like a US weather-agency product page
rather than like a dashboard. See "Design language" below for what was
taken from where, and what deliberately was not.

Interactive dashboard to explore the Outage Severity Index problem: how
weather and outage severity behave across a storm, with an orbiting 3D
storm map, distributions, multicollinearity, Frisch-Waugh-Lovell,
hysteresis and Moran's I, all computed live on whatever file is loaded.

## Why the default data is simulated

The challenge doesn't allow showing or distributing the official dataset
outside the registered team. To demo the dashboard without touching that
restriction, `simular_datos.py` generates a toy storm (counties, names,
coordinates and values all invented) with the same column structure and
the same simplified physics as the real problem: two waves traveling
west to east, hysteresis between them, zero-inflation, and real (not
hand-drawn) spatial clustering. It doesn't use a single value from
`DM_Train.csv`.

When the team wants to see this with real data, anyone with authorized
access can upload their own file from the "Load data" page. The rest of
the pages update on their own. If the file doesn't have `hour_idx` (the
real `DM_Train.csv` doesn't, only `timestamp_et`), it's computed
automatically on load.

## How to run it

```
pip install -r requirements.txt
streamlit run Inicio.py
```

To regenerate the simulated data, for example with more counties per
state:

```
python simular_datos.py
```

## The 3D relief works on the real file too, without posicion_x/posicion_y

The real `DM_Train.csv` has no `posicion_x`/`posicion_y` (those are a
simulated-data invention), so Storm map's relief used to refuse to draw
anything for it. `viz._con_posiciones(df)`
now derives them automatically when they're missing but the file has
real `fipsCode`: it looks up each county's real centroid from the same
Census cache `geo_condados.py` already uses for the real county map,
and merges it in. If a file has neither real coordinates nor a real
`fipsCode` match, it still returns `None` and the page shows the same
warning as before, honestly, instead of drawing nothing silently.

## Structure

The code is split by responsibility, so each file can be read and
touched without carrying the rest of the app with it:

- `Inicio.py`: cover page.
- `theme.py`: color palette, typography, the Plotly chart theme, and the
  shared CSS.
- `schema.py`: required columns, upload validation, and the single entry
  point for loading the session's active data.
- `components.py`: reusable interface pieces (metric cards, page
  headers, the simulated-data banner, the "automatic finding" box), so
  spacing and symmetry stay consistent across the app.
- `estadistica.py`: the math behind each analysis page (moments, VIF,
  autocorrelation, Frisch-Waugh-Lovell, Moran's I).
- `viz.py`: the animated storm map (Gaussian interpolation between
  neighboring counties) in flat and orbiting-3D-relief form.
- `simular_datos.py`: generates `data/datos_simulados.csv`.
- `pages/`: each file is a sidebar page, in the order they're numbered.

Also present but not currently wired into any page (built during an
earlier direction, kept in case it's useful later): `geo_condados.py`
(downloads and caches real US Census county boundaries), `viz_folium.py`
(a Folium/Leaflet cinematic map mode), and `exportar_html.py` (exports
the storm map as a standalone HTML file). `viz.py` also still has
`figura_mapa_geografico` and `capa_pydeck_columnas` from that same
direction. None of these run in the live app right now; say the word if
you want them removed entirely instead of just unused.

## Pages

1. Load data
2. Storm map: the storm running hour by hour, as a continuously
   orbiting 3D relief, and a real US county map (Census TIGER/Line
   boundaries) above it: with the real challenge file it's the actual
   counties; with simulated data, each simulated county borrows a real
   county's shape (clearly labeled as a borrowed shape, not a claim
   about that real county). Both animate client-side (Plotly frames)
   and start playing on their own the moment the page loads, with rain
   falling on both (a canvas layered on top, not a Mapbox effect, no
   external account needed), each with its own play/pause built into
   the chart. Below the maps: automatic call-outs when it detects each
   wave's peak, a Moran's I finding on spatial clustering, and an hour
   slider to freeze on one exact moment and see the hardest-hit
   counties. Used to be split across this page and a separate
   "Cinematic view" page; merged into one once both pieces worked
   equally well, so there's a single best version instead of two
   near-duplicates.
3. Patterns: parallel coordinates, a hierarchically clustered heatmap
   with a real dendrogram, a Sankey of how severity escalates, and an
   animated bubble view (`viz_patterns.py`) that also runs on its own
   by default. A ridgeline of OSI's distribution shifting across the
   event lives here too and is reused on Distributions.
4. Time series
5. Distributions and zero-inflation
6. Correlations and multicollinearity (VIF)
7. Frisch-Waugh-Lovell
8. Hysteresis and memory
9. Costs (broken down by residential / commercial / industrial segment,
   sourced from LBNL-54365)
10. Models (empty on purpose, see below)
11. References: the team, the paper (`pages/11_References.py`), and the
    sources behind every method actually used in the dashboard.

## Auto-starting animations and the rain effect

`components.figura_autoreproducida(fig, altura, duracion_ms, en_bucle,
lluvia)` is what makes a Plotly animated figure start playing on its
own (see the section below for why this needs an iframe + a
`post_script`, not `st.plotly_chart`). `lluvia=True` additionally
attaches a small canvas to the same chart div with falling rain drops,
low opacity on purpose (an earlier attempt at a rain effect elsewhere in
this project used CSS at full chart-container opacity and completely
obscured the data underneath; this one is calibrated to be visible
without hiding anything). It's off by default, so existing calls
(Storm map) are unaffected unless a page opts in.

An access token from a mapping provider (Mapbox, etc.) was considered
for a richer rain/wind effect and was deliberately not used: it would
require every person running this dashboard to have their own account
and token, which the team decided against. Everything here runs with
no external account, same as the rest of the dashboard.

## Design language

Four reference sites were studied and mixed; none was cloned. What each
one contributed:

- **spc.noaa.gov**: the categorical scale. `theme.NIVELES` defines five
  numbered severity categories (`1 MNML` ... `5 EXTR`) with the SPC's own
  pastel fills and dark text, and `components.cinta_riesgo()` always
  renders the whole scale with the OSI threshold printed under each step
  and the one in effect raised. Showing the entire scale, not just the
  active category, is what makes it read as a product rather than as a
  coloured pill. `theme.nivel_para_osi()` is the only place that maps a
  number to a category, so the ribbon, the badges and the map legend
  cannot disagree.
- **nhc.noaa.gov**: the advisory format. `components.titular()` renders
  the all-capitals headline wrapped in ellipses
  (`...PEAK OUTAGE SEVERITY 0.412 AT HOUR 84...`), which is the
  signature of an NWS text product; `components.tarjeta_datos()` is the
  vitals block, with product name and number in a solid header, dotted
  leader lines between label and value, and an issuance footer; and
  `components.lista_estado()` is the bulleted "what is in effect right
  now" list from the NHC front page, used instead of a paragraph.
- **weather.gov**: the site structure. A three-band header (utility
  strip, unit masthead with issuance stamp, grouped section index), a
  breadcrumb trail on every page, and the section index repeated in the
  left rail. The eleven pages are grouped into five named sections in
  `components.PAGINAS` instead of sitting flat in one row of tabs.
- **iii.org**: the spacing and the tone. One bounded reading column, a
  standfirst paragraph that explains and attributes the figure *before*
  it is drawn (`components.entradilla()`), numbered figures with a source
  line underneath (`components.figura()`), and a "related products" block
  at the foot of each page.

No agency seal, logo, wordmark or `.gov` domain convention is
reproduced. The utility strip says "student project, not an operational
forecast" on every page and the footer repeats it at length; a test
asserts both, because the disclaimer is what makes the pastiche honest.

### Three weights of number, and one function for each

The single biggest reason the earlier passes read as generated was that
everything was presented as the same metric card, so there was nothing to
rank. The site now distinguishes:

| Weight | Function | Looks like |
| --- | --- | --- |
| Headline | `components.cifra_titular()` | one 62px figure per page, with a thick rule under it |
| Vitals | `components.fila_metricas()` | one bordered box with vertical dividers, monospaced, mid-size |
| Footnote | `components.nota_fuente()`, `pie_de_hoja()` | 10.5px monospaced under a hairline |

Monospace is used only for data, metadata and product identifiers, never
for prose. Every numeric display is `tabular-nums`.

### Rhythm

All vertical spacing derives from two CSS variables (`--bloque: 24px`,
`--apartado: 44px`) declared once in `theme._bloque_css`. Previously each
block carried its own invented margin, which is why the page almost
lined up without ever quite doing so.

## House constraints

Carried over from this project's history; a test pins most of them:

- No Mapbox or any service needing an API token or account. Everything
  runs offline after `pip install`.
- Real challenge data is never committed or persisted. The only CSV in
  the repo is the generated sample; uploads live in session state only.
- No government seal, logo, wordmark or `.gov` branding element. Layout,
  color and typography language only, with an explicit disclaimer.
- No em or en dashes in prose, and no emojis, in code or docs.

## Tests

```
pip install -r requirements.txt pytest
pytest tests/ -v
```

`tests/test_paginas.py` runs every page through
`streamlit.testing.v1.AppTest` twice: once on the simulated sample, and
once with a file injected into session state as if it had been uploaded.
It asserts no exception either way. On top of that it pins the things
that are easy to lose in a later edit: that every page carries the
three-band header, the breadcrumb, the metadata strip, the issuance stamp
and the institutional footer; that the severity scale covers the real
line with no gap or overlap; that the old `calm`/`watch`/`warning`/`severe`
vocabulary still resolves; that no agency logo or domain is embedded; and
that nothing requires a map token or ships challenge data in the repo.

## Autoplay instead of a play button (and no page drives a server-side rerun loop anymore)

Both Storm map's relief and Patterns's county-cloud bubble chart used to
drive their own animation with `st.session_state` + `st.rerun()`: each
render advanced the current hour, slept briefly, and called `st.rerun()`,
so the chart started playing on page load with no click needed. That
caused real, measurable problems: `st.rerun()` re-executes the *entire*
page, not just the section that changed, so on Storm map the real US
county map's own client-side animation got resent and reset on every
tick too (roughly 8 times a second), and on Patterns the parallel
coordinates, the hierarchical clustering (a real scipy linkage, not
cheap to recompute) and the Sankey below the bubble chart were all
rebuilt on every ~0.45s tick whether or not they had changed, which is
what made the page feel slow and made it hard to tell which chart was
actually the one animating. As long as anything on a page calls
`st.rerun()` in a loop, nothing else client-side on that page can stay
visually stable.

The fix, applied to both: drop the server-driven loop entirely and build
every frame into the figure itself. Storm map's relief uses
`figura_tormenta_3d`; Patterns's bubble chart uses
`figura_burbujas_animada` (`px.scatter(..., animation_frame="hour_idx")`,
the same approach Plotly's own Gapminder example uses). Both have their
own Plotly frames and play/pause, same as the county map, and neither
page calls `st.rerun()` at all anymore. The tradeoff is that charts on
the same page no longer share one clock or one Pause button, they each
run on their own timeline, since that's what having no server loop
requires. `figura_relieve_una_hora` (the single-frame, session-state-driven
version) is still in `viz.py`, unused, kept only as reference for how the
old approach worked.

That fixed the flicker, but Plotly still never starts an animation on
its own: `st.plotly_chart` draws the frames and waits for someone to
click play, and there's no figure property that means "start playing".
`components.figura_autoreproducida(fig, altura, duracion_ms, en_bucle)`
is what actually auto-starts the county map and the relief on Storm
map: it exports the figure with `fig.to_html(post_script=...)`, a
real Plotly.io feature that runs a JS snippet right after the plot
draws, and renders that HTML in an iframe via
`streamlit.components.v1.html`. The snippet calls `Plotly.animate`
after a short delay, and loops by rewinding to the first frame and
calling it again once the sequence finishes. It still honors the
chart's own play/pause button: it listens for `plotly_buttonclicked`
and stops re-triggering the loop if pause was the one clicked. Falls
back to a plain `st.plotly_chart` if the figure has no frames.

Two real tradeoffs from going through an iframe this way, both
deliberate: those two charts now load plotly.js from a CDN
(`include_plotlyjs="cdn"`) instead of Streamlit's own bundled copy, so
they need internet the first time (inlining it instead would add
~3.5 MB per chart with no browser caching); and they render at a fixed
height inside the iframe rather than themeing or resizing like a
normal `st.plotly_chart` does.

## About the "Models" page

It still has no results of its own because the team is working on
`v11_basic` and `V11-TailGuard`, and on the queue of pending
experiments. It's already built to receive a predictions CSV
(`fipsCode`, `hour_idx`, `predicted_osi`) and compute RMSE/MAE against
whatever is currently loaded. Nothing new needs to be written when the
final results are ready, just upload the file.
