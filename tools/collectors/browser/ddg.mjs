import { chromium } from "playwright";
const b = await chromium.launch({ headless: true, channel: "chrome" });
const p = await b.newPage({ locale: "en-GB" });
for (const q of process.argv.slice(2)) {
  await p.goto("https://www.bing.com/search?setlang=en-GB&cc=GB&q=" + encodeURIComponent(q), { waitUntil: "domcontentloaded" });
  await p.waitForTimeout(3500);
  const res = await p.$$eval("li.b_algo h2 a", as => as.slice(0, 8).map(a => a.innerText.trim() + " | " + a.href));
  console.log("=== " + q + "\n  " + res.join("\n  "));
  await p.waitForTimeout(2500);
}
await b.close();
