import React, { useState } from "react";
import ChatWindow from "../components/ChatWindow";
import InputBox from "../components/InputBox";
import { useChatStorage } from "../hooks/useChatStorage";
import { mockChatAPI } from "../mock/mockResponse";
import type { Message } from "../types";

const ChatPage: React.FC = () => {
  const { messages, addMessage, clearMessages } = useChatStorage();
  const [message, setMessage] = useState("");

  const handleSend = async (userMessage: string) => {
    const userMsg: Message = { role: "user", content: userMessage, type: "text" };
    addMessage(userMsg);

    const res = await mockChatAPI(userMessage);
    addMessage(res);
  };

  return (
    <div className="flex flex-col w-full max-w-3xl mx-auto py-10 px-6 lg:px-8">
      <h1 className="text-3xl font-semibold text-green-600 mb-6 text-center tracking-tight">
        🌿 Kids Activity Chatbot
      </h1>

      {/* ChatWindow 안으로 예시 프롬프트 포함 */}
      <ChatWindow messages={messages} onPromptClick={setMessage} />

      <div className="mt-4">
        <InputBox message={message} setMessage={setMessage} onSend={handleSend} />
        <button
          onClick={clearMessages}
          className="text-s cursor-pointer text-gray-400 mt-2 self-center hover:underline block mx-auto"
        >
          대화 초기화
        </button>
      </div>
    </div>
  );
};

export default ChatPage;
