import api from './api'

export interface Document {
  id: number
  name: string
  file_path: string
  file_type: string
  file_size: number
  upload_time: string
  parse_status: 'pending' | 'parsing' | 'success' | 'failed'
  parse_result?: any
  document_type?: 'api' | 'requirement' | 'unknown'
  created_by?: number
  created_at?: string
  updated_at?: string
}

export interface DocumentListResponse {
  items: Document[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface DocumentUploadResponse {
  success: boolean
  data: Document
  message: string
}

export const documentService = {
  /**
   * Upload a document file
   */
  upload: async (file: File): Promise<DocumentUploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  /**
   * Get documents list with pagination and search
   */
  getList: async (
    page: number = 1,
    pageSize: number = 20,
    search?: string
  ): Promise<{ success: boolean; data: DocumentListResponse }> => {
    const params: any = {
      page,
      page_size: pageSize,
    }
    if (search) {
      params.search = search
    }
    
    const response = await api.get('/documents', { params })
    return response.data
  },

  /**
   * Get document by ID
   */
  getById: async (id: number): Promise<{ success: boolean; data: Document }> => {
    const response = await api.get(`/documents/${id}`)
    return response.data
  },

  /**
   * Delete a document
   */
  delete: async (id: number): Promise<{ success: boolean; message: string }> => {
    const response = await api.delete(`/documents/${id}`)
    return response.data
  },

  /**
   * Rename a document
   */
  rename: async (
    id: number,
    name: string
  ): Promise<{ success: boolean; data: Document; message: string }> => {
    const response = await api.put(`/documents/${id}/rename`, { name })
    return response.data
  },

  /**
   * Get document parse status
   */
  getParseStatus: async (
    id: number
  ): Promise<{ success: boolean; data: any }> => {
    const response = await api.get(`/documents/${id}/parse-status`)
    return response.data
  },
}
