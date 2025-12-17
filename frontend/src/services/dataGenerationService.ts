import api from './api'

export interface DocumentReference {
  type: 'document' | 'datasource' | 'custom'
  id: number
  name: string
}

export interface GenerateDataRequest {
  user_query: string
  model_config_id?: number
  format?: string
  references?: DocumentReference[]
}

export interface GenerateDataResponse {
  success: boolean
  data: {
    generated_data: string
    format: string
    usage: {
      input_tokens: number
      output_tokens: number
    }
    history_id?: number
  }
  message: string
}

export const dataGenerationService = {
  generateData: async (request: GenerateDataRequest): Promise<GenerateDataResponse> => {
    const response = await api.post('/data-generation/generate', request)
    return response.data
  },
  
  getHistoryList: async (skip: number = 0, limit: number = 100) => {
    const response = await api.get('/history', { params: { skip, limit } })
    return response.data
  },
  
  getHistoryDetail: async (id: number) => {
    const response = await api.get(`/history/${id}`)
    return response.data
  },
  
  deleteHistory: async (id: number) => {
    const response = await api.delete(`/history/${id}`)
    return response.data
  },
  
  regenerateHistory: async (id: number) => {
    const response = await api.post(`/history/${id}/regenerate`)
    return response.data
  },
}
