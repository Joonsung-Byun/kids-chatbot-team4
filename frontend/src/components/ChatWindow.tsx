import React from "react";
import type { Message } from "../types";
import MessageBubble from "./MessageBubble";
import KakaoMapView from "./KakaoMapView";
import ExamplePrompts from "./ExamplePrompts";

interface Props {
  messages: Message[];
  onPromptClick: (prompt: string) => void; // 👈 InputBox와 연결
}



const ChatWindow: React.FC<Props> = ({ messages, onPromptClick }) => {
  return (
    <div className="w-full max-w-full flex flex-col gap-3 h-[65vh] overflow-y-auto p-6 bg-white/70 rounded-2xl shadow-lg border border-green-100 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center px-4">
          <ExamplePrompts onPromptClick={onPromptClick} />
        </div>
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
