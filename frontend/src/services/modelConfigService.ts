import api from './api'

export interface ModelConfig {
  id: number
  config_name: string
  model_type: string
  model_version: string
  api_base?: string
  temperature?: number
  max_tokens?: number
  timeout: number
  is_enabled: boolean
  is_default: boolean
  created_at?: string
  updated_at?: string
}

export interface ModelConfigCreate {
  config_name: string
  model_type: string
  model_version: string
  api_key: string
  api_base?: string
  temperature?: number
  max_tokens?: number
  timeout?: number
  is_enabled?: boolean
  is_default?: boolean
}

export interface ModelConfigUpdate {
  config_name?: string
  model_type?: string
  model_version?: string
  api_key?: string
  api_base?: string
  temperature?: number
  max_tokens?: number
  timeout?: number
  is_enabled?: boolean
  is_default?: boolean
}

export const modelConfigService = {
  getAll: async (include_sensitive: boolean = false, skip: number = 0, limit: number = 100) => {
    const response = await api.get('/model-config', {
      params: { include_sensitive, skip, limit }
    })
    return response.data
  },
  
  getById: async (id: number, include_sensitive: boolean = false) => {
    const response = await api.get(`/model-config/${id}`, {
      params: { include_sensitive }
    })
    return response.data
  },
  
  getDefault: async (include_sensitive: boolean = false) => {
    const response = await api.get('/model-config/default/config', {
      params: { include_sensitive }
    })
    return response.data
  },
  
  create: async (data: ModelConfigCreate) => {
    const response = await api.post('/model-config', data)
    return response.data
  },
  
  update: async (id: number, data: ModelConfigUpdate) => {
    const response = await api.put(`/model-config/${id}`, data)
    return response.data
  },
  
  delete: async (id: number) => {
    const response = await api.delete(`/model-config/${id}`)
    return response.data
  },
  
  setDefault: async (id: number) => {
    const response = await api.put(`/model-config/${id}/set-default`)
    return response.data
  },
}
