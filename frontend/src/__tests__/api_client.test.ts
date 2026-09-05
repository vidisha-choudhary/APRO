import { describe, it, expect, vi, beforeEach } from "vitest";
import { DashboardApiClient } from "../api/client";

describe("DashboardApiClient", () => {
  let client: DashboardApiClient;
  let fetchMock: any;

  beforeEach(() => {
    client = new DashboardApiClient("/api/dashboard");
    fetchMock = vi.fn();
    global.fetch = fetchMock;
  });

  it("getOverview fetches /api/dashboard/overview without query param if not provided", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "ok", metadata: {}, data: null }),
    });

    const res = await client.getOverview();
    expect(res.status).toBe("ok");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const calledUrl = fetchMock.mock.calls[0][0];
    expect(calledUrl).toContain("/api/dashboard/overview");
    expect(calledUrl).not.toContain("benchmark_run_id=");
  });

  it("getOverview appends ?benchmark_run_id=run_123 when provided", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "ok", metadata: { benchmark_run_id: "run_123" }, data: null }),
    });

    const res = await client.getOverview("run_123");
    expect(res.status).toBe("ok");
    const calledUrl = fetchMock.mock.calls[0][0];
    expect(calledUrl).toContain("/api/dashboard/overview?benchmark_run_id=run_123");
  });

  it("propagates benchmark_run_id across benchmarks, safety, prediction-quality, adaptive, cohorts", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ status: "ok", metadata: {} }),
    });

    await client.getBenchmarks("run_test");
    expect(fetchMock.mock.calls[0][0]).toContain("/api/dashboard/benchmarks?benchmark_run_id=run_test");

    await client.getSafety("run_test");
    expect(fetchMock.mock.calls[1][0]).toContain("/api/dashboard/safety?benchmark_run_id=run_test");

    await client.getPredictionQuality("run_test");
    expect(fetchMock.mock.calls[2][0]).toContain("/api/dashboard/prediction-quality?benchmark_run_id=run_test");

    await client.getAdaptive("run_test");
    expect(fetchMock.mock.calls[3][0]).toContain("/api/dashboard/adaptive?benchmark_run_id=run_test");

    await client.getCohorts("run_test");
    expect(fetchMock.mock.calls[4][0]).toContain("/api/dashboard/cohorts?benchmark_run_id=run_test");
  });

  it("throws clear error on HTTP non-200 response", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: async () => ({ detail: "Benchmark run 'run_missing' not found" }),
    });

    await expect(client.getOverview("run_missing")).rejects.toThrow("Benchmark run 'run_missing' not found");
  });
});
