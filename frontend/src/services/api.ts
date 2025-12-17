import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    console.log('[API Request]', {
      method: config.method?.toUpperCase(),
      url: config.url,
      baseURL: config.baseURL,
      fullURL: `${config.baseURL}${config.url}`,
    })
    return config
  },
  (error) => {
    console.error('[API Request Error]', error)
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    if (error.response) {
      // 服务器返回了错误响应
      console.error('[API Error]', {
        status: error.response.status,
        statusText: error.response.statusText,
        url: error.config?.url,
        baseURL: error.config?.baseURL,
        fullURL: `${error.config?.baseURL}${error.config?.url}`,
        data: error.response.data,
        message: error.message,
      })
    } else if (error.request) {
      // 请求已发出但没有收到响应
      console.error('[API Error]', {
        message: 'No response received from server',
        url: error.config?.url,
        baseURL: error.config?.baseURL,
        fullURL: `${error.config?.baseURL}${error.config?.url}`,
        error: error.message,
      })
    } else {
      // 请求配置出错
      console.error('[API Error]', {
        message: 'Request setup error',
        error: error.message,
      })
    }
    return Promise.reject(error)
  }
)

export default api
