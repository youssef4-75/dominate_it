// End-to-end test of the website in a real headless Chrome.
//
//   terminal 1:  python main.py --ui web --port 8123
//   terminal 2:  cd tests/e2e_browser && npm install && node e2e.mjs
//
// APP_URL     where the server listens (default http://127.0.0.1:8123/)
// CHROME_PATH use your own Chrome/Chromium instead of the bundled Linux one
//             (needed on Windows/macOS), e.g. CHROME_PATH="/usr/bin/google-chrome"
// Screenshots are written to ./screenshots/
import fs from "node:fs";
import puppeteer from "puppeteer-core";

const URL = process.env.APP_URL || "http://127.0.0.1:8123/";
const SHOTS = "./screenshots";
fs.mkdirSync(SHOTS, { recursive: true });

let launchOptions;
if (process.env.CHROME_PATH) {
  launchOptions = { executablePath: process.env.CHROME_PATH, args: ["--no-sandbox"], headless: true };
} else {
  const { default: chromium } = await import("@sparticuz/chromium");
  launchOptions = { args: [...chromium.args, "--no-sandbox"], executablePath: await chromium.executablePath(), headless: "shell" };
}
const browser = await puppeteer.launch(launchOptions);
const page = await browser.newPage();
await page.setViewport({ width: 1000, height: 780 });
const problems = [];
page.on("pageerror", (e) => problems.push("pageerror: " + e.message));
let expectedBadRequests = 0;  // set just before a click that SHOULD be refused by the server
page.on("console", (m) => {
  if (m.type() !== "error") return;
  if (expectedBadRequests > 0 && m.text().includes("status of 400")) { expectedBadRequests--; return; }
  problems.push("console: " + m.text());
});
const visible = (sel) => page.$eval(sel, (el) => !el.classList.contains("hidden") && el.offsetParent !== null).catch(() => false);
const text = (sel) => page.$eval(sel, (el) => el.textContent.trim());
const check = (name, ok) => console.log((ok ? "PASS " : "FAIL ") + name) || (ok || problems.push("failed: " + name));
const cell = (r, c) => `#board .cell[data-row="${r}"][data-col="${c}"]`;

await page.goto(URL); await page.waitForSelector("#play-btn");
check("home page shown", await visible("#home") && !(await visible("#match")));
await page.screenshot({ path: `${SHOTS}/home.png` });

await page.click("#play-btn"); await page.waitForSelector("#board .cell");
check("match screen with 25 cells", (await page.$$("#board .cell")).length === 25);
check("turns 50 / 50", (await text("#turns")) === "50 / 50");
check("two upcoming cards", (await page.$$("#next-cards .card")).length === 2);
check("current card has 4 colored cells", (await page.$$("#current-card .on")).length === 4);
check("start message", (await text("#message")).includes("Game start! RED begins."));
check("active rules are listed", (await text("#rules")).includes("full_board_win"));
check("no card note when no rule changed the card", (await text("#card-note")) === "");

await page.hover(cell(2, 2));
const previewCount = (await page.$$("#board .cell.preview")).length;
check("hover preview paints 4 cells", previewCount === 4);
await page.screenshot({ path: `${SHOTS}/hover.png` });
await page.hover(cell(0, 0));
check("preview is clipped at the corner (<=4)", (await page.$$("#board .cell.preview")).length <= 4);

await page.click(cell(2, 2)); await page.waitForFunction(() => document.getElementById("turns").textContent === "49 / 50");
check("score updated after a move", (await text("#score-RED .value")) === "4");
check("BLUE is now active", await page.$eval("#score-BLUE", (e) => e.classList.contains("active")));
check("message names the move", (await text("#message")).includes("RED played at row 3, col 3"));
await page.mouse.move(5, 5);
await page.screenshot({ path: `${SHOTS}/after_move.png` });

await page.reload(); await page.waitForSelector("#board .cell");
check("reload resumes the game", (await text("#turns")) === "49 / 50" && (await text("#score-RED .value")) === "4");

await page.keyboard.press("Escape");
check("Esc goes home", await visible("#home") && !(await visible("#match")));
await page.reload(); await page.waitForSelector("#play-btn");
check("after Esc a reload stays on home", await visible("#home"));

// full match: 50 clicks
const freshGame = () => page.waitForFunction(() =>
  !document.getElementById("match").classList.contains("hidden") &&
  document.getElementById("turns").textContent === "50 / 50");
