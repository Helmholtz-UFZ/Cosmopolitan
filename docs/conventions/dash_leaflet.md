# Dash Leaflet Conventions

Map gotchas that only appear in the deployed app. COSMONAUT's
`docs/conventions/dash_leaflet.md` has the same tile-layer section plus more
component gotchas.

## Tile Layers: Referer and CSP

Every external tile source has to pass two gates that exist only in the deployed
app. Neither shows up locally or in a suite (`test_e2e.py` mocks the tile layer),
and both fail as a broken map, not as an error.

- **Send a Referer to OpenStreetMap.** The cluster ingress (UFZ IT, not in
  `values.yaml`) answers every page with `Referrer-Policy: same-origin`, which strips
  the Referer from cross-origin requests. OSM's tile usage policy requires one; in
  2026-10 both apps showed "Access blocked – App is not following the tile usage
  policy" tiles instead of a map. Set the policy on the layer; Leaflet applies it to
  each tile image, overriding the page policy there:

  ```python
  dl.TileLayer(
      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      attribution="© OpenStreetMap contributors",
      referrerPolicy="strict-origin-when-cross-origin",
  )
  ```

  Origin only: OSM receives `https://<host>/`, never the page path, which carries
  job ids. A `dl.TileLayer()` without `url` defaults to OSM and needs it too.
  Guarded by `test/test_osm_tile_referrer.py`.

- **Allow the tile host in the CSP.** The ingress `Content-Security-Policy` in
  `deployments/ufz/{stage,prod}/values.yaml` lists every image host in `img-src`.
  A host missing there fails silently: the layer stays blank, and the only trace is
  a console message. Today the app needs `*.tile.openstreetmap.org` and the TiTiler
  under `*.app.ufz.de`, both listed. `*.tile.openstreetmap.org` does not match the
  bare `tile.openstreetmap.org`, so a layer that drops the `{s}` subdomains needs
  that host added. A `values.yaml` change needs a new tag, see
  [deployment](deployment.md).

To check either in a browser: the network tab shows whether a tile request carries
a `Referer`, and the console reports CSP blocks. Both reproduce locally with a
minimal Dash page that sets the two headers in an `after_request` hook.
