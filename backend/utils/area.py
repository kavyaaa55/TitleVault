# backend/utils/area.py

import math
from shapely.ops import transform

try:
    from pyproj import Transformer
    _transformer = Transformer.from_crs(
        "EPSG:4326",
        "EPSG:6933",  # Equal-area projection
        always_xy=True
    )
    def geodesic_area_m2(geom):
        projected = transform(_transformer.transform, geom)
        return abs(projected.area)
except Exception:
    def geodesic_area_m2(geom):
        if geom is None or geom.is_empty:
            return 0.0
        centroid = geom.centroid
        lat_rad = math.radians(centroid.y)
        r = 6378137.0
        kx = math.cos(lat_rad) * (math.pi / 180.0) * r
        ky = (math.pi / 180.0) * r

        def _proj(x, y, z=None):
            return (x * kx, y * ky)

        projected = transform(_proj, geom)
        return abs(projected.area)
