// 檢查各頁面的多國語言對照表：每種語言的詞條要和繁體中文一樣齊全，佔位符 {n} {size} {lang} 也要一致；
// 頁面與程式用到的詞條都要存在。執行：node group/tests/check_i18n.js
const fs = require('fs'), path = require('path');
const ph = s => (String(s).match(/\{\w+\}/g) || []).sort().join(',');
let bad = 0;
for (const page of ['simple.html', 'live.html', 'admin.html']) {
  const html = fs.readFileSync(path.join(__dirname, '..', page), 'utf8');
  const src = html.match(/const I18N=\{[\s\S]*?\n?\}\};/)[0];
  const I18N = new Function(src + '; return I18N;')();
  const langs = Object.keys(I18N);
  for (const code of langs) {
    const d = I18N[code];
    for (const k of Object.keys(I18N.zh)) {
      if (!(k in d)) { console.log(`${page} ${code} 缺 ${k}`); bad++; }
      else if (ph(d[k]) !== ph(I18N.zh[k])) { console.log(`${page} ${code}.${k} 佔位符不一致`); bad++; }
    }
    for (const k of Object.keys(d)) if (!(k in I18N.zh)) { console.log(`${page} ${code} 多了 ${k}`); bad++; }
  }
  for (const m of html.matchAll(/data-t(?:-html|-ph)?="(\w+)"/g)) if (!(m[1] in I18N.zh)) { console.log(`${page} 頁面用到不存在的詞條 ${m[1]}`); bad++; }
  for (const m of html.matchAll(/\bt\('(\w+)'[,)]/g)) if (!(m[1] in I18N.zh)) { console.log(`${page} 程式用到不存在的詞條 ${m[1]}`); bad++; }
  console.log(`${page}：${langs.length} 種語言、各 ${Object.keys(I18N.zh).length} 個詞條`);
}
console.log(bad ? `共 ${bad} 個問題` : 'OK');
process.exit(bad ? 1 : 0);
