import type { components } from "@/lib/api/schema";

type SignupRequest = components["schemas"]["SignupRequest"];
const emailLocal = /^[A-Za-z0-9!#$%&'*+/=?^`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^`{|}~-]+)*$/;
const emailLabel = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$/;
const seoulYear = new Intl.DateTimeFormat("en", { timeZone: "Asia/Seoul", year: "numeric" });

export const MIN_BIRTH_YEAR = 1900;

export function currentBirthYear(now = new Date()): number {
  return Number(seoulYear.format(now));
}

export function isValidEmail(email: string): boolean {
  const [local, domain, extra] = email.split("@");
  const labels = domain?.split(".") ?? [];
  return email.length <= 254 && local.length <= 64 && emailLocal.test(local) &&
    extra === undefined && labels.length >= 2 && labels.every((label) => emailLabel.test(label));
}

export function validateSignup(
  data: Omit<SignupRequest, "gender"> & { gender: string },
  passwordConfirmation: string,
  maxBirthYear = currentBirthYear(),
): string | null {
  if (!isValidEmail(data.email)) {
    return "이메일 형식을 확인해 주세요.";
  }
  const passwordLength = [...data.password].length;
  if (passwordLength < 8 || passwordLength > 64 || !/[A-Za-z]/.test(data.password) || !/[0-9]/.test(data.password)) {
    return "비밀번호는 영문과 숫자를 포함해 8~64자로 입력해 주세요.";
  }
  if (data.password !== passwordConfirmation) {
    return "비밀번호가 일치하지 않아요.";
  }
  const nicknameLength = [...data.display_name.trim()].length;
  if (nicknameLength < 2 || nicknameLength > 12) {
    return "닉네임은 2~12자로 입력해 주세요.";
  }
  if (data.gender !== "female" && data.gender !== "male") {
    return "성별을 선택해 주세요.";
  }
  if (!Number.isInteger(data.birth_year) || data.birth_year < MIN_BIRTH_YEAR || data.birth_year > maxBirthYear) {
    return "출생연도를 확인해 주세요.";
  }
  return null;
}
