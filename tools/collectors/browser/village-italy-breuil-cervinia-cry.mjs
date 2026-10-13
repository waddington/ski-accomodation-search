import { chromium } from "playwright";
import fs from "fs";
const S="/tmp/chalet-scratch/village-italy-breuil-cervinia";
const slugs=process.argv.slice(2);
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "en-GB", viewport: { width: 1366, height: 900 } });
const reqs=[];
page.on("response", async r=>{ const u=r.url(); const ct=r.headers()["content-type"]||""; if(ct.includes("json") && /crystal|tui/.test(u)){ let b=""; try{b=(await r.text()).slice(0,2500)}catch{}; reqs.push({u,b}); }});
for(const s of slugs){
  reqs.length=0;
  await page.goto(`https://www.crystalski.co.uk/ski-resorts/italy-ski-holidays/cervinia/${s}/`,{waitUntil:"domcontentloaded"});
  await page.waitForTimeout(5000);
  await page.getByRole("button",{name:/accept/i}).first().click().catch(()=>{});
  await page.waitForTimeout(1000);
  fs.writeFileSync(`${S}/cry-${s}.txt`, await page.innerText("body"));
  const imgs=await page.$$eval("img",is=>is.map(i=>i.currentSrc||i.src).filter(Boolean));
  fs.writeFileSync(`${S}/cry-${s}.imgs`, [...new Set(imgs)].join("\n"));
  fs.writeFileSync(`${S}/cry-${s}.reqs.json`, JSON.stringify(reqs,null,1));
  console.log(s, reqs.length);
  await page.waitForTimeout(2500);
}
await browser.close();
