# Journey map asset

`journey-map-cartoon.png` is the bundled 16:9 illustrated adventure map used by
the 2026 Krasnodar-to-Chamonix journey. It was generated for this bot on
2026-08-10 from the original terrain composition and intentionally contains no
progress line, labels, markers, or live metrics. The brighter hand-painted atlas
style keeps the geography recognisable while making the group journey feel more
playful in Telegram.

`app/journey.py` resizes the background to 1200×675 and draws the route,
checkpoint state, current marker, and progress bar from database totals. The map
is illustrative and must not be used for navigation. A replacement should keep
the same crop, route corridor, and 16:9 aspect ratio unless the overlay
coordinates are updated at the same time.
