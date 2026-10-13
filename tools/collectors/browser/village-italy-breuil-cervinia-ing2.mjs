import { chromium } from "playwright";
import fs from "fs";
const S="/tmp/chalet-scratch/village-italy-breuil-cervinia";
const base="https://www.inghams.co.uk/ski-holidays/ski-resorts/italy/aosta-valley-ski-area/cervinia/";
const slugs=["hotel-serenella","hotel-punta-maquignaz","hotel-dragon","base-camp-apartments-cervinia","hotel-perruquet","hotel-breuil","hotel-grivola","vretreats-cervino"];
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "en-GB", viewport: { width: 1366, height: 900 } });
let hdrs=null, code=null;
page.on("request", r=>{ const u=r.url(); if(u.includes("pcms.inghams.co.uk/api/Availability")){ hdrs=r.headers(); const m=u.match(/propertyCode=([A-Z0-9]+)/); if(m) code=m[1]; }});
const out={};
for(const s of slugs){
  code=null;
  await page.goto(base+s,{waitUntil:"domcontentloaded"}); await page.waitForTimeout(3000);
  await page.getByRole("button",{name:/accept/i}).first().click().catch(()=>{});
  await page.getByRole("button",{name:/check availability/i}).first().click().catch(()=>{});
  await page.waitForTimeout(4000);
  const txt=await page.innerText("body"); fs.writeFileSync(`${S}/ing-${s}.txt`,txt);
  const imgs=await page.$$eval("img",is=>is.map(i=>i.currentSrc||i.src).filter(Boolean));
  const res={code,imgs:[...new Set(imgs)].slice(0,40)};
  if(code&&hdrs){
    for(const [d,a] of [["2027-03-21",2],["2027-03-21",3],["2027-03-21",4]]){
      const u=`https://pcms.inghams.co.uk/api/Availability/ING/GBINA%7CGBINN%7CGBIND/departure-dates?propertyCode=${code}&nights=7&departureDate=${d}&adults=${a}&self=true&sortOrder=Ascending`;
      const h={...hdrs}; delete h["host"];
      const r=await page.request.get(u,{headers:h}); res["d"+d+"a"+a]=(await r.text()).slice(0,3000);
      await page.waitForTimeout(1500);
    }
  }
  out[s]=res; console.log(s,code,(res["d2027-03-21a2"]||"").slice(0,300));
  await page.waitForTimeout(2500);
}
fs.writeFileSync(S+"/ing-prices.json",JSON.stringify(out,null,1));
await browser.close();
