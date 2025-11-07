import React from "react";
import type { FormEvent } from "react";

interface Props {
  message: string;
  setMessage: (value: string) => void;
  onSend: (message: string) => void;
}

const InputBox: React.FC<Props> = ({ message, setMessage, onSend }) => {
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;
    onSend(message);
    setMessage("");
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex gap-3 bg-white border border-gray-200 rounded-xl p-3 shadow-sm"
    >
      <input
        type="text"
        placeholder="메시지를 입력하세요..."
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        className="flex-1 text-gray-700 px-3 py-2 focus:ring-2 focus:ring-green-400 focus:outline-none rounded-lg"
      />
      <button
        type="submit"
        className="bg-green-500 text-white font-medium px-5 rounded-lg hover:bg-green-600 transition"
      >
        보내기
      </button>
    </form>
  );
};

export default InputBox;
