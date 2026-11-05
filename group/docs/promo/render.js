// 把 promo.html 錄成影片（Playwright 錄 webm，再用 ffmpeg 轉 mp4）：node render.js <輸出資料夾>
const {chromium}=require('playwright');const path=require('path');
(async()=>{
  const out=process.argv[2]||'.';
  const b=await chromium.launch();
  const ctx=await b.newContext({viewport:{width:1280,height:720},recordVideo:{dir:out,size:{width:1280,height:720}}});
  const pg=await ctx.newPage();
  await pg.goto('file://'+path.resolve(__dirname,'promo.html'));
  const shots=[[4000,'f1'],[17000,'f2'],[26000,'f3'],[40000,'f4'],[50000,'f5'],[59000,'f6']];let t0=Date.now();
  for(const [at,name] of shots){const w=at-(Date.now()-t0);if(w>0)await pg.waitForTimeout(w);await pg.screenshot({path:path.join(out,name+'.png')})}
  await pg.waitForFunction(()=>document.body.dataset.done==='1',null,{timeout:90000});
  await pg.waitForTimeout(800);
  const v=pg.video();await ctx.close();console.log(await v.path());await b.close();
})();