async function playFullMatch() {
  await freshGame();
  for (let i = 0; i < 50; i++) {
    await page.click(cell(i % 5, (i * 2) % 5));
    await page.waitForFunction((n) => document.getElementById("turns").textContent === `${n} / 50`, {}, 49 - i);
  }
  await page.waitForSelector("#gameover:not(.hidden)");
}
await page.click("#play-btn");
await playFullMatch();
check("game over overlay", await visible("#gameover"));
check("hint hidden at game over", !(await visible("#hint")));
check("outcome text", /wins!|draw/.test(await text("#outcome")));
check("replay/home buttons shown, cards hidden", await visible("#actions") && !(await visible("#cards-block")));
const finals = await page.$$eval("#final-scores .final-score", (els) => els.map((e) => e.textContent.trim()));
const headers = await page.$$eval("#scores .score .value", (els) => els.map((e) => e.textContent.trim()));
check("final scores match the header", finals.length === 2 && finals.join() === headers.join());
await page.screenshot({ path: `${SHOTS}/over.png` });
await page.click(cell(0, 0));
check("clicking after game over changes nothing", (await text("#turns")) === "0 / 50");

await page.click("#replay-btn"); await page.waitForFunction(() => document.getElementById("turns").textContent === "50 / 50");
check("replay starts a fresh game", !(await visible("#gameover")) && (await text("#score-RED .value")) === "0");
await playFullMatch();
await page.click("#home-btn");
check("Home button works", await visible("#home") && !(await visible("#match")));

// ---- settings of the next game: 3 players, 9 turns, no line bonus
check("settings form built from the server schema", (await page.$$("#params .row")).length === 6 && (await page.$$("#rules-list .rule")).length === 5);
check("default form values", (await page.$eval("#param-num_players", (e) => e.value)) === "2");
await page.$eval("#param-num_players", (e) => { e.value = "3"; });
await page.$eval("#param-total_turns", (e) => { e.value = "9"; });
await page.$eval("#rule-line_bonus", (e) => { e.checked = false; e.dispatchEvent(new Event("change")); });
check("an unchecked rule looks disabled", await page.$eval("#rulebox-line_bonus", (e) => e.classList.contains("off")));
await page.click("#play-btn");
await page.waitForFunction(() => document.getElementById("turns").textContent === "9 / 9");
check("3 score boxes", (await page.$$("#scores .score")).length === 3);
check("3 distinct player colors", new Set(await page.$$eval("#scores .score", (els) => els.map((e) => e.style.getPropertyValue("--c")))).size === 3);
check("this game's rules reflect the form", (await text("#rules")).includes("full_board_win") && !(await text("#rules")).includes("line_bonus"));
const turnOrder = [];
for (let i = 0; i < 9; i++) {
  turnOrder.push(await page.$eval("#scores .score.active", (e) => e.id.replace("score-", "")));
  await page.click(cell(i % 5, 0));
  await page.waitForFunction((n) => document.getElementById("turns").textContent === `${n} / 9`, {}, 8 - i);
}
check("players rotate RED, BLUE, GREEN", turnOrder.join() === "RED,BLUE,GREEN,RED,BLUE,GREEN,RED,BLUE,GREEN");
await page.waitForSelector("#gameover:not(.hidden)");
check("game over shows 3 scores", (await page.$$("#final-scores .final-score")).length === 3);
await page.screenshot({ path: `${SHOTS}/over3.png` });
await page.click("#replay-btn");
await page.waitForFunction(() => document.getElementById("turns").textContent === "9 / 9");
check("Replay keeps this game's settings", (await page.$$("#scores .score")).length === 3);
await page.keyboard.press("Escape");
check("the form kept the values after going home", (await page.$eval("#param-num_players", (e) => e.value)) === "3");
await page.click("#defaults-btn");
check("Defaults restores the form", (await page.$eval("#param-num_players", (e) => e.value)) === "2" && await page.$eval("#rule-line_bonus", (e) => e.checked));
await page.$eval("#param-num_players", (e) => { e.value = "9"; });
expectedBadRequests = 1;
await page.click("#play-btn");
await page.waitForSelector("#config-error:not(.hidden)");
check("an invalid setting is explained on the page", (await text("#config-error")).includes("between") && await visible("#home"));
await page.click("#defaults-btn");

// narrow (phone) layout
await page.setViewport({ width: 390, height: 820 });
await page.click("#play-btn"); await freshGame();
await page.click(cell(2, 2)); await page.waitForFunction(() => document.getElementById("turns").textContent === "49 / 50");
check("no horizontal scroll on a phone", await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
await page.screenshot({ path: `${SHOTS}/phone.png`, fullPage: true });

await browser.close();
if (problems.length) { console.log("PROBLEMS:\n" + problems.join("\n")); process.exit(1); }
console.log("ALL OK, no console errors");
