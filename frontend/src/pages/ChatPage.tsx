import React, { useState } from "react";
import ChatWindow from "../components/ChatWindow";
import InputBox from "../components/InputBox";
import ExamplePrompts from "../components/ExamplePrompts";
import { useChatStorage } from "../hooks/useChatStorage";
import { mockChatAPI } from "../mock/mockResponse";
import type { Message } from "../types";

const ChatPage: React.FC = () => {

  

  const { messages, addMessage, clearMessages } = useChatStorage();
  const [message, setMessage] = useState("");
  // 처음엔 hero 화면, 대화가 한번이라도 시작되면 false
  const [started, setStarted] = useState(messages.length > 0);

  const handlePromptClick = (prompt: string) => {
  // 프롬프트 클릭 시 입력창에만 넣고 화면 전환은 하지 않음
  setMessage(prompt);
};


const handleSend = async (userMessage: string) => {
  if (!started) setStarted(true);

  const userMsg: Message = { role: "user", content: userMessage, type: "text" };
  addMessage(userMsg);

  // 여기를 수정! ↓
  // const res = await mockChatAPI(userMessage);  ← 이 줄을 아래로 교체
  const res = await fetch('http://localhost:3001/chat/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: userMessage })
  });
  const data = await res.json();
  
  addMessage(data);  // res → data로 변경
};

window.addEventListener("beforeunload", () => {
  localStorage.removeItem("chatMessages");
});
  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10">

  <div className="w-full max-w-4xl">
    {/* ① Hero 화면 */}
    <div
      className={`transition-all duration-500 ease-in-out ${
        started
          ? "opacity-0 -translate-y-3 pointer-events-none h-0 overflow-hidden"
          : "opacity-100 translate-y-0"
      }`}
    >
      <div className="text-center mb-8">
        <div className="flex justify-center items-center mb-3" >
<img src="/logo_copy.webp" alt="" className="w-36 md:w-48 lg:w-72 h-auto block "/>
        
        </div>
        <p className="text-4xl md:text-5xl font-semibold text-[#3a3a35] mb-3 tracking-tight">
          아이와 주말 나들이 어때요?
        </p>
        <p className="text-sm text-[#9a9081]">
          지역·날씨·아이 연령에 맞는 장소를 챗봇이 추천해드릴게요.
        </p>
      </div>

      <div className="w-full">
        <InputBox
          variant="hero"
          message={message}
          setMessage={setMessage}
          onSend={handleSend}
        />
      </div>

      <div className="mt-6 flex justify-center">
        <ExamplePrompts onPromptClick={handlePromptClick} />
      </div>
    </div>

    {/* ② Chat 화면 */}
    <div
      className={`transition-all duration-500 ease-in-out ${
        started
          ? "opacity-100 translate-y-0"
          : "opacity-0 translate-y-3 pointer-events-none h-0 overflow-hidden"
      }`}
    >
      {started && (
        <>
          <div className="mb-4 min-w-0">
            <ChatWindow messages={messages} onPromptClick={handlePromptClick} />
          </div>

          <InputBox
            variant="chat"
            message={message}
            setMessage={setMessage}
            onSend={handleSend}
          />
          <button
            onClick={clearMessages}
            className="text-xs text-gray-400 mt-2 hover:underline block mx-auto"
          >
            대화 초기화
          </button>
        </>
      )}
    </div>
  </div>
</div>

  );
};

export default ChatPage;
