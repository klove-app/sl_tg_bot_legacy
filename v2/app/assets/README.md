# Journey map asset

`journey-map-cartoon.png` is the bundled 16:9 illustrated adventure map used by
the 2026 Krasnodar-to-Chamonix journey. It was generated for this bot on
2026-08-10 from the original terrain composition and intentionally contains no
progress line, labels, markers, or live metrics. The brighter hand-painted atlas
style keeps the geography recognisable while making the group journey feel more
playful in Telegram.

`app/journey.py` resizes the background to 1200×675 and draws the route,
checkpoint state, current marker, finish flag, level, next quest, and team XP
bar from database totals. Reached checkpoints become stars and the next dense
waypoint gets a mint highlight, so the generated image reads like a lightweight
game board without adding database state.

`journey-waypoints-2026.json` contains 201 deterministic route marks at 12.5 km
intervals. Their nearby populated-place names come from the GeoNames `cities500`
and country alternate-name exports under CC BY 4.0; Russian names are preferred
with the local name as fallback. Generation is reproducible with
`scripts/generate_journey_waypoints.py`. GeoNames data is bundled at build time,
so production performs no live geocoding.

The map and route are illustrative and must not be used for navigation. A
replacement should keep the same crop, route corridor, and 16:9 aspect ratio
unless the overlay coordinates are updated at the same time.
