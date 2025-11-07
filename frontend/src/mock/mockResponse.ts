import type { Message } from "../types";

export function mockChatAPI(userMessage: string): Promise<Message> {
  return new Promise((resolve) => {
    setTimeout(() => {
      if (userMessage.includes("한남동")) {
        resolve({
          role: "ai",
          type: "map",
          content: "한남동 근처 아이와 가기 좋은 공원이에요 🌳",
          data: {
            center: { lat: 37.533, lng: 127.002 },
            markers: [
              { name: "한남어린이공원", lat: 37.5341, lng: 127.0013, desc: "그늘 많음" },
              { name: "보광어린이공원", lat: 37.5298, lng: 127.0025, desc: "놀이터 완비" }
            ]
          }
        });
      } else {
        resolve({
          role: "ai",
          type: "text",
          content: `“${userMessage}” 에 대한 정보를 준비 중이에요 💬`
        });
      }
    }, 500);
  });
}
