// 檢查 simple.html 的多國語言對照表：每種語言的詞條要和繁體中文一樣齊全，佔位符 {n} {size} {lang} 也要一致
// 執行：node group/tests/check_i18n.js
const fs = require('fs'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'simple.html'), 'utf8');
const src = html.match(/const LANGS=[\s\S]*?\n\}\};/)[0];
const { LANGS, I18N } = new Function(src + '; return {LANGS, I18N};')();
let bad = 0;
const ph = s => (String(s).match(/\{\w+\}/g) || []).sort().join(',');
for (const [code] of LANGS) {
  const d = I18N[code];
  if (!d) { console.log(`缺少語言 ${code}`); bad++; continue; }
  for (const k of Object.keys(I18N.zh)) {
    if (!(k in d)) { console.log(`${code} 缺 ${k}`); bad++; }
    else if (ph(d[k]) !== ph(I18N.zh[k])) { console.log(`${code}.${k} 佔位符不一致`); bad++; }
  }
  for (const k of Object.keys(d)) if (!(k in I18N.zh)) { console.log(`${code} 多了 ${k}`); bad++; }
}
// 頁面上用到的詞條都要存在
for (const m of html.matchAll(/data-t(?:-html|-ph)?="(\w+)"/g)) if (!(m[1] in I18N.zh)) { console.log(`頁面用到不存在的詞條 ${m[1]}`); bad++; }
for (const m of html.matchAll(/\bt\('(\w+)'[,)]/g)) if (!(m[1] in I18N.zh)) { console.log(`程式用到不存在的詞條 ${m[1]}`); bad++; }
console.log(bad ? `共 ${bad} 個問題` : `OK：${LANGS.length} 種語言、各 ${Object.keys(I18N.zh).length} 個詞條`);
process.exit(bad ? 1 : 0);
