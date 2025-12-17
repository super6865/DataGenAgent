import api from './api'

export const eventLogService = {
  listTraces: async (params?: {
    service_name?: string
    start_time?: string
    end_time?: string
    skip?: number
    limit?: number
  }) => {
    const response = await api.get('/observability/traces', { params })
    return response.data
  },

  getTrace: async (traceId: string) => {
    const response = await api.get(`/observability/traces/${traceId}`)
    return response.data
  },

  listSpans: async (traceId: string) => {
    const response = await api.get(`/observability/traces/${traceId}/spans`)
    return response.data
  },

  getTraceDetail: async (traceId: string) => {
    const response = await api.get(`/observability/traces/${traceId}/detail`)
    return response.data
  },
}
