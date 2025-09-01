"""
TLE 加载器

使用 skyfield 解析 TLE 文件，提供基础的卫星位置获取接口。
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
from skyfield.api import load, EarthSatellite
from skyfield.api import wgs84


@dataclass
class TLESatellite:
    sat: EarthSatellite
    name: str


class TLELoader:
    """从 TLE 文件加载卫星并提供位置查询接口。"""

    def __init__(self, tle_path: str) -> None:
        self.tle_path = str(Path(tle_path))
        self.ts = load.timescale()
        self.satellites: List[TLESatellite] = []

    def load(self) -> int:
        """加载 TLE 文件，返回卫星数量。"""
        with open(self.tle_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]

        sats: List[TLESatellite] = []
        i = 0
        while i + 2 < len(lines):
            # 兼容可选的名称行：若行不以 '1 ' 开头则视为名称
            if not lines[i].startswith('1 ') and not lines[i].startswith('2 '):
                name = lines[i]
                line1 = lines[i + 1]
                line2 = lines[i + 2]
                i += 3
            else:
                # 无名称，仅两行 TLE
                name = f"SAT_{len(sats)}"
                line1 = lines[i]
                line2 = lines[i + 1]
                i += 2

            try:
                sat = EarthSatellite(line1, line2, name, self.ts)
                sats.append(TLESatellite(sat=sat, name=name))
            except Exception:
                # 跳过异常条目
                continue

        self.satellites = sats
        return len(self.satellites)

    def positions_at_time(self, time_seconds: float) -> List[Dict[str, Any]]:
        """给定 UTC 秒（相对任意 epoch），返回各卫星的地理位置。

        注意：此处将 time_seconds 视为自 TLE epoch 起的相对秒数；
        若需要与系统仿真时钟严格对齐，应在调用侧统一转换。
        """
        if not self.satellites:
            return []

        # 以第一个卫星的 epoch 为参考，构造绝对时刻
        epoch = self.satellites[0].sat.epoch
        t = self.ts.tt_jd(epoch.tt + time_seconds / 86400.0)

        results: List[Dict[str, Any]] = []
        for idx, entry in enumerate(self.satellites):
            geocentric = entry.sat.at(t)
            subpoint = wgs84.subpoint(geocentric)
            lat = subpoint.latitude.degrees
            lon = subpoint.longitude.degrees
            alt_km = subpoint.elevation.km
            results.append({
                'id': idx,
                'name': entry.name,
                'lat': lat,
                'lon': lon,
                'alt': alt_km,
                'active': True
            })

        return results


