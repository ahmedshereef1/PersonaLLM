# LLM Twin — Frontend

A React + Vite chat interface for the LLM Twin project, featuring authentication, a dashboard, and a RAG-powered chat.

## Prerequisites

- [Node.js](https://nodejs.org/) v18+
- The backend API running on `http://localhost:8000`

## Setup & Run

```bash
# 1. Navigate to this folder
cd front_end/llm_twin

# 2. Install dependencies
npm install

# 3. Start the development server
npm run dev
```

The app will be available at **http://localhost:5173**

## Pages

| Route | Description |
|---|---|
| `/login` | Sign in to your account |
| `/register` | Create a new account |
| `/dashboard` | Overview and settings |
| `/chat` | RAG-powered chat with your LLM Twin |

## Other Commands

```bash
# Build for production
npm run build

# Preview the production build locally
npm run preview

# Run the linter
npm run lint
```

## How It Works

The dev server proxies all API calls to the backend:

- `/auth` → `http://localhost:8000/auth`
- `/dashboard` → `http://localhost:8000/dashboard`
- `/rag` → `http://localhost:8000/rag`
- `/chat` → `http://localhost:8000/chat`

Make sure the backend is running before starting the frontend.
