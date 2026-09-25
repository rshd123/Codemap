import { createContext, useContext, useReducer, useCallback } from 'react'
import { search as searchApi } from '../services/api'

const SearchContext = createContext(null)

const initialState = {
  query: '',
  graphData: { nodes: [], links: [] },
  cypher: '',
  explanation: '',
  loading: false,
  error: null,
  selectedNode: null,
}

function reducer(state, action) {
  switch (action.type) {
    case 'SEARCH_START':
      return {
        ...state,
        query: action.query,
        loading: true,
        error: null,
        explanation: '',
        cypher: '',
        selectedNode: null,
      }
    case 'SEARCH_SUCCESS':
      return {
        ...state,
        loading: false,
        graphData: action.graphData,
        cypher: action.cypher,
        explanation: action.explanation,
      }
    case 'SEARCH_ERROR':
      return { ...state, loading: false, error: action.error }
    case 'SET_GRAPH':
      return { ...state, graphData: action.graphData, loading: false, error: null }
    case 'SELECT_NODE':
      return { ...state, selectedNode: action.node }
    case 'CLEAR_SELECTION':
      return { ...state, selectedNode: null }
    case 'RESET':
      return { ...initialState }
    default:
      return state
  }
}

export function SearchProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState)

  const runSearch = useCallback(async (prompt) => {
    dispatch({ type: 'SEARCH_START', query: prompt })
    try {
      const res = await searchApi(prompt)
      const data = res.data
      dispatch({
        type: 'SEARCH_SUCCESS',
        graphData: data.graphData || { nodes: [], links: [] },
        cypher: data.cypher || '',
        explanation: data.explanation || '',
      })
    } catch (err) {
      const detail =
        err.response?.data?.detail || err.message || 'Search failed'
      dispatch({ type: 'SEARCH_ERROR', error: detail })
    }
  }, [])

  const setGraph = useCallback((graphData) => {
    dispatch({ type: 'SET_GRAPH', graphData })
  }, [])

  const selectNode = useCallback((node) => {
    dispatch({ type: 'SELECT_NODE', node })
  }, [])

  const clearSelection = useCallback(() => {
    dispatch({ type: 'CLEAR_SELECTION' })
  }, [])

  const reset = useCallback(() => {
    dispatch({ type: 'RESET' })
  }, [])

  const value = {
    ...state,
    runSearch,
    setGraph,
    selectNode,
    clearSelection,
    reset,
  }

  return <SearchContext.Provider value={value}>{children}</SearchContext.Provider>
}

export function useSearch() {
  const ctx = useContext(SearchContext)
  if (!ctx) {
    throw new Error('useSearch must be used within a SearchProvider')
  }
  return ctx
}
