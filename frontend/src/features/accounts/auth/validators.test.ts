import { describe, expect, it } from "vitest";
import { currentBirthYear, validateSignup } from "./validators";

const valid = {
  email: "tester@example.com",
  password: "kitten12",
  display_name: "테스터",
  birth_year: 1999,
  gender: "female",
};

describe("F10 signup validation", () => {
  it.each(["가", "가나다라마바사아자차카타파", "   "])("rejects nickname %j", (display_name) => {
    expect(validateSignup({ ...valid, display_name }, valid.password, 2026)).toMatch(/닉네임/);
  });

  it.each(["12345678", "abcdefgh", "abcdef1", "a".repeat(64) + "1"])("rejects password %j", (password) => {
    expect(validateSignup({ ...valid, password }, password, 2026)).toMatch(/비밀번호/);
  });

  it.each([1899, 2027, 2000.5])("rejects birth year %s", (birth_year) => {
    expect(validateSignup({ ...valid, birth_year }, valid.password, 2026)).toMatch(/출생연도/);
  });

  it.each([1900, 2026])("accepts birth year %s at the boundary", (birth_year) => {
    expect(validateSignup({ ...valid, birth_year }, valid.password, 2026)).toBeNull();
  });

  it("accepts the server-compatible sample_user@example.com address", () => {
    expect(validateSignup({ ...valid, email: "sample_user@example.com" }, valid.password, 2026)).toBeNull();
  });

  it("uses the Korean calendar year across New Year", () => {
    expect(currentBirthYear(new Date("2025-12-31T15:01:00Z"))).toBe(2026);
  });
});
