# Journey map asset

`journey-map-base.png` is the bundled 16:9 topographic illustration used by the
2026 Krasnodar-to-Chamonix journey. It was generated for this bot on 2026-08-10
and intentionally contains no progress line or live metrics.

`app/journey.py` resizes the background to 1200×675 and draws the route,
checkpoint state, current marker, and progress bar from database totals. The map
is illustrative and must not be used for navigation. A replacement should keep
the same crop, label positions, and 16:9 aspect ratio unless the overlay
coordinates are updated at the same time.
