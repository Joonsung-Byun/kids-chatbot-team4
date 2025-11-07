import { useState, useEffect } from "react";
import type { Message } from "../types";

export function useChatStorage() {
  const [messages, setMessages] = useState<Message[]>(() => {
    const saved = localStorage.getItem("chatMessages");
    return saved ? JSON.parse(saved) : [];
  });

  useEffect(() => {
    localStorage.setItem("chatMessages", JSON.stringify(messages));
  }, [messages]);

  const addMessage = (message: Message) => {
    setMessages((prev) => [...prev, message]);
  };

  const clearMessages = () => {
    setMessages([]);
    localStorage.removeItem("chatMessages");
  };

  return { messages, addMessage, clearMessages };
}
