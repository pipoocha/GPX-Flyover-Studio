from __future__ import annotations

import html
import json
import os
import sys
import webbrowser
from pathlib import Path

from studio.config.loader import ProjectLoaderV5
from studio.io.gpx_loader import GPXLoader

CESIUM_JS_VERSION = "1.143"
TOKEN_FILE = Path("config/cesium_ion_token.txt")


def load_token() -> str:
    token = os.environ.get("CESIUM_ION_TOKEN", "").strip()
    if token:
        return token
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text(encoding="utf-8").strip()
    return ""


def save_token(token: str) -> Path:
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(token.strip(), encoding="utf-8")
    return TOKEN_FILE


def _downsample(points: list[dict], maximum: int = 5000) -> list[dict]:
    if len(points) <= maximum:
        return points
    step = max(1, len(points) // maximum)
    sampled = points[::step]
    if sampled[-1] is not points[-1]:
        sampled.append(points[-1])
    return sampled


def _mode_from_project(project) -> str:
    background = str(getattr(project.terrain, "background", "cesium_bing")).lower()
    mapping = {
        "cesium_bing": "bing",
        "cesium_google2d": "google2d",
        "cesium_osm": "osm",
        "google_3d": "google3d",
    }
    return mapping.get(background, "bing")


def build_html(project_file: str | Path, *, token: str | None = None) -> Path:
    project = ProjectLoaderV5(project_file).load()
    points = _downsample(GPXLoader(project.gpx.file).load())
    if len(points) < 2:
        raise ValueError("Le GPX doit contenir au moins deux points.")

    token = (token or load_token()).strip()
    if not token:
        raise RuntimeError(
            "Clé Cesium ion absente. Dans Flyover Studio, clique sur « Clé Cesium ion… » "
            "puis colle le token de ton compte Cesium ion."
        )

    coords = [
        [float(p["lon"]), float(p["lat"]), float(p.get("ele") or 0.0)]
        for p in points
    ]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    center_lon = (min(lons) + max(lons)) / 2.0
    center_lat = (min(lats) + max(lats)) / 2.0
    span = max(max(lons) - min(lons), max(lats) - min(lats), 0.01)
    range_m = max(2500.0, min(120000.0, span * 111000.0 * 1.65))
    mode = _mode_from_project(project)

    output_dir = Path("output/cesium")
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "flyover_cesium_preview.html"

    # Token is intentionally client-side: CesiumJS uses browser-side ion tokens.
    token_js = json.dumps(token)
    coords_js = json.dumps(coords, separators=(",", ":"))
    title = html.escape(str(project.title or "Flyover Studio"))

    body = f'''<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{title} — Cesium</title>
  <script src="https://cesium.com/downloads/cesiumjs/releases/{CESIUM_JS_VERSION}/Build/Cesium/Cesium.js"></script>
  <link href="https://cesium.com/downloads/cesiumjs/releases/{CESIUM_JS_VERSION}/Build/Cesium/Widgets/widgets.css" rel="stylesheet" />
  <style>
    html,body,#cesiumContainer {{ width:100%; height:100%; margin:0; padding:0; overflow:hidden; background:#111; }}
    #panel {{ position:absolute; z-index:20; left:14px; top:14px; background:rgba(18,18,18,.82); color:white; padding:10px 12px; border-radius:8px; font-family:Segoe UI,Arial,sans-serif; font-size:13px; box-shadow:0 2px 12px rgba(0,0,0,.35); }}
    #panel select,#panel button {{ margin-left:6px; }}
    #status {{ margin-top:6px; color:#ddd; max-width:520px; }}
  </style>
</head>
<body>
<div id="cesiumContainer"></div>
<div id="panel">
  <strong>Flyover Studio V2.1.2 — Cesium</strong>
  <label>Fond
    <select id="mode">
      <option value="bing">Bing aérien + World Terrain</option>
      <option value="google2d">Google Satellite 2D + World Terrain</option>
      <option value="osm">OpenStreetMap + World Terrain</option>
      <option value="google3d">Google Photorealistic 3D</option>
    </select>
  </label>
  <button id="reload">Appliquer</button>
  <div id="status">Chargement du terrain…</div>
</div>
<script type="module">
const TOKEN = {token_js};
const TRACK = {coords_js};
const initialMode = {json.dumps(mode)};
Cesium.Ion.defaultAccessToken = TOKEN;

document.getElementById('mode').value = initialMode;
document.getElementById('reload').onclick = () => {{
  const m = document.getElementById('mode').value;
  const u = new URL(window.location.href);
  u.searchParams.set('mode', m);
  window.location.href = u.toString();
}};
const selectedMode = new URL(window.location.href).searchParams.get('mode') || initialMode;
document.getElementById('mode').value = selectedMode;

let viewer;
try {{
  if (selectedMode === 'google3d') {{
    viewer = new Cesium.Viewer('cesiumContainer', {{
      globe: false,
      baseLayerPicker: false,
      animation: false,
      timeline: false,
      geocoder: Cesium.IonGeocodeProviderType.GOOGLE,
      navigationHelpButton: false,
      sceneModePicker: false,
    }});
    const tileset = await Cesium.createGooglePhotorealistic3DTileset();
    viewer.scene.primitives.add(tileset);
  }} else {{
    let baseLayer;
    if (selectedMode === 'google2d') {{
      baseLayer = Cesium.ImageryLayer.fromProviderAsync(
        Cesium.IonImageryProvider.fromAssetId(3830183)
      );
    }} else if (selectedMode === 'osm') {{
      baseLayer = new Cesium.ImageryLayer(new Cesium.OpenStreetMapImageryProvider({{
        url: 'https://tile.openstreetmap.org/'
      }}));
    }}
    const options = {{
      terrain: Cesium.Terrain.fromWorldTerrain({{requestVertexNormals:true, requestWaterMask:true}}),
      baseLayerPicker: false,
      animation: false,
      timeline: false,
      navigationHelpButton: false,
      sceneModePicker: false,
      geocoder: false,
    }};
    if (baseLayer) options.baseLayer = baseLayer;
    viewer = new Cesium.Viewer('cesiumContainer', options);
  }}

  viewer.scene.globe && (viewer.scene.globe.depthTestAgainstTerrain = true);
  viewer.scene.fog.enabled = true;
  viewer.scene.fog.density = 0.00018;
  viewer.scene.skyAtmosphere && (viewer.scene.skyAtmosphere.show = true);
  viewer.scene.postProcessStages.fxaa.enabled = true;
  viewer.resolutionScale = Math.min(window.devicePixelRatio || 1, 2);

  const positions = TRACK.map(p => Cesium.Cartesian3.fromDegrees(p[0], p[1], Math.max(0, p[2]) + 12));
  const track = viewer.entities.add({{
    name: 'Trace GPX',
    polyline: {{
      positions,
      width: 7,
      material: new Cesium.PolylineGlowMaterialProperty({{
        glowPower: 0.22,
        taperPower: 0.8,
        color: Cesium.Color.fromCssColorString('#FC4C02')
      }}),
      clampToGround: true,
      arcType: Cesium.ArcType.GEODESIC,
    }}
  }});

  const start = TRACK[0];
  const finish = TRACK[TRACK.length-1];
  viewer.entities.add({{ position: Cesium.Cartesian3.fromDegrees(start[0], start[1], start[2] + 15), point: {{pixelSize:12,color:Cesium.Color.LIME,outlineColor:Cesium.Color.WHITE,outlineWidth:2,heightReference:Cesium.HeightReference.RELATIVE_TO_GROUND}} }});
  viewer.entities.add({{ position: Cesium.Cartesian3.fromDegrees(finish[0], finish[1], finish[2] + 15), point: {{pixelSize:12,color:Cesium.Color.RED,outlineColor:Cesium.Color.WHITE,outlineWidth:2,heightReference:Cesium.HeightReference.RELATIVE_TO_GROUND}} }});

  const center = Cesium.Cartesian3.fromDegrees({center_lon}, {center_lat}, 0);
  viewer.camera.lookAt(center, new Cesium.HeadingPitchRange(Cesium.Math.toRadians(330), Cesium.Math.toRadians(-28), {range_m}));
  viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);

  // A second, entity-based fit is delayed until terrain/tiles have begun streaming.
  setTimeout(() => {{
    viewer.zoomTo(track, new Cesium.HeadingPitchRange(Cesium.Math.toRadians(330), Cesium.Math.toRadians(-28), {range_m}));
  }}, 1800);

  document.getElementById('status').textContent = selectedMode === 'google3d'
    ? 'Google Photorealistic 3D actif. La couverture dépend de la zone.'
    : 'Cesium World Terrain actif. Tu peux tourner, incliner et zoomer librement.';
  window.flyoverReady = true;
}} catch (error) {{
  console.error(error);
  document.getElementById('status').textContent = 'Erreur Cesium : ' + error;
}}
</script>
</body>
</html>'''

    output.write_text(body, encoding="utf-8")
    return output.resolve()


def launch(project_file: str | Path, *, token: str | None = None) -> Path:
    output = build_html(project_file, token=token)
    webbrowser.open(output.as_uri())
    return output


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("Usage: python -m studio.cesium.preview <project.yaml>")
        return 2
    try:
        output = launch(argv[0])
        print(f"Preview Cesium créé : {output}")
        return 0
    except Exception as exc:
        print(f"Erreur Cesium : {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
