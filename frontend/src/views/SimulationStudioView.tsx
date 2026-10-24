import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Cpu,
  FlaskConical,
  HardDrive,
  Info,
  Network,
  Play,
  Zap,
} from 'lucide-react';
import { listScenarios, runSimulation } from '../api';
import { ResourceBarChart } from '../components/charts';
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  HealthGauge,
  LoadingState,
  MetricCard,
  StatusBadge,
} from '../components/common';
import type {
  ScenarioProfile,
  SimulationRunResponse,
} from '../types';

export const SimulationStudioView: React.FC = () => {
  const [scenarios, setScenarios] = useState<ScenarioProfile[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string>('cpu_spike');
  const [seed, setSeed] = useState<number>(42);
  const [persist, setPersist] = useState<boolean>(false);

  // Optional overrides
  const [useCustomOverrides, setUseCustomOverrides] = useState<boolean>(false);
  const [overrideCpu, setOverrideCpu] = useState<string>('');
  const [overrideMemory, setOverrideMemory] = useState<string>('');
  const [overrideDisk, setOverrideDisk] = useState<string>('');

  const [loadingScenarios, setLoadingScenarios] = useState<boolean>(true);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [simulationResult, setSimulationResult] = useState<SimulationRunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch scenarios from API
  useEffect(() => {
    async function load() {
      try {
        setLoadingScenarios(true);
        const data = await listScenarios();
        setScenarios(data);
        if (data.length > 0) {
          setSelectedScenario(data[0].scenario);
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to retrieve simulation scenarios from API.';
        setError(msg);
      } finally {
        setLoadingScenarios(false);
      }
    }
    load();
  }, []);

  const handleExecute = async () => {
    try {
      setIsExecuting(true);
      setError(null);

      // Build overrides dict
      const overrides: Record<string, unknown> = {};
      if (useCustomOverrides) {
        if (overrideCpu.trim() !== '') overrides.cpu_percent = parseFloat(overrideCpu);
        if (overrideMemory.trim() !== '') overrides.memory_percent = parseFloat(overrideMemory);
        if (overrideDisk.trim() !== '') overrides.disk_percent = parseFloat(overrideDisk);
      }

      const res = await runSimulation({
        scenario: selectedScenario,
        seed: Number(seed),
        persist: Boolean(persist),
        overrides,
      });

      setSimulationResult(res);
    } catch (err: unknown) {
      // NEVER simulate success locally when API fails
      setSimulationResult(null);
      const msg = err instanceof Error ? err.message : 'Simulation execution failed on the backend.';
      setError(msg);
    } finally {
      setIsExecuting(false);
    }
  };

  const currentProfile = scenarios.find((s) => s.scenario === selectedScenario);

  if (loadingScenarios && scenarios.length === 0) {
    return <LoadingState message="Loading anomaly scenarios from FastAPI..." height={350} />;
  }

  // Build resource comparison data for chart if result exists
  const simMetrics = simulationResult?.simulated_metrics;
  const chartData = simMetrics
    ? [
        {
          resource: 'CPU %',
          current: simMetrics.cpu.utilization_percent,
          baseline: 25.0,
        },
        {
          resource: 'RAM %',
          current: simMetrics.memory.utilization_percent,
          baseline: 45.0,
        },
        {
          resource: 'Disk %',
          current: simMetrics.disk.utilization_percent,
          baseline: 55.0,
        },
      ]
    : [];

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <div className="page-title">
            <FlaskConical size={20} style={{ color: 'var(--accent-primary)' }} />
            <span>Deterministic Anomaly Simulation Studio</span>
          </div>
          <div className="page-subtitle">
            Inject synthetic subsystem distress scenarios through the end-to-end ML feature engine and isolation estimator
          </div>
        </div>

        {currentProfile && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Target Subsystem:</span>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-primary)' }}>
              {currentProfile.stress_subsystem}
            </span>
            <StatusBadge status={currentProfile.expected_risk} />
          </div>
        )}
      </div>

      {/* Simulation Controls Card */}
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <FlaskConical size={15} style={{ color: 'var(--accent-primary)' }} />
            <span>Scenario Execution Controls</span>
          </div>
        }
        subtitle="Configure deterministic stress vectors, reproducibility seed, and SQLite persistence"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Controls Bar */}
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-end',
              flexWrap: 'wrap',
              gap: 14,
            }}
          >
            {/* Scenario Selector */}
            <div className="form-group" style={{ flex: '1 1 280px', minWidth: 260 }}>
              <label className="form-label" htmlFor="sim-scenario-select">
                Simulation Scenario Profile
              </label>
              <select
                id="sim-scenario-select"
                className="form-select"
                value={selectedScenario}
                onChange={(e) => setSelectedScenario(e.target.value)}
              >
                {scenarios.map((sc) => (
                  <option key={sc.scenario} value={sc.scenario}>
                    {sc.name} ({sc.stress_subsystem})
                  </option>
                ))}
              </select>
            </div>

            {/* Seed input */}
            <div className="form-group" style={{ width: 120 }}>
              <label className="form-label" htmlFor="sim-seed-input">
                PRNG Seed
              </label>
              <input
                id="sim-seed-input"
                type="number"
                className="form-input"
                value={seed}
                onChange={(e) => setSeed(parseInt(e.target.value, 10) || 0)}
              />
            </div>

            {/* Persist Checkbox */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                paddingBottom: 9,
                fontSize: 12.5,
                color: 'var(--text-secondary)',
              }}
            >
              <input
                id="sim-persist-check"
                type="checkbox"
                checked={persist}
                onChange={(e) => setPersist(e.target.checked)}
                style={{ cursor: 'pointer', accentColor: 'var(--accent-primary)', width: 15, height: 15 }}
              />
              <label htmlFor="sim-persist-check" style={{ cursor: 'pointer', fontWeight: 500 }}>
                Commit to SQLite DB
              </label>
            </div>

            {/* Run Action */}
            <div style={{ marginLeft: 'auto' }}>
              <Button
                variant="primary"
                icon={<Play size={14} />}
                loading={isExecuting}
                onClick={handleExecute}
              >
                Run Simulation
              </Button>
            </div>
          </div>

          {/* Active Profile Description Banner */}
          {currentProfile && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 14px',
                backgroundColor: 'rgba(0, 0, 0, 0.25)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
                fontSize: 12,
                flexWrap: 'wrap',
                gap: 10,
              }}
            >
              <div>
                <strong style={{ color: 'var(--text-primary)' }}>{currentProfile.name}: </strong>
                <span style={{ color: 'var(--text-secondary)' }}>{currentProfile.description}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-muted)' }}>
                <span>Stress Target:</span>
                <code style={{ color: 'var(--accent-primary)' }}>{currentProfile.stress_subsystem}</code>
              </div>
            </div>
          )}

          {/* Optional Metric Overrides Accordion */}
          <div>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => setUseCustomOverrides(!useCustomOverrides)}
              style={{ fontSize: 12 }}
            >
              {useCustomOverrides ? '▼ Hide Advanced Overrides' : '► Advanced Metric Overrides (Optional)'}
            </button>

            {useCustomOverrides && (
              <div
                style={{
                  marginTop: 10,
                  padding: '12px 14px',
                  backgroundColor: 'rgba(0, 0, 0, 0.2)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px dashed var(--border-default)',
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: 12,
                }}
              >
                <div className="form-group">
                  <label className="form-label" htmlFor="override-cpu">CPU Percent Override (%)</label>
                  <input
                    id="override-cpu"
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    placeholder="e.g. 98.5"
                    className="form-input"
                    value={overrideCpu}
                    onChange={(e) => setOverrideCpu(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="override-mem">Memory Percent Override (%)</label>
                  <input
                    id="override-mem"
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    placeholder="e.g. 92.0"
                    className="form-input"
                    value={overrideMemory}
                    onChange={(e) => setOverrideMemory(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="override-disk">Disk Percent Override (%)</label>
                  <input
                    id="override-disk"
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    placeholder="e.g. 95.0"
                    className="form-input"
                    value={overrideDisk}
                    onChange={(e) => setOverrideDisk(e.target.value)}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* Error Banner when Real API execution fails */}
      {error && (
        <ErrorState
          title="Simulation API Error"
          message={error}
          detail="The real API request failed. Synthetic success is never fabricated locally."
          onRetry={handleExecute}
          height={160}
        />
      )}

      {/* Simulation Results Display */}
      {simulationResult && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Top Banner Outcome */}
          <div
            style={{
              padding: '14px 18px',
              borderRadius: 'var(--radius-lg)',
              backgroundColor: simulationResult.prediction.is_anomaly
                ? 'var(--status-critical-bg)'
                : 'var(--status-healthy-bg)',
              border: `1px solid ${
                simulationResult.prediction.is_anomaly
                  ? 'var(--status-critical-border)'
                  : 'var(--status-healthy-border)'
              }`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: 12,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              {simulationResult.prediction.is_anomaly ? (
                <AlertTriangle size={24} style={{ color: 'var(--status-critical)' }} />
              ) : (
                <CheckCircle2 size={24} style={{ color: 'var(--status-healthy)' }} />
              )}
              <div>
                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
                  Simulation Outcome: {simulationResult.profile.name}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                  {simulationResult.diagnostics.summary_headline}
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className={`status-badge ${simulationResult.prediction.is_anomaly ? 'critical' : 'healthy'}`}>
                {simulationResult.prediction.is_anomaly ? 'ANOMALY DETECTED' : 'NOMINAL INFERENCE'}
              </span>
              <StatusBadge status={simulationResult.prediction.risk_category} />
            </div>
          </div>

          {/* Metric Breakdown Grid */}
          <div className="grid-cols-4">
            <MetricCard
              label="Simulated CPU"
              value={`${simMetrics?.cpu.utilization_percent.toFixed(1)}%`}
              percentage={simMetrics?.cpu.utilization_percent}
              icon={<Cpu size={16} />}
              subtext={<span>{simMetrics?.cpu.logical_cores} Cores Stressed</span>}
            />
            <MetricCard
              label="Simulated Memory"
              value={`${simMetrics?.memory.utilization_percent.toFixed(1)}%`}
              percentage={simMetrics?.memory.utilization_percent}
              icon={<Zap size={16} />}
              subtext={<span>{simMetrics?.memory.used_mb.toFixed(0)} MB / {simMetrics?.memory.total_mb.toFixed(0)} MB</span>}
            />
            <MetricCard
              label="Simulated Disk"
              value={`${simMetrics?.disk.utilization_percent.toFixed(1)}%`}
              percentage={simMetrics?.disk.utilization_percent}
              icon={<HardDrive size={16} />}
              subtext={<span>{simMetrics?.disk.used_gb} GB used</span>}
            />
            <MetricCard
              label="Simulated Network"
              value={`${simMetrics?.network.download_kbps.toFixed(1)} KB/s`}
              icon={<Network size={16} />}
              subtext={<span>↑ {simMetrics?.network.upload_kbps.toFixed(1)} KB/s upload</span>}
            />
          </div>

          {/* Charts & Inference Evaluation */}
          <div className="grid-split-left">
            {/* Health Score Gauge */}
            <Card
              title={
                <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                  <Zap size={15} style={{ color: 'var(--accent-primary)' }} />
                  <span>Simulated Health &amp; Risk</span>
                </div>
              }
              subtitle="Scored through complete inference pipeline"
            >
              <div style={{ padding: '8px 0 4px 0', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <HealthGauge
                  score={simulationResult.prediction.health_score}
                  riskCategory={simulationResult.prediction.risk_category}
                  size={145}
                />
                <div
                  style={{
                    width: '100%',
                    marginTop: 16,
                    padding: '12px 14px',
                    backgroundColor: 'rgba(0, 0, 0, 0.25)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-subtle)',
                    fontSize: 12,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 8,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Anomaly Score:</span>
                    <span style={{ fontWeight: 700, color: simulationResult.prediction.anomaly_score >= 0.5 ? 'var(--status-critical)' : 'var(--accent-primary)', fontVariantNumeric: 'tabular-nums' }}>
                      {simulationResult.prediction.anomaly_score.toFixed(3)}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Raw Decision Score:</span>
                    <span style={{ fontWeight: 500, color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>
                      {simulationResult.prediction.raw_decision_score.toFixed(4)}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Engineered Features:</span>
                    <span style={{ fontWeight: 600, color: 'var(--accent-primary)' }}>
                      {simulationResult.features_count} Features
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Persisted to DB:</span>
                    <StatusBadge
                      status={simulationResult.persisted ? 'COMMITTED' : 'EPHEMERAL'}
                      type={simulationResult.persisted ? 'healthy' : 'neutral'}
                    />
                  </div>
                </div>
              </div>
            </Card>

            {/* Subsystem Utilization Comparison Bar Chart */}
            <Card
              title="Simulated vs Baseline Resource Utilization"
              subtitle="Comparison of stressed subsystems against nominal operational baseline"
            >
              <ResourceBarChart data={chartData} height={240} compareMode={true} />
            </Card>
          </div>

          {/* Diagnostic Evidence Report */}
          <Card
            title={
              <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                <Info size={15} style={{ color: 'var(--accent-primary)' }} />
                <span>Generated Diagnostic Evidence &amp; Remediation Runbook</span>
              </div>
            }
            subtitle="Pipeline-generated root-cause hypotheses for synthetic telemetry"
          >
            {simulationResult.diagnostics.recommendations.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {simulationResult.diagnostics.recommendations.map((rec) => (
                  <div
                    key={rec.id}
                    style={{
                      padding: '14px 16px',
                      backgroundColor: 'rgba(0, 0, 0, 0.25)',
                      border: '1px solid var(--border-default)',
                      borderRadius: 'var(--radius-md)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 10,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--text-primary)' }}>
                          {rec.title}
                        </span>
                        <StatusBadge status={rec.severity} />
                      </div>
                      <span style={{ fontSize: 10.5, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                        {rec.category}
                      </span>
                    </div>

                    <p style={{ fontSize: 12.5, color: 'var(--text-secondary)' }}>{rec.summary}</p>

                    {rec.root_cause_hypothesis && (
                      <div
                        style={{
                          fontSize: 12,
                          color: '#BAE6FD',
                          padding: '8px 12px',
                          backgroundColor: 'rgba(56, 189, 248, 0.06)',
                          border: '1px solid rgba(56, 189, 248, 0.2)',
                          borderRadius: 'var(--radius-sm)',
                        }}
                      >
                        <strong>Hypothesis:</strong> {rec.root_cause_hypothesis}
                      </div>
                    )}

                    {/* Remediation steps */}
                    {rec.remediation_steps.length > 0 && (
                      <div style={{ marginTop: 4 }}>
                        <div style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--status-healthy)', marginBottom: 5, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                          Remediation Steps:
                        </div>
                        <ul style={{ paddingLeft: 18, fontSize: 12.5, color: 'var(--text-primary)', display: 'flex', flexDirection: 'column', gap: 3 }}>
                          {rec.remediation_steps.map((st, i) => (
                            <li key={i}>{st}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState message="No critical diagnostic recommendations generated for this simulated profile." height={120} />
            )}
          </Card>
        </div>
      )}
    </div>
  );
};
