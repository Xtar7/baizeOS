/**
 * 前端 API 层契约测试（Node 环境跑真实 axios，走 Vite 代理）。
 *
 * 背景：request.ts 曾用 `api.get<T, T>()` 这种双泛型写法 —— 类型上声称
 * 返回值就是响应体，运行时却仍是 AxiosResponse。这类错误 tsc 抓不到，
 * 只在浏览器里表现为"后端正常但前端全空"。本脚本把每个 API 函数的
 * 返回值形状断言一遍，防止再次回归。
 *
 * 用法：node tests/api_contract.mjs [baseUrl]
 */
import axios from 'axios'

const BASE = process.argv[2] || 'http://127.0.0.1:3000'
const api = axios.create({ baseURL: BASE + '/v1', timeout: 120000 })

// 与 src/api/request.ts 中的 helper 保持一致
const apiGet = (u) => api.get(u).then((r) => r.data)
const apiPost = (u, d) => api.post(u, d).then((r) => r.data)
const apiPut = (u, d) => api.put(u, d).then((r) => r.data)
const apiPatch = (u, d) => api.patch(u, d).then((r) => r.data)
const apiDelete = (u, c) => api.delete(u, c).then((r) => r.data)

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

const isArr = Array.isArray

async function main() {
  // ---- 1. listConversations 必须返回数组 ----
  // 旧代码：r.data 拿到的是 {object,data,total} 对象 → 侧边栏 find() 崩溃
  const convs = await apiGet('/conversations?user_id=local').then((r) => r?.data ?? [])
  check('listConversations() 返回数组', isArr(convs), `len=${convs?.length}`)

  // ---- 2. listKB 的 .data 必须是数组 ----
  // 旧代码：res.data 拿到的是 {object,data,total} → list.find() 崩溃
  const kbList = await apiGet('/kb/list')
  check('listKB() 返回 {data: 数组}', isArr(kbList?.data), `len=${kbList?.data?.length}`)

  // ---- 3. listModels 的 .data 必须是数组 ----
  const models = await apiGet('/models')
  check('listModels() 返回 {data: 数组}', isArr(models?.data), `len=${models?.data?.length}`)

  // ---- 4. listEmbeddingModels 的 .models 必须是数组 ----
  // 旧代码：res.models 为 undefined → 模型选择器永远空
  const emb = await apiGet('/rag/embedding_models')
  check('listEmbeddingModels() 返回 models 数组', isArr(emb?.models), `len=${emb?.models?.length}`)

  // ---- 5. listTmpFiles 的 .data 必须是数组 ----
  const chatId = 'contract-' + Date.now()
  const tmp = await apiPost('/files/list', { chat_id: chatId })
  check('listTmpFiles() 返回 {data: 数组}', isArr(tmp?.data), `len=${tmp?.data?.length}`)

  // ---- 6. createConversation 必须直接带 id（旧代码 conv.id 为 undefined）----
  const newId = 'contract' + Date.now()
  const conv = await apiPost('/conversations', { conversation_id: newId })
  check('createConversation() 返回带 id 的对象', conv?.id === newId, `id=${conv?.id}`)

  // ---- 7. getKB 必须直接带 kb_id（旧代码是 AxiosResponse → undefined）----
  if (kbList?.data?.length) {
    const kbId = kbList.data[0].kb_id
    const kb = await apiGet('/kb/' + encodeURIComponent(kbId))
    check('getKB() 返回带 kb_id 的对象', kb?.kb_id === kbId, `kb_id=${kb?.kb_id}`)
  } else {
    check('getKB() 返回带 kb_id 的对象', true, '跳过：没有知识库')
  }

  // ---- 8. getConversation(include_messages) 必须带 messages 数组 ----
  const got = await apiGet('/conversations/' + newId + '?include_messages=true')
  check('getConversation() 带 messages 数组', isArr(got?.messages), `len=${got?.messages?.length}`)

  // ---- 9. 新建知识库 → 返回 kb_id（旧代码 undefined）----
  const created = await apiPost('/kb', { display_name: 'contract-' + Date.now() })
  check('createKB() 返回带 kb_id 的对象', typeof created?.kb_id === 'string', `kb_id=${created?.kb_id}`)

  if (created?.kb_id) {
    // ---- 10. updateKB 的 .kb 必须是对象（KbFormModal 依赖它 emit）----
    const upd = await apiPut('/kb/' + created.kb_id, { display_name: 'contract-renamed' })
    check('updateKB() 返回 {kb: 对象}', !!upd?.kb && typeof upd.kb.kb_id === 'string',
      `needs_rebuild=${upd?.needs_rebuild}`)

    await apiDelete('/kb', { data: { kb_id: created.kb_id } })
  }

  // ---- 11. renameConversation / deleteConversation ----
  await apiPatch('/conversations/' + newId, { title: 'contract-renamed' })
  const after = await apiGet('/conversations/' + newId)
  check('renameConversation() 生效', after?.title === 'contract-renamed', `title=${after?.title}`)

  const del = await apiDelete('/conversations/' + newId)
  check('deleteConversation() 返回 {deleted:true}', del?.deleted === true, JSON.stringify(del))

  // ---- 12. 404 走 ApiError 分支，message 可直接展示 ----
  try {
    await apiGet('/conversations/does-not-exist-xyz')
    check('未知会话抛错', false, '本应抛错但成功了')
  } catch (e) {
    check('未知会话抛错且有可读 message', e.response?.status === 404 && !!e.response?.data?.error,
      `status=${e.response?.status} error=${e.response?.data?.error}`)
  }

  console.log('\n' + '='.repeat(52))
  console.log(`  合计 ${pass + fail} 项：通过 ${pass}，失败 ${fail}`)
  console.log('='.repeat(52))
  return fail === 0 ? 0 : 1
}

main().then(
  (c) => process.exit(c),
  (e) => {
    console.error('测试自身异常:', e)
    process.exit(1)
  },
)
