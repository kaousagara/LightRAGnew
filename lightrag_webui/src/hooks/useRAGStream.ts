import { useCallback, useRef, useState } from 'react'
import { queryTextStream, type QueryRequest } from '@/api/lightrag'
import { errorMessage } from '@/lib/utils'

export interface RAGStreamState {
  content: string
  isStreaming: boolean
  error: string | null
}

export function useRAGStream() {
  const [state, setState] = useState<RAGStreamState>({
    content: '',
    isStreaming: false,
    error: null
  })

  const abortControllerRef = useRef<AbortController | null>(null)

  const startStream = useCallback(async (
    request: QueryRequest,
    onChunk?: (chunk: string) => void
  ): Promise<void> => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }

    const controller = new AbortController()
    abortControllerRef.current = controller

    setState({ content: '', isStreaming: true, error: null })

    try {
      await queryTextStream(
        { ...request, stream: true },
        (chunk) => {
          if (!controller.signal.aborted) {
            setState(prev => ({
              ...prev,
              content: prev.content + chunk
            }))
            onChunk?.(chunk)
          }
        },
        (error) => {
          if (!controller.signal.aborted) {
            setState(prev => ({
              ...prev,
              isStreaming: false,
              error
            }))
          }
        }
      )

      if (!controller.signal.aborted) {
        setState(prev => ({ ...prev, isStreaming: false }))
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        const errMsg = errorMessage(error)
        setState(prev => ({
          ...prev,
          isStreaming: false,
          error: errMsg
        }))
      }
    }
  }, [])

  const stopStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
      setState(prev => ({ ...prev, isStreaming: false }))
    }
  }, [])

  const reset = useCallback(() => {
    stopStream()
    setState({ content: '', isStreaming: false, error: null })
  }, [stopStream])

  return {
    ...state,
    startStream,
    stopStream,
    reset
  }
}
