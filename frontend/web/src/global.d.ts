declare module 'markdown-it' {
  interface MarkdownIt {
    render: (text: string) => string
  }
  const MarkdownIt: {
    new (options?: Record<string, unknown>): MarkdownIt
  }
  export default MarkdownIt
}
