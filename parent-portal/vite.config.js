import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// 项目根目录（.env 统一配置文件所在处）：parent-portal/ 的上两级
const projectRoot = fileURLToPath(new URL('../..', import.meta.url))

export default defineConfig(({ mode }) => {
  // 读取根目录 .env；空前缀 '' = 加载全部变量（不限 VITE_ 前缀）
  // 后端地址与主前端共用 BACKEND_PORT，代理走本机 127.0.0.1
  const env = loadEnv(mode, projectRoot, '')

  const backendPort = env.BACKEND_PORT || '8001'
  const parentHost = env.PARENT_HOST || '0.0.0.0'
  const parentPort = Number(env.PARENT_PORT) || 5174

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      host: parentHost,
      port: parentPort,
      // 公网隧道（cpolar）域名白名单：免费版每次重启随机分配子域名，
      // 放行 cpolar 常见域名后缀；IP 直连（局域网）不受影响
      allowedHosts: ['.cpolar.top', '.cpolar.cn', '.cpolar.io'],
      proxy: {
        '/api': {
          // 本机转发到后端（与班主任端共用同一后端），换局域网 IP 无需修改
          target: `http://127.0.0.1:${backendPort}`,
          changeOrigin: true,
          // 透传真实客户端 IP（X-Forwarded-For），后端家长端限流依赖此头
          xfwd: true
        }
      }
    }
  }
})
