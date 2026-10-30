// Viewer pixel-grid check: renders 4A (fit) and a follow close-up at deviceScaleFactor 1/2/3, saves the raw canvas
// (dpr_*.png, device pixels) + page screenshots (dprshot_*.png) and prints the device scale (ds) used.
//   PLAYWRIGHT_DIR=... node tools/v2/viewer_dpr.js [baseURL] [outDir]
const path=require('path');
const {chromium}=require(process.env.PLAYWRIGHT_DIR ? require('path').join(process.env.PLAYWRIGHT_DIR, 'node_modules/playwright') : 'playwright');
const BASE=(process.argv[2]||'http://127.0.0.1:8765')+'/harness/viewer/index.html'; const OUT=process.argv[3]||'/tmp';
(async()=>{
  const b=await chromium.launch();
  for (const dpr of [1,2,3]) for (const [tag,q] of [['4A','loc=floor4&view=4A&t=17:46:58'],['follow','loc=floor4&view=4A&t=17:46:58&follow=sheldon&zoom=2.5']]) {
    const ctx=await b.newContext({viewport:{width:1280,height:720},deviceScaleFactor:dpr});
    const p=await ctx.newPage(); const errs=[]; p.on('pageerror',e=>errs.push(String(e)));
    await p.goto(`${BASE}?${q}&play=0&manual=1&bare=1`); await p.waitForFunction(()=>document.title.includes('ready'),null,{timeout:60000});
    const info=await p.evaluate(()=>{viewer.render(1.0); const cv=document.querySelector('#cv'); const t=cv.getContext('2d'); 
      return {ds:viewer.V? viewer.V.ds: null, cw:cv.width, ch:cv.height, css:getComputedStyle(cv).imageRendering};});
    // export the raw canvas (device pixels) instead of a screenshot so overlays/compositing don't interfere
    const data=await p.evaluate(()=>document.querySelector('#cv').toDataURL('image/png'));
    require('fs').writeFileSync(`${OUT}/dpr_${tag}_${dpr}.png`,Buffer.from(data.split(',')[1],'base64'));
    await p.screenshot({path:`${OUT}/dprshot_${tag}_${dpr}.png`});
    console.log(dpr,tag,JSON.stringify(info),errs);
    await ctx.close();
  }
  await b.close();
})();
