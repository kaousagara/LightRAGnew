import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  getDocuments, 
  getDocumentsPaginated,
  deleteDocuments,
  clearDocuments,
  insertText,
  uploadDocument,
  type DocsStatusesResponse,
  type PaginatedDocsResponse,
  type DocumentsRequest
} from '@/api/lightrag'

export const DOCUMENTS_QUERY_KEY = ['documents']

export function useDocuments() {
  return useQuery<DocsStatusesResponse>({
    queryKey: DOCUMENTS_QUERY_KEY,
    queryFn: getDocuments,
  })
}

export function useDocumentsPaginated(request: DocumentsRequest) {
  return useQuery<PaginatedDocsResponse>({
    queryKey: [...DOCUMENTS_QUERY_KEY, 'paginated', request],
    queryFn: () => getDocumentsPaginated(request),
    staleTime: 10000,
  })
}

export function useDeleteDocuments() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ docIds, deleteFile = false }: { docIds: string[], deleteFile?: boolean }) => 
      deleteDocuments(docIds, deleteFile),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY })
    },
  })
}

export function useClearDocuments() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: () => clearDocuments(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY })
    },
  })
}

export function useInsertText() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (text: string) => insertText(text),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY })
    },
  })
}

export function useUploadDocument() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ file, onUploadProgress }: { file: File, onUploadProgress?: (percentCompleted: number) => void }) => 
      uploadDocument(file, onUploadProgress),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY })
    },
  })
}
