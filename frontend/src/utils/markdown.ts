import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js/lib/core'

// 按需注册常用语言，控制包体
import javascript from 'highlight.js/lib/languages/javascript'
import typescript from 'highlight.js/lib/languages/typescript'
import python from 'highlight.js/lib/languages/python'
import json from 'highlight.js/lib/languages/json'
import bash from 'highlight.js/lib/languages/bash'
import xml from 'highlight.js/lib/languages/xml'
import css from 'highlight.js/lib/languages/css'
import markdownLang from 'highlight.js/lib/languages/markdown'
import sql from 'highlight.js/lib/languages/sql'
import yaml from 'highlight.js/lib/languages/yaml'
import java from 'highlight.js/lib/languages/java'
import c from 'highlight.js/lib/languages/c'
import cpp from 'highlight.js/lib/languages/cpp'
import go from 'highlight.js/lib/languages/go'
import rust from 'highlight.js/lib/languages/rust'
import diff from 'highlight.js/lib/languages/diff'
import ini from 'highlight.js/lib/languages/ini'

hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('python', python)
hljs.registerLanguage('json', json)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('xml', xml)
hljs.registerLanguage('css', css)
hljs.registerLanguage('markdown', markdownLang)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('yaml', yaml)
hljs.registerLanguage('java', java)
hljs.registerLanguage('c', c)
hljs.registerLanguage('cpp', cpp)
hljs.registerLanguage('go', go)
hljs.registerLanguage('rust', rust)
hljs.registerLanguage('diff', diff)
hljs.registerLanguage('ini', ini)

const md: MarkdownIt = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

/** 代码块：外包一层带语言标签与复制按钮的容器 */
md.renderer.rules.fence = (tokens, idx) => {
  const token = tokens[idx]!
  const lang = (token.info || '').trim().split(/\s+/)[0] || ''
  let highlighted = ''
  let langLabel = lang || '文本'

  if (lang && hljs.getLanguage(lang)) {
    try {
      highlighted = hljs.highlight(token.content, { language: lang }).value
    } catch {
      highlighted = ''
    }
  }
  if (!highlighted) {
    highlighted = md.utils.escapeHtml(token.content)
    if (!lang) langLabel = '文本'
  }

  const safeLabel = md.utils.escapeHtml(langLabel)
  return (
    `<div class="code-block">` +
    `<div class="code-head"><span class="code-lang">${safeLabel}</span>` +
    `<button type="button" class="code-copy" data-code-copy aria-label="复制代码">复制</button></div>` +
    `<pre><code class="hljs">${highlighted}</code></pre></div>`
  )
}

/** 外链新窗口打开 */
md.renderer.rules.link_open = (tokens, idx, options, _env, self) => {
  const token = tokens[idx]!
  token.attrSet('target', '_blank')
  token.attrSet('rel', 'noopener noreferrer')
  return self.renderToken(tokens, idx, options)
}

/** 渲染 Markdown 为 HTML（聊天内容为受信任的本地产物，但仍然关闭原始 HTML） */
export function renderMarkdown(text: string): string {
  return md.render(text ?? '')
}

export { hljs }
