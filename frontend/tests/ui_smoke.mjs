/**
 * UI 冒烟：用 Edge 无头模式真正渲染前端页面，抓 console 错误与失败请求。
 *
 * 存在的理由：api_contract.mjs 只验证了 API 层返回值形状，证明不了
 * Vue 组件能正常渲染 —— 而本项目此前的前端故障正是"接口有数据、页面空白"。
 * 这里直接 dump 渲染后的 DOM，看关键节点里有没有真实数据。
 *
 * 用法：node tests/ui_smoke.mjs [baseUrl] [dumpDir]
 */
import { execFileSync } from 'node:child_process'
import { mkdirSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const BASE = process.argv[2] || 'http://127.0.0.1:3000'
const DUMP = process.argv[3] || 'tests/.dump'
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'

const ROUTES = [
  // 路径取自 src/router/index.ts；写错会被 catch-all 重定向到 '/'，
  // 表现为"两个页面 DOM 一模一样"却仍然全部 PASS。
  { path: '/', name: 'chat', wait: 3500 },
  { path: '/kb', name: 'knowledge', wait: 3500 },
  { path: '/settings', name: 'settings', wait: 3000 },
]

mkdirSync(DUMP, { recursive: true })

let pass = 0
let fail = 0
function check(name, ok, detail = '') {
  if (ok) {
    pass++
    console.log(`[PASS] ${name}${detail ? '  — ' + detail : ''}`)
  } else {
    fail++
    console.log(`[FAIL] ${name}  — ${detail}`)
  }
}

function render(route) {
  // profile 目录必须是 Windows 绝对路径。踩过的坑：Git-Bash 风格的 /tmp/xxx
  // 传给 Edge 后它无法解析，进程既不退出也不输出，spawnSync 只能等到超时
  // （表现为"所有路由渲染超时"，但 Edge 本身完全正常）。
  const profile = join(tmpdir(), 'baizeos-edge-' + route.name)
  const html = join(DUMP, route.name + '.html')
  // Edge 退出码不一定是 0（后台进程残留），但 stdout 里往往已带完整 DOM，
  // 所以 catch 后回退读 stdout，只有 stdout 也空才算失败。
  let dom = ''
  try {
    dom = execFileSync(
      EDGE,
      [
        '--headless=new',
        '--disable-gpu',
        '--no-sandbox',
        '--virtual-time-budget=6000',
        `--user-data-dir=${profile}`,
        `--dump-dom`,
        BASE + route.path,
      ],
      { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], timeout: 45000 },
    )
  } catch (e) {
    dom = e.stdout || ''
    if (!dom) throw e
  }
  writeFileSync(html, dom, 'utf8')
  return dom
}

const digests = new Map()

for (const route of ROUTES) {
  let dom = ''
  let ok = false
  try {
    dom = render(route)
    ok = dom.length > 0
  } catch (e) {
    dom = ''
    console.log('  render error:', e.message)
  }
  check(`渲染 ${route.path}`, ok, `${dom.length} 字节 DOM`)

  if (!ok) continue

  // Vue 挂载成功：#app 内不再是空的
  const body = dom.replace(/[\s\S]*<div id="app">/, '')
  const hasContent = body.replace(/<\/div>[\s\S]*/, '').trim().length > 20
  check(`${route.path} #app 已挂载内容`, hasContent)

  // 关键：不能出现 Vue 的运行时错误提示
  const vueError = /\[Vue warn\]|Unhandled error|TypeError:|Cannot read propert/.test(dom)
  check(`${route.path} 无 Vue/JS 运行时错误`, !vueError,
    vueError ? dom.match(/TypeError:.*|Cannot read propert.*/)?.[0]?.slice(0, 90) : '')

  // 不能出现后端连不上的空态文案
  const offline = /后端未返回模型列表|无法连接后端服务|请求失败（HTTP 0）/.test(dom)
  check(`${route.path} 无"连不上后端"迹象`, !offline)

  digests.set(route.name, dom)
}

// 页面必须各不相同。写错路由路径会被 catch-all 重定向到 '/'，此时每个
// 页面都能"渲染成功 + 无报错"，却其实测的是同一个视图 —— 只有比对
// 渲染结果才能发现。
const names = [...digests.keys()]
for (let i = 0; i < names.length; i++) {
  for (let j = i + 1; j < names.length; j++) {
    const a = digests.get(names[i])
    const b = digests.get(names[j])
    check(`/${names[i]} 与 /${names[j]} 渲染结果不同`, a !== b,
      a === b ? '两者 DOM 完全一致 —— 很可能路由路径写错被重定向了' : '')
  }
}

// 聊天页必须真的把后端数据渲染出来（会话标题来自 /v1/conversations）
const chatDom = digests.get('chat') || ''
check('聊天页渲染出真实会话数据', /conversation|会话|新建对话|durability|rag-usage/.test(chatDom),
  chatDom.length ? '' : 'chat 页未渲染')


console.log('\n' + '='.repeat(52))
console.log(`  合计 ${pass + fail} 项：通过 ${pass}，失败 ${fail}`)
console.log(`  DOM dump: ${DUMP}`)
console.log('='.repeat(52))
process.exit(fail === 0 ? 0 : 1)
