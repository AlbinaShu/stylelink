/// <reference types="vite/client" />

interface IRuntimeEnv {
  API_URL: string;
}

interface Window {
  __ENV__: IRuntimeEnv;
}