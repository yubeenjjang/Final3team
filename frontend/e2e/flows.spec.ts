import { randomBytes } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";

const festivalId = "fst_000001";
const festivalPath = `/festivals/${festivalId}`;
const returnPath = `/routes/return?festivalId=${festivalId}`;

function capture(page: Page, name: string) {
  return page.screenshot({
    path: `e2e-screenshots/${name}.png`,
    fullPage: true,
    animations: "disabled",
  });
}

function routeResults(page: Page) {
  return page.getByRole("region", { name: "AI 추천 귀가 경로" });
}

test("F6 서울을 선택하면 축제 카드 두 개가 보인다", async ({ page }) => {
  await page.goto("/festivals");
  const cards = page.getByTestId(/^festival-card-/);
  await expect(page.getByTestId("festival-card-fst_000003")).toBeVisible();
  await capture(page, "f6-01-festivals");

  await page.getByRole("combobox", { name: "지역 선택" }).selectOption({ label: "서울" });
  await expect(cards).toHaveCount(2);
  await expect(page.getByTestId("festival-card-fst_000001")).toBeVisible();
  await expect(page.getByTestId("festival-card-fst_000002")).toBeVisible();
  await capture(page, "f6-02-seoul");
});

test("F7 서울 축제 상세에 혼잡도, 기온, 공지 두 건이 보인다", async ({ page }) => {
  await page.goto(festivalPath);
  await expect(page.getByTestId("live-info-crowd").getByText("보통", { exact: true })).toBeVisible();
  await expect(page.getByTestId("live-info-weather").getByText(/^-?\d+(?:\.\d+)?°C$/)).toBeVisible();
  await expect(page.getByTestId("live-info-notices").getByRole("listitem")).toHaveCount(2);
  await capture(page, "f7-01-seoul-detail");
});

test("F7 부산 축제 상세에 혼잡도 미지원 안내가 보인다", async ({ page }) => {
  await page.goto("/festivals/fst_000003");
  const crowd = page.getByTestId("live-info-crowd");
  await expect(crowd.getByText("이 지역은 아직 지원하지 않아요", { exact: true })).toBeVisible();
  await capture(page, "f7-02-busan-detail");
});

test("F7 없는 축제는 안내를 표시하고 목록으로 돌아갈 수 있다", async ({ page }) => {
  await page.goto("/festivals/fst_999999");
  await expect(page.getByText("축제를 찾을 수 없어요", { exact: true })).toBeVisible();
  await capture(page, "f7-03-missing-festival");

  await page.getByRole("link", { name: "목록으로", exact: true }).click();
  await expect(page).toHaveURL("/festivals");
  await expect(page.getByTestId("festival-card-fst_000001")).toBeVisible();
  await capture(page, "f7-04-back-to-list");
});

test("F8 서울역 귀가를 요청하면 38분 경로 카드가 보인다", async ({ page }) => {
  await page.goto(returnPath);
  await page.getByRole("textbox", { name: "도착지" }).fill("서울역");
  const submit = page.getByRole("button", { name: "집으로 가는 길 찾기" });
  await expect(submit).toBeEnabled();
  await capture(page, "f8-01-return-form");

  await submit.click();
  const card = routeResults(page).getByRole("button", { name: /38분/ });
  await expect(card.getByText("38분", { exact: true })).toBeVisible();
  await capture(page, "f8-02-return-result");
});

test("F8 async_timeout 시나리오에서 시간 초과와 다시 시도가 보인다", async ({ page }) => {
  await page.goto(returnPath);
  await page.getByRole("combobox", { name: "시나리오" }).selectOption("async_timeout");
  await page.getByRole("textbox", { name: "도착지" }).fill("서울역");
  const submit = page.getByRole("button", { name: "집으로 가는 길 찾기" });
  await expect(submit).toBeEnabled();
  await capture(page, "f8-03-timeout-form");

  await submit.click();
  await expect(page.getByRole("alert").filter({ hasText: "경로를 찾는 시간이 초과됐어요." })).toBeVisible();
  await expect(page.getByRole("button", { name: "다시 시도", exact: true })).toBeVisible();
  await capture(page, "f8-04-timeout-result");
});

test("F9 홈 AI 답변에서 귀가 경로 카드로 이동한다", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /오늘,\s*어디서 놀까\?/ })).toBeVisible();
  await capture(page, "f9-01-home");

  await page.getByRole("textbox", { name: "AI 질문 입력" }).fill("서울역으로 귀가하는 길 알려줘");
  await page.getByRole("button", { name: "AI에게 질문하기" }).click();
  await expect(page.getByRole("status").filter({ hasText: "경로를 찾았어요." })).toBeVisible();
  const routeLink = page.getByRole("link", { name: "귀가 경로 보기" });
  await expect(routeLink).toBeVisible();
  await capture(page, "f9-02-assistant-answer");

  await routeLink.click();
  await expect(page).toHaveURL(/\/routes\/return\?id=[^&]+$/);
  await expect(routeResults(page).getByRole("button", { name: /38분/ })).toBeVisible();
  await capture(page, "f9-03-assistant-route");
});

test("F10 회원가입과 로그인 후 찜한 축제는 다시 들어가도 유지된다", async ({ page }) => {
  const nickname = `${Date.now().toString(36)}${randomBytes(2).toString("hex")}`;
  const email = `${nickname}@example.com`;
  const password = `E2e${randomBytes(12).toString("hex")}`;
  const favorite = page.getByRole("button", { name: "찜하기", exact: true });
  const savedFavorite = page.getByRole("button", { name: "찜 해제", exact: true });

  await page.goto(festivalPath);
  await favorite.click();
  await expect(page).toHaveURL(`/auth/login?next=${encodeURIComponent(festivalPath)}`);
  await capture(page, "f10-01-guest-login");

  await page.getByRole("link", { name: "회원가입", exact: true }).click();
  await expect(page).toHaveURL(`/auth/signup?next=${encodeURIComponent(festivalPath)}`);
  await expect(page.getByLabel("닉네임", { exact: true })).toBeVisible();
  await capture(page, "f10-02-signup");

  await page.getByLabel("이메일", { exact: true }).fill(email);
  await page.getByLabel("비밀번호", { exact: true }).fill(password);
  await page.getByLabel("비밀번호 확인", { exact: true }).fill(password);
  await page.getByLabel("닉네임", { exact: true }).fill(nickname);
  await page.getByText("여성", { exact: true }).click();
  await expect(page.getByRole("radio", { name: "여성" })).toBeChecked();
  await page.getByRole("combobox", { name: "출생연도" }).selectOption("2000");
  await page.getByRole("button", { name: "회원가입", exact: true }).click();

  const loginButton = page.getByRole("button", { name: "로그인", exact: true });
  await expect(loginButton).toBeVisible();
  await expect(page.getByLabel("이메일", { exact: true })).toHaveValue(email);
  await capture(page, "f10-03-login-after-signup");

  await page.getByLabel("비밀번호", { exact: true }).fill(password);
  await loginButton.click();
  await expect(page).toHaveURL(festivalPath);
  await expect(page.getByRole("link", { name: `내 계정 (${nickname})`, exact: true })).toBeVisible();
  await expect(favorite).toHaveAttribute("aria-pressed", "false");
  await capture(page, "f10-04-signed-in");

  await favorite.click();
  await expect(savedFavorite).toHaveAttribute("aria-pressed", "true");
  await capture(page, "f10-05-favorite-saved");

  await page.reload();
  await expect(savedFavorite).toHaveAttribute("aria-pressed", "true");
  await capture(page, "f10-06-favorite-persisted");
});
