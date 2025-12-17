import api from './api'

export interface DataTemplate {
  id: number
  name: string
  description?: string
  schema: any
  field_definitions: any[]
  example_data?: any
  field_count: number
  created_by?: number
  created_at?: string
  updated_at?: string
}

export interface TemplateListResponse {
  items: DataTemplate[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface TemplateCreateRequest {
  name: string
  description?: string
  schema: any
  field_definitions: any[]
  example_data?: any
}

export interface TemplateUpdateRequest {
  name?: string
  description?: string
  schema?: any
  field_definitions?: any[]
  example_data?: any
}

export interface TemplateCopyRequest {
  name?: string
}

export interface ParseJsonRequest {
  json_string: string
  use_agent?: boolean
}

export interface ParseJsonResponse {
  schema: any
  field_definitions: any[]
}

export const dataTemplateService = {
  /**
   * Get templates list with pagination and search
   */
  getList: async (
    page: number = 1,
    pageSize: number = 20,
    search?: string
  ): Promise<{ success: boolean; data: TemplateListResponse }> => {
    const params: any = {
      page,
      page_size: pageSize,
    }
    if (search) {
      params.search = search
    }
    
    const response = await api.get('/data-templates', { params })
    return response.data
  },

  /**
   * Get template by ID
   */
  getById: async (id: number): Promise<{ success: boolean; data: DataTemplate }> => {
    const response = await api.get(`/data-templates/${id}`)
    return response.data
  },

  /**
   * Create a new template
   */
  create: async (
    template: TemplateCreateRequest
  ): Promise<{ success: boolean; data: DataTemplate; message: string }> => {
    const response = await api.post('/data-templates', template)
    return response.data
  },

  /**
   * Update a template
   */
  update: async (
    id: number,
    template: TemplateUpdateRequest
  ): Promise<{ success: boolean; data: DataTemplate; message: string }> => {
    const response = await api.put(`/data-templates/${id}`, template)
    return response.data
  },

  /**
   * Delete a template
   */
  delete: async (id: number): Promise<{ success: boolean; message: string }> => {
    const response = await api.delete(`/data-templates/${id}`)
    return response.data
  },

  /**
   * Copy a template
   */
  copy: async (
    id: number,
    newName?: string
  ): Promise<{ success: boolean; data: DataTemplate; message: string }> => {
    const request: TemplateCopyRequest = {}
    if (newName) {
      request.name = newName
    }
    const response = await api.post(`/data-templates/${id}/copy`, request)
    return response.data
  },

  /**
   * Parse JSON string to schema and field definitions
   */
  parseJson: async (
    jsonString: string,
    useAgent: boolean = false
  ): Promise<{ success: boolean; data: ParseJsonResponse }> => {
    const request: ParseJsonRequest = { 
      json_string: jsonString,
      use_agent: useAgent
    }
    const response = await api.post('/data-templates/parse-json', request)
    return response.data
  },
}
