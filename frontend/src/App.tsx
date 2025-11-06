import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="min-h-screen bg-white text-gray-900 flex flex-col items-center justify-center p-6">
      <div className="flex items-center gap-6 mb-8">
        <a href="https://vite.dev" target="_blank" rel="noreferrer">
          <img src={viteLogo} className="h-16 w-16" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank" rel="noreferrer">
          <img src={reactLogo} className="h-16 w-16" alt="React logo" />
        </a>
      </div>

      <h1 className="text-5xl font-bold tracking-tight">Vite + React + Tailwind</h1>

      <div className="mt-6 rounded-xl border border-gray-200 p-6 shadow-sm">
        <button
          className="rounded-lg bg-indigo-600 px-4 py-2 text-white shadow hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          onClick={() => setCount((count) => count + 1)}
        >
          count is {count}
        </button>
        <p className="mt-3 text-sm text-gray-600">
          Edit <code className="font-mono">src/App.tsx</code> and save to test HMR
        </p>
      </div>

      <p className="mt-6 text-xs text-gray-500">
        Click on the Vite and React logos to learn more
      </p>
    </div>
  )
}

export default App
