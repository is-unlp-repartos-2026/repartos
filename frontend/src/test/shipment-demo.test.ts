import { describe, expect, it } from "vitest";
import { trackingGuideSchema } from "@/lib/shipment-demo";

describe("Tracking guide requirement", () => {
  it("rejects an empty guide", () => expect(trackingGuideSchema.safeParse("").success).toBe(false));
  it("rejects whitespace-only guides", () => expect(trackingGuideSchema.safeParse("   ").success).toBe(false));
  it("accepts a filled guide", () => expect(trackingGuideSchema.parse(" 000123456 ")).toBe("000123456"));
});
import { driverTokenSchema, generateDriverToken } from "@/lib/shipment-demo";
describe("Driver token", () => {
  it("accepts 4 alphanumeric chars", () => expect(driverTokenSchema.parse("ab12")).toBe("AB12"));
  it("rejects 3 chars", () => expect(driverTokenSchema.safeParse("AB1").success).toBe(false));
  it("rejects 5 chars", () => expect(driverTokenSchema.safeParse("AB123").success).toBe(false));
  it("generates a 4-char token not already in use", () => {
    const t = generateDriverToken(["AAAA"]);
    expect(t).toMatch(/^[A-Z0-9]{4}$/); expect(t).not.toBe("AAAA");
  });
});
