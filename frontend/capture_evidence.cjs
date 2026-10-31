const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const OUTPUT_DIR = path.join(__dirname, '..', 'storage', 'screenshots');
const ARTIFACT_DIR = 'C:\\Users\\DM\\.gemini\\antigravity\\brain\\8b321f81-6da4-400e-8b5d-2855c47f66fe';

fs.mkdirSync(OUTPUT_DIR, { recursive: true });

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function saveScreen(page, name) {
  const p1 = path.join(OUTPUT_DIR, `${name}.png`);
  const p2 = path.join(ARTIFACT_DIR, `${name}.png`);
  await page.screenshot({ path: p1, fullPage: false });
  fs.copyFileSync(p1, p2);
  console.log(`Saved screenshot: ${name}.png -> ${p1}`);
}

async function main() {
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1600,1000']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 1000 });

  console.log('Navigating to http://127.0.0.1:5173...');
  await page.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle2' });
  await sleep(2000);

  // 1. Capture Dashboard
  console.log('Switching to Dashboard...');
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const b = btns.find((el) => el.textContent.includes('Dashboard'));
    if (b) b.click();
  });
  await sleep(1500);
  await saveScreen(page, '01_dashboard');

  // 2. Studio Video Player
  console.log('Switching to Studio...');
  const studioBtn = await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const b = btns.find((el) => el.textContent.includes('Studio') || el.textContent.includes('Timeline Studio'));
    if (b) { b.click(); return true; }
    return false;
  });
  await sleep(2000);
  await saveScreen(page, '02_studio_player');

  // 3. Timeline with Waveform
  console.log('Capturing Timeline with Waveform...');
  // Scroll down slightly or ensure timeline is in view
  await saveScreen(page, '03_timeline_waveform');

  // 4. Layout Editor with Bounding Boxes
  console.log('Switching to Layout Editor...');
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const b = btns.find((el) => el.textContent.includes('Layout') || el.textContent.includes('Edit Layout'));
    if (b) b.click();
  });
  await sleep(2500);
  await saveScreen(page, '04_layout_editor_boxes');

  // 5. Mobile 9:16 Preview
  console.log('Capturing Mobile Preview in Layout...');
  await saveScreen(page, '05_mobile_preview');

  // 6. Scene Keyframe Editing
  console.log('Capturing Scene Keyframe section...');
  await page.evaluate(() => {
    window.scrollTo(0, document.body.scrollHeight);
  });
  await sleep(1000);
  await saveScreen(page, '06_keyframe_editing');

  // 7. Trim Mode Selection Modal
  console.log('Opening Trim Mode Modal in Studio...');
  await page.evaluate(() => {
    window.scrollTo(0, 0);
    const btns = Array.from(document.querySelectorAll('button'));
    const b = btns.find((el) => el.textContent.includes('Timeline Studio') || el.textContent.includes('Studio'));
    if (b) b.click();
  });
  await sleep(1500);

  // Click +10s four times to advance time to 40s
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const plus10 = btns.find((el) => el.textContent.trim() === '+10s');
    if (plus10) {
      plus10.click();
      plus10.click();
      plus10.click();
      plus10.click();
    }
  });
  await sleep(1000);

  // Click Cut Pre-Roll Intro button
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const b = btns.find((el) => el.textContent.includes('Cut Intro Before') || el.textContent.includes('Pre-Roll'));
    if (b && !b.disabled) {
      b.click();
    }
  });
  await sleep(1500);
  await saveScreen(page, '07_trim_mode_selection');

  await browser.close();
  console.log('All screenshots captured successfully!');
}

main().catch((err) => {
  console.error('Screenshot capture failed:', err);
  process.exit(1);
});
