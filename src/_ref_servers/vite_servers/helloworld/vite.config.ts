import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    //https: {
    //  key: fs.readFileSync('./server.key'),
    //  cert: fs.readFileSync('./server.crt'),
    //},
    host: '0.0.0.0',
    port: 8080, // 기본값이 5173이므로 다른 포트를 사용할 수도 있음
    //cors: true,  // CORS 허용
  },
})
