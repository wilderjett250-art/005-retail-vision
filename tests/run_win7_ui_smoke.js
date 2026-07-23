const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const projectRoot = path.resolve(__dirname, "..");
const baseUrl = process.env.APP_BASE_URL || "http://127.0.0.1:18768/";
const sampleImage = path.join(
  projectRoot,
  "diagnostics",
  "normal_detection",
  "samples",
  "01_store_interior.jpeg"
);
const screenshotDirectory = path.join(projectRoot, "output", "playwright");
const screenshotPath = path.join(screenshotDirectory, "win7-final-ui-result.png");

(async () => {
  const browser = await chromium.launch({ channel: "msedge", headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.locator("#service-status span").waitFor();
  const serviceStatus = await page.locator("#service-status span").innerText();
  if (serviceStatus !== "模型已就绪") throw new Error(`Unexpected service status: ${serviceStatus}`);

  await page.locator("#item-license .file-input").setInputFiles(sampleImage);
  await page.locator("#item-license .run-one").click();
  await page.waitForFunction(() => {
    const value = document.querySelector("#item-license .item-state");
    return value && value.innerText === "已识别";
  });

  const score = await page.locator("#item-license .picture-score").innerText();
  const target = await page.locator("#item-license .target-result").innerText();
  const detectionCount = await page.locator("#item-license .detection-count").innerText();
  if (score !== "25.00" || target !== "识别通过" || detectionCount !== "1") {
    throw new Error(`Unexpected UI result: score=${score}, target=${target}, count=${detectionCount}`);
  }

  await page.locator("#item-pack_cluster .file-input").setInputFiles(sampleImage);
  await page.locator("#item-pack_cluster .run-one").click();
  await page.waitForFunction(() => {
    const value = document.querySelector("#item-pack_cluster .item-state");
    return value && value.innerText === "已识别";
  });

  const compositeScore = await page.locator("#item-pack_cluster .picture-score").innerText();
  const compositeTarget = await page.locator("#item-pack_cluster .target-result").innerText();
  const compositeDetailScore = await page.locator("#item-pack_cluster .target-score").innerText();
  const compositeDetectionCount = await page.locator("#item-pack_cluster .detection-count").innerText();
  if (
    compositeScore !== "25.00" ||
    compositeTarget !== "识别通过" ||
    compositeDetailScore !== "25.00" ||
    compositeDetectionCount !== "2"
  ) {
    throw new Error(
      `Unexpected pack-cluster composite result: score=${compositeScore}, ` +
      `target=${compositeTarget}, detail=${compositeDetailScore}, count=${compositeDetectionCount}`
    );
  }
  if (consoleErrors.length) throw new Error(`Browser console errors: ${consoleErrors.join(" | ")}`);

  fs.mkdirSync(screenshotDirectory, { recursive: true });
  await page.screenshot({ path: screenshotPath, fullPage: true });
  console.log("PASS: direct and front-plus-back composite UI rules rendered correctly");
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
