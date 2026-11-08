// 逐格錄動畫（30fps），加上配樂，輸出 MP4：node render3d.js <zh|id|vi> <配樂.wav> <輸出.mp4> [頁面，預設 promo-ad.html] [秒數，預設 54.5]
const {chromium}=require('playwright');const path=require('path');const {spawn}=require('child_process');
(async()=>{
  const [lang,music,out,page='promo-ad.html',dur='54.5']=process.argv.slice(2);const FPS=30,DUR=+dur;
  const ff=spawn('ffmpeg',['-loglevel','error','-y','-f','image2pipe','-framerate',String(FPS),'-i','-','-i',music,
    '-c:v','libx264','-preset','medium','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-shortest','-movflags','+faststart',out],{stdio:['pipe','inherit','inherit']});
  const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1280,height:720}});
  await pg.goto('file://'+path.resolve(__dirname,page)+`?lang=${lang}&render=1`);
  await pg.waitForTimeout(500);
  const n=Math.round(DUR*FPS);
  for(let i=0;i<n;i++){
    await pg.evaluate(t=>window.seek(t),i/FPS);
    const buf=await pg.screenshot({type:'jpeg',quality:92});
    if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));
    if(i%300===0)console.log(lang,'frame',i,'/',n);
  }
  ff.stdin.end();await new Promise(r=>ff.on('close',r));await b.close();console.log('done',out);
})();
