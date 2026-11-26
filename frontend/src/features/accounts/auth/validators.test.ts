import { describe, expect, it } from "vitest";
import { currentBirthYear, validatePasswordChange, validateSignup } from "./validators";

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

describe("password change validation", () => {
  it.each(["12345678", "abcdefgh", "abc1234", "a".repeat(64) + "1"])(
    "rejects invalid new password %j",
    (newPassword) => {
      expect(validatePasswordChange("Current123", newPassword, newPassword)).toMatch(/영문과 숫자/);
    },
  );

  it("rejects when new password matches current password", () => {
    expect(validatePasswordChange("SamePass12", "SamePass12", "SamePass12")).toMatch(/달라야/);
  });

  it("rejects when confirmation does not match", () => {
    expect(validatePasswordChange("OldPass12", "NewPass12", "OtherPass12")).toMatch(/일치하지/);
  });

  it("accepts a valid password change", () => {
    expect(validatePasswordChange("OldPass12", "NewPass34", "NewPass34")).toBeNull();
  });
});
