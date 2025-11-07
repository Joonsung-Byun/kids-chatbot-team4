import React from "react";
import type { MessageRole } from "../types";

interface Props {
  role: MessageRole;
  content: string;
}

const MessageBubble: React.FC<Props> = ({ role, content }) => {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] p-3 rounded-2xl text-sm leading-relaxed shadow-sm ${
          isUser
            ? "bg-green-200 text-gray-800 rounded-br-none"
            : "bg-gray-100 text-gray-700 border border-gray-200 rounded-bl-none"
        }`}
      >
        {content}
      </div>
    </div>
  );
};

export default MessageBubble;
