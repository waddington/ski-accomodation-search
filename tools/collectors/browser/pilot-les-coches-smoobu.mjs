import { chromium } from "playwright";
const [arr, dep, adults] = process.argv.slice(2);
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "en-GB" });
page.on("response", async (r) => {
  const u = r.url();
  if (/smoobu/.test(u) && /avail|price|search|apartment|check/i.test(u) && !/\.(js|css|png|svg|woff)/.test(u)) {
    let b = ""; try { b = (await r.text()).slice(0, 3000); } catch {}
    console.log("XHR", r.status(), u, "\n", b);
  }
});
await page.goto("https://booking.smoobu.com/9A1161918", { waitUntil: "networkidle" });
const fmt = await page.$eval("#dpArrival", (e) => ({ ph: e.placeholder, ro: e.readOnly, type: e.type, v: e.value, df: e.dataset }));
console.log("field", JSON.stringify(fmt));
for (const [sel, val] of [["#dpArrival", arr], ["#dpDeparture", dep]]) {
  await page.$eval(sel, (e, v) => { e.removeAttribute("readonly"); e.value = v; e.dispatchEvent(new Event("input", {bubbles:true})); e.dispatchEvent(new Event("change", {bubbles:true})); }, val);
}
await page.selectOption("#adults", adults || "10");
await page.click("#check-availability-button");
await page.waitForTimeout(6000);
const txt = await page.$eval("#content", (e) => e.innerText);
console.log("TEXT\n", txt.replace(/\n\s*\n/g, "\n").slice(0, 3000));
await page.screenshot({ path: "/tmp/chalet-scratch/smoobu.png", fullPage: true });
await browser.close();
