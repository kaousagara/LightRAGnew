import { useMemo } from 'react'

export function useLaTeXValidator(content: string): boolean {
  return useMemo(() => {
    const blockLatexMatches = content.match(/\$\$/g) || []
    const hasUnclosedBlock = blockLatexMatches.length % 2 !== 0

    const contentWithoutBlocks = content.replace(/\$\$[\s\S]*?\$\$/g, '')
    const inlineLatexMatches = contentWithoutBlocks.match(/(?<!\$)\$(?!\$)/g) || []
    const hasUnclosedInline = inlineLatexMatches.length % 2 !== 0

    return !hasUnclosedBlock && !hasUnclosedInline
  }, [content])
}
