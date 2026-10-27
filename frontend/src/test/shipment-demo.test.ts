import { describe, expect, it } from "vitest";
import { trackingGuideSchema } from "@/lib/shipment-demo";

describe("Tracking guide requirement", () => {
  it("rejects an empty guide", () => expect(trackingGuideSchema.safeParse("").success).toBe(false));
  it("rejects whitespace-only guides", () => expect(trackingGuideSchema.safeParse("   ").success).toBe(false));
  it("accepts a filled guide", () => expect(trackingGuideSchema.parse(" 000123456 ")).toBe("000123456"));
});