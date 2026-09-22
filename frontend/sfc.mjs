import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import fs from 'node:fs'
for (const f of process.argv.slice(2)) {
  const src = fs.readFileSync(f, 'utf8')
  const { descriptor, errors } = parse(src, { filename: f })
  if (errors.length) { console.log('PARSE', f, errors.map(e => e.message)); continue }
  try {
    const script = compileScript(descriptor, { id: 'x', inlineTemplate: true })
    const t = descriptor.template && compileTemplate({ source: descriptor.template.content, filename: f, id: 'x', compilerOptions: { bindingMetadata: script.bindings } })
    console.log('OK  ', f, t && t.errors.length ? t.errors : '')
  } catch (e) { console.log('FAIL', f, e.message) }
}
