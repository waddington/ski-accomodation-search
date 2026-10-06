#!/usr/bin/env node
// Load a page in headless Chromium (renders JS, looks like a normal browser)
// and dump what a scraper needs.
//
//   node tools/browse.mjs <url> [outdir] [--wait=ms] [--click="css selector"] [--headed]
//
// Writes to outdir (default: ./browse-out):
//   page.txt     rendered visible text
//   page.html    rendered HTML
//   images.txt   absolute image URLs (img src/srcset, CSS backgrounds), largest first where known
//   links.txt    absolute link URLs with their text
//   shot.png     full-page screenshot
// Prints the final URL, title and file paths.
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "fs";
import { join } from "path";

const args = process.argv.slice(2);
const url = args.find((a) => !a.startsWith("--"));
const outdir = args.filter((a) => !a.startsWith("--"))[1] || "browse-out";
const opt = (k) => args.find((a) => a.startsWith(`--${k}=`))?.split("=").slice(1).join("=");
const wait = Number(opt("wait") || 3000);
const clicks = args.filter((a) => a.startsWith("--click=")).map((a) => a.slice(8));
if (!url) {
  console.error("usage: node tools/browse.mjs <url> [outdir] [--wait=ms] [--click=selector] [--headed]");
  process.exit(2);
}

mkdirSync(outdir, { recursive: true });
const browser = await chromium.launch({ headless: !args.includes("--headed"), channel: "chrome" });
const page = await browser.newPage({
  userAgent:
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36",
  viewport: { width: 1366, height: 900 },
  locale: "en-GB",
});
try {
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(wait);
  // Dismiss common cookie banners.
  for (const label of ["Accept all", "Accept All", "Accept", "I agree", "Tout accepter", "OK"]) {
    const b = page.getByRole("button", { name: label, exact: true });
    if (await b.count()) { await b.first().click().catch(() => {}); break; }
  }
  for (const sel of clicks) {
    await page.click(sel, { timeout: 10000 }).catch((e) => console.error(`click ${sel}: ${e.message}`));
    await page.waitForTimeout(wait);
  }
  // Scroll to trigger lazy-loaded images.
  await page.evaluate(async () => {
    for (let y = 0; y < document.body.scrollHeight; y += 800) {
      window.scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 150));
    }
  });
  await page.waitForTimeout(1000);

  const data = await page.evaluate(() => {
    const abs = (u) => { try { return new URL(u, location.href).href; } catch { return null; } };
    const imgs = new Map();
    for (const img of document.images) {
      const cands = [img.currentSrc, img.src, img.dataset.src, img.dataset.lazySrc];
      if (img.srcset) cands.push(...img.srcset.split(",").map((s) => s.trim().split(" ")[0]));
      for (const c of cands) if (c) { const a = abs(c); if (a && !imgs.has(a)) imgs.set(a, img.naturalWidth * img.naturalHeight); }
    }
    for (const el of document.querySelectorAll("[style*='background']")) {
      const m = el.style.backgroundImage.match(/url\(["']?(.*?)["']?\)/);
      if (m) { const a = abs(m[1]); if (a && !imgs.has(a)) imgs.set(a, el.offsetWidth * el.offsetHeight); }
    }
    const links = [...document.links].map((l) => `${l.href}\t${l.innerText.trim().replace(/\s+/g, " ").slice(0, 80)}`);
    return {
      text: document.body.innerText,
      images: [...imgs.entries()].sort((a, b) => b[1] - a[1]).map(([u]) => u).filter((u) => !u.startsWith("data:")),
      links: [...new Set(links)],
      title: document.title,
    };
  });
  writeFileSync(join(outdir, "page.txt"), data.text);
  writeFileSync(join(outdir, "page.html"), await page.content());
  writeFileSync(join(outdir, "images.txt"), data.images.join("\n") + "\n");
  writeFileSync(join(outdir, "links.txt"), data.links.join("\n") + "\n");
  await page.screenshot({ path: join(outdir, "shot.png"), fullPage: true }).catch(() => {});
  console.log(`url:   ${page.url()}\ntitle: ${data.title}\nout:   ${outdir}/{page.txt,page.html,images.txt,links.txt,shot.png}`);
  console.log(`text chars: ${data.text.length}, images: ${data.images.length}, links: ${data.links.length}`);
} finally {
  await browser.close();
}
