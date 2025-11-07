import React from "react";
import type { Message } from "../types";
import MessageBubble from "./MessageBubble";
import KakaoMapView from "./KakaoMapView";

interface Props {
  messages: Message[];
}

const ChatWindow: React.FC<Props> = ({ messages }) => {
  return (
    <div className="flex flex-col gap-3 w-full h-[75vh] overflow-y-auto p-6 bg-white/70 rounded-2xl shadow-lg border border-green-100 backdrop-blur-sm">
      {messages.length === 0 ? (
        <p className="text-gray-400 text-center mt-20">
          👋 아이와 함께할 활동을 물어보세요! 예: “서울 한남동 놀이터 추천해줘”
        </p>
      ) : (
        messages.map((msg, i) => (
          <div key={i}>
            {msg.type === "map" ? (
              <>
                <MessageBubble role={msg.role} content={msg.content} />
                {msg.data && <KakaoMapView data={msg.data} />}
              </>
            ) : (
              <MessageBubble role={msg.role} content={msg.content} />
            )}
          </div>
        ))
      )}
    </div>
  );
};

export default ChatWindow;
