export type MessageRole = "user" | "ai";

export interface MapMarker {
  name: string;
  lat: number;
  lng: number;
  desc?: string;
}

export interface MapData {
  center: { lat: number; lng: number };
  markers: MapMarker[];
}

export interface Message {
  role: MessageRole;
  content: string;
  type?: "text" | "map";
  data?: MapData | null;
  link?: string;
}
