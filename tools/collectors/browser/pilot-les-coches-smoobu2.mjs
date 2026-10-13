import { chromium } from "playwright";
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "en-GB" });
await page.goto("https://booking.smoobu.com/9A1161918", { waitUntil: "networkidle" });
const weeks = process.argv.slice(2);
for (const w of weeks) {
  const [a, d] = w.split("-");
  const r = await page.evaluate(async ([a, d]) => {
    const u = `/9A1161918/checkAvailability?theme=booking-tool&arrivalDate=${a}&departureDate=${d}&userId=1161918&guests=10&adults=10&children=0`;
    const res = await fetch(u, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    return await res.text();
  }, [a, d]);
  let j; try { j = JSON.parse(r).data; } catch { console.log(w, "nonjson", r.slice(0, 200)); continue; }
  const av = j.availabilityResponse;
  console.log(w, "avail", JSON.stringify(av.availableApartments), "prices", JSON.stringify(av.prices).slice(0, 500), "err", JSON.stringify(av.errorMessages).slice(0, 300), "apts", JSON.stringify((j.apartments||[]).map(x=>[x.id,x.name])));
  await page.waitForTimeout(800);
}
await browser.close();
