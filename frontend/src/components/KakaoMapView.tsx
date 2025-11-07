import React, { useEffect } from "react";
import type { MapData } from "../types";

interface Props {
  data: MapData;
}

const KakaoMapView: React.FC<Props> = ({ data }) => {
  useEffect(() => {
    const script = document.createElement("script");
    script.src = "//dapi.kakao.com/v2/maps/sdk.js?appkey=발급받은_APP_KEY";
    script.onload = () => {
      const container = document.getElementById("map");
      if (!container) return;

      const options = {
        center: new kakao.maps.LatLng(data.center.lat, data.center.lng),
        level: 4,
      };
      const map = new kakao.maps.Map(container, options);

      data.markers.forEach((m) => {
        const marker = new kakao.maps.Marker({
          position: new kakao.maps.LatLng(m.lat, m.lng),
          map,
        });

        const iw = new kakao.maps.InfoWindow({
          content: `<div style="padding:5px;">${m.name}<br>${m.desc ?? ""}</div>`,
        });

        kakao.maps.event.addListener(marker, "click", () => iw.open(map, marker));
      });
    };
    document.head.appendChild(script);
  }, [data]);

  return (
    <div
      id="map"
      className="w-full h-64 rounded-xl border border-green-300 my-3 shadow-sm"
    />
  );
};

export default KakaoMapView;
